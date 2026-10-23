"""Atomic plan commit store: CAS, reservations, audit and outbox in one transaction (P03-04).

Order of operations (mirrors DATA_CONTRACTS §提交与并发):

1. lock the schedule row, so competing commits for the same schedule serialize;
2. re-read the idempotency receipt for this key (same hash returns it unchanged);
3. verify that the candidate, its snapshot and the validation report describe the same
   content, and that the expected active version still matches;
4. allocate the next ``version_no`` and insert the immutable version + schedule tasks;
5. lock resource rows in ascending UUID order and re-check calendar capacity;
6. CAS ``schedules.active_version_id``, supersede the previous version, append audit and
   outbox, and store the receipt — all in the same transaction.

No route is registered here: P16-03 owns the formal commit API.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, fields, replace
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, insert, select, update

from logistics_backend.errors import ServiceError
from logistics_backend.persistence.idempotency import IdempotencyStore
from logistics_backend.persistence.planning_models import (
    audit_entries,
    candidate_plans,
    outbox,
    planning_snapshots,
    schedule_tasks,
    schedule_versions,
    schedules,
)
from logistics_backend.persistence.reservations import ReservationStore
from logistics_contracts.planning import (
    CandidatePlanDTO,
    CommitReceiptDTO,
    ScheduleTaskDTO,
    ScheduleVersionDTO,
)
from logistics_domain.planning import (
    CommitCommand,
    CommitReceipt,
    ScheduleTask,
    ScheduleVersion,
    ValidationReport,
    VersionReason,
    content_hash,
)
from logistics_domain.runtime import ActorContext
from logistics_domain.states import EntityState, ErrorCode

SYSTEM_ACTOR = UUID(int=0)
RESERVATION_TTL = timedelta(hours=24)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


class PlanCommitStore:
    """Concrete ``PlanCommitStore`` protocol implementation."""

    def __init__(self, uow_factory, workspace_id: UUID):
        self.uow_factory = uow_factory
        self.workspace_id = workspace_id
        self.idempotency = IdempotencyStore()
        self.reservations = ReservationStore()

    def commit(self, cmd: CommitCommand, report: ValidationReport, *,
               actor: ActorContext | None = None, trace_id: UUID | None = None) -> CommitReceipt:
        if not isinstance(cmd, CommitCommand):
            raise ServiceError(ErrorCode.INVALID_INPUT, "commit expects a CommitCommand")
        if not isinstance(report, ValidationReport):
            raise ServiceError(ErrorCode.INVALID_INPUT, "commit expects a ValidationReport")
        if report.candidate_hash != cmd.candidate_hash or report.snapshot_hash != cmd.snapshot_hash:
            raise ServiceError(ErrorCode.INVALID_INPUT,
                               "validation report does not describe this candidate/snapshot")
        if not report.valid:
            raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT,
                               "candidate has no valid independent validation report")
        actor_id = actor.actor_id if actor is not None else SYSTEM_ACTOR
        trace = trace_id if trace_id is not None else uuid4()
        now = utcnow()
        request_hash = content_hash(cmd)
        with self.uow_factory() as uow:
            connection = uow.connection
            lock_key = int.from_bytes(hashlib.sha256(
                f"{self.workspace_id}:{actor_id}:commit:{cmd.idempotency_key}".encode()).digest()[:8],
                "big", signed=True)
            connection.execute(select(func.pg_advisory_xact_lock(lock_key)))
            schedule = connection.execute(select(schedules).where(
                schedules.c.id == cmd.schedule_id, schedules.c.scope_id == self.workspace_id)
                .with_for_update()).mappings().first()
            if schedule is None:
                raise ServiceError(ErrorCode.NOT_FOUND, "schedule not found")
            if schedule["status"] in ("completed", "superseded"):
                raise ServiceError(ErrorCode.INVALID_TRANSITION,
                                   "a finished schedule cannot accept a new version")
            prior_receipt = self.idempotency.lookup(connection, scope_id=self.workspace_id,
                actor_id=actor_id, operation="commit_schedule", key=cmd.idempotency_key)
            if prior_receipt is not None:
                if prior_receipt["request_hash"] != request_hash:
                    raise ServiceError(ErrorCode.IDEMPOTENCY_CONFLICT,
                                       "idempotency key was used with a different commit")
                return CommitReceiptDTO.model_validate(prior_receipt["receipt"]).to_domain()
            if schedule["active_version_id"] != cmd.expected_active_version_id:
                raise ServiceError(ErrorCode.STALE_SNAPSHOT,
                                   "active version changed since the candidate was read")
            candidate_row = connection.execute(select(candidate_plans).where(
                candidate_plans.c.id == cmd.candidate_id,
                candidate_plans.c.schedule_id == cmd.schedule_id,
                candidate_plans.c.scope_id == self.workspace_id)).mappings().first()
            if candidate_row is None:
                raise ServiceError(ErrorCode.NOT_FOUND, "candidate not found")
            candidate = CandidatePlanDTO.model_validate_json(
                json.dumps(candidate_row["payload"])).to_domain()
            if candidate.content_hash != cmd.candidate_hash:
                raise ServiceError(ErrorCode.INVALID_INPUT, "candidate content hash mismatch")
            if candidate.snapshot_hash != cmd.snapshot_hash:
                raise ServiceError(ErrorCode.STALE_SNAPSHOT, "candidate snapshot hash mismatch")
            if (candidate.epoch_utc != schedule["epoch_utc"]
                    or candidate.horizon_s != schedule["horizon_s"]):
                raise ServiceError(ErrorCode.STALE_SNAPSHOT,
                                   "candidate epoch/horizon differs from the schedule")
            if not candidate.solver_evidence_refs:
                raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT,
                                   "candidate has no trusted solver evidence reference")
            snapshot = connection.execute(select(planning_snapshots.c.content_hash).where(
                planning_snapshots.c.id == candidate.snapshot_id,
                planning_snapshots.c.scope_id == self.workspace_id)).first()
            if snapshot is None or snapshot[0] != candidate.snapshot_hash:
                raise ServiceError(ErrorCode.STALE_SNAPSHOT, "planning snapshot is unavailable")
            version_no = int(connection.execute(select(
                func.coalesce(func.max(schedule_versions.c.version_no), 0)).where(
                schedule_versions.c.schedule_id == cmd.schedule_id)).scalar_one())
            previous = None
            if schedule["active_version_id"] is not None:
                previous = connection.execute(select(schedule_versions.c.id,
                    schedule_versions.c.content_hash, schedule_versions.c.version_no).where(
                    schedule_versions.c.id == schedule["active_version_id"])).mappings().first()
                if previous is None:
                    raise ServiceError(ErrorCode.STALE_SNAPSHOT,
                                       "active version pointer references a missing version")
            version_id = uuid4()
            version = ScheduleVersion(
                id=version_id, status=EntityState.COMMITTED, created_at=now, updated_at=now,
                row_version=0, schema_version="2.0.0", created_by=actor_id,
                schedule_id=cmd.schedule_id, version_no=version_no + 1,
                parent_version_id=previous["id"] if previous is not None else None,
                snapshot_id=candidate.snapshot_id, content_hash=candidate.content_hash,
                reason=VersionReason("commit"), event_id=None,
                task_refs=tuple(task.task_id for task in candidate.task_assignments),
                validation_report_ref=report.id)
            connection.execute(insert(schedule_versions).values(
                id=version.id, scope_id=self.workspace_id, status=version.status.value,
                created_at=now, updated_at=now, created_by=actor_id, row_version=0,
                schema_version="2.0.0", payload=_version_payload(version),
                schedule_id=cmd.schedule_id, version_no=version.version_no,
                parent_version_id=version.parent_version_id, snapshot_id=version.snapshot_id,
                content_hash=version.content_hash, reason=version.reason,
                event_id=None, validation_report_ref=report.id))
            for assignment in candidate.task_assignments:
                stored = replace(assignment, id=uuid4(), version_id=version_id,
                                 status=EntityState.PLANNED, created_at=now, updated_at=now,
                                 row_version=0, created_by=actor_id)
                connection.execute(insert(schedule_tasks).values(
                    id=stored.id, scope_id=self.workspace_id, status=stored.status.value,
                    created_at=now, updated_at=now, created_by=actor_id, row_version=0,
                    schema_version="2.0.0", payload=_task_payload(stored),
                    version_id=version_id, task_id=stored.task_id,
                    task_kind=stored.task_kind.value,
                    planned_start_s=stored.planned_start_s,
                    planned_end_s=stored.planned_end_s, sequence=stored.sequence))
            self.reservations.assert_and_reserve(connection,
                workspace_id=self.workspace_id, schedule_epoch=schedule["epoch_utc"],
                assignments=candidate.task_assignments, version_id=version_id,
                actor_id=actor_id, now=now, expires_at=now + RESERVATION_TTL)
            if previous is not None:
                next_revision = schedule_versions.c.row_version + 1
                superseded_payload = schedule_versions.c.payload.op("||")(
                    func.jsonb_build_object("status", "superseded",
                                            "row_version", next_revision))
                connection.execute(update(schedule_versions).where(
                    schedule_versions.c.id == previous["id"]).values(
                    status="superseded", row_version=next_revision,
                    payload=superseded_payload, updated_at=now))
            schedule_revision = schedule["row_version"] + 1
            schedule_payload = schedules.c.payload.op("||")(
                func.jsonb_build_object("status", "active", "row_version", schedule_revision,
                                        "active_version_id", str(version_id),
                                        "updated_at", _utc(now)))
            updated = connection.execute(update(schedules).where(
                schedules.c.id == cmd.schedule_id,
                schedules.c.scope_id == self.workspace_id,
                schedules.c.active_version_id.is_(None) if cmd.expected_active_version_id is None
                else schedules.c.active_version_id == cmd.expected_active_version_id).values(
                active_version_id=version_id, status="active",
                row_version=schedule_revision, payload=schedule_payload, updated_at=now))
            if updated.rowcount != 1:
                raise ServiceError(ErrorCode.STALE_SNAPSHOT, "active version CAS failed")
            audit_id = uuid4()
            connection.execute(insert(audit_entries).values(
                id=audit_id, scope_id=self.workspace_id, status="recorded",
                created_at=now, updated_at=now, created_by=actor_id, row_version=0,
                schema_version="2.0.0", payload=_audit_payload(audit_id, actor_id, trace, now,
                    cmd.schedule_id, previous["content_hash"] if previous is not None else None,
                    candidate.content_hash),
                actor_id=actor_id, action="commit_schedule", entity_kind="schedule",
                entity_id=cmd.schedule_id, trace_id=trace,
                before_hash=previous["content_hash"] if previous is not None else None,
                after_hash=candidate.content_hash))
            sequence = int(connection.execute(select(func.nextval("outbox_sequence"))).scalar_one())
            outbox_id = uuid4()
            connection.execute(insert(outbox).values(
                id=outbox_id, scope_id=self.workspace_id, status="pending",
                created_at=now, updated_at=now, created_by=actor_id, row_version=0,
                schema_version="2.0.0", payload=_outbox_payload(outbox_id, actor_id, now,
                    cmd.schedule_id, version_id, version.version_no),
                topic="schedule.version_committed", sequence=sequence, retry_after=None,
                attempt=0))
            receipt = CommitReceipt(schedule_id=cmd.schedule_id, version_id=version_id,
                version_no=version.version_no, parent_version_id=version.parent_version_id,
                content_hash=candidate.content_hash, audit_id=audit_id, trace_id=trace,
                committed_at=now)
            receipt_payload = json.loads(CommitReceiptDTO.model_validate(
                asdict(receipt)).model_dump_json())
            self.idempotency.register(connection, scope_id=self.workspace_id,
                actor_id=actor_id, operation="commit_schedule", key=cmd.idempotency_key,
                request_hash=request_hash, receipt=receipt_payload,
                expires_at=now + timedelta(days=1))
            return receipt


def _version_payload(version: ScheduleVersion) -> dict:
    return json.loads(ScheduleVersionDTO.model_validate({
        item.name: getattr(version, item.name) for item in fields(version)
    }).model_dump_json())


def _task_payload(task: ScheduleTask) -> dict:
    return json.loads(ScheduleTaskDTO.model_validate({
        item.name: getattr(task, item.name) for item in fields(task)
    }).model_dump_json())


def _audit_payload(audit_id, actor_id, trace, now, schedule_id, before_hash, after_hash) -> dict:
    return {
        "id": str(audit_id), "status": "recorded", "schema_version": "2.0.0",
        "row_version": 0, "created_at": _utc(now), "updated_at": _utc(now),
        "created_by": str(actor_id), "actor_id": str(actor_id), "action": "commit_schedule",
        "entity_ref": {"kind": "schedule", "id": str(schedule_id), "revision": None},
        "trace_id": str(trace), "before_hash": before_hash, "after_hash": after_hash,
    }


def _outbox_payload(outbox_id, actor_id, now, schedule_id, version_id, version_no) -> dict:
    return {
        "id": str(outbox_id), "status": "pending", "schema_version": "2.0.0",
        "row_version": 0, "created_at": _utc(now), "updated_at": _utc(now),
        "created_by": str(actor_id), "topic": "schedule.version_committed",
        "entity_ref": {"kind": "schedule_version", "id": str(version_id), "revision": 0},
        "schedule_id": str(schedule_id), "version_no": version_no,
    }


def _utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["PlanCommitStore", "SYSTEM_ACTOR", "utcnow"]
