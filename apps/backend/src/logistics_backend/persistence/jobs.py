"""PostgreSQL job queue with row locks, fencing epochs and bounded retries."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, insert, update, or_, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from logistics_backend.persistence.runtime_models import jobs, attempts, requests, idempotency
from logistics_backend.application.jobs import LeaseToken, WorkLeaseLost, WorkRetryScheduled, WorkTerminal
from logistics_backend.application.master_data import ServiceError
from logistics_contracts.runtime import JobRequest, JobRef, JobView, JobResultRef
from logistics_contracts.common import ErrorEnvelope
from logistics_domain.states import ErrorCode


def utcnow():
    return datetime.now(timezone.utc).replace(microsecond=0)


def stored_failure(error):
    return {"code": error.code.value, "safe_message": error.message,
            "trace_id": str(error.trace_id), "retryable": error.retryable, "diagnostic_ref": None}


class JobRepository:
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    def store_request(self, reference, scope_id, content: bytes):
        if hashlib.sha256(content).hexdigest() != reference.hash:
            raise ServiceError(ErrorCode.INVALID_INPUT, "request hash mismatch")
        with self.uow_factory() as uow:
            uow.connection.execute(pg_insert(requests).values(request_id=reference.request_id,
                version=reference.version, scope_id=scope_id, family=reference.family.value,
                schema_version=reference.schema_version, hash=reference.hash, content=content).on_conflict_do_nothing())
            row = uow.connection.execute(select(requests).where(requests.c.request_id == reference.request_id,
                requests.c.version == reference.version)).mappings().one()
            if row["hash"] != reference.hash or row["content"] != content or row["scope_id"] != scope_id or row["family"] != reference.family.value:
                raise ServiceError(ErrorCode.IDEMPOTENCY_CONFLICT, "immutable request already exists")

    def load_request(self, reference, scope_id):
        with self.uow_factory() as uow:
            rows = uow.connection.execute(select(requests).where(requests.c.request_id == reference.request_id,
                requests.c.scope_id == scope_id)).mappings().all()
        if not rows:
            raise ServiceError(ErrorCode.NOT_FOUND, "request not found")
        row = next((r for r in rows if r["version"] == reference.version), None)
        if row is None:
            raise ServiceError(ErrorCode.STALE_SNAPSHOT, "request version not found")
        if (row["hash"] != reference.hash or hashlib.sha256(row["content"]).hexdigest() != reference.hash
                or row["family"] != reference.family.value or row["schema_version"] != reference.schema_version):
            raise ServiceError(ErrorCode.INVALID_INPUT, "request reference mismatch")
        return row["content"]

    def enqueue(self, command, actor, key, trace_id):
        now = utcnow()
        if not key or len(key) > 256:
            raise ServiceError(ErrorCode.INVALID_INPUT, "invalid idempotency key")
        if not now < command.deadline_utc <= now + timedelta(seconds=60):
            raise ServiceError(ErrorCode.INVALID_INPUT, "job deadline must be within 60 seconds")
        body = command.model_dump(mode="json")
        digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        job_id = uuid4()
        receipt = JobRef(schema_version="2.0.0", job_id=job_id, status="queued",
            status_url=f"/api/v1/jobs/{job_id}", result_url=f"/api/v1/jobs/{job_id}/result", trace_id=trace_id)
        with self.uow_factory() as uow:
            result = uow.connection.execute(pg_insert(idempotency).values(scope_id=actor.scope_id,
                actor_id=actor.actor_id, operation="submit_job", key=key, request_hash=digest,
                receipt=receipt.model_dump(mode="json"), expires_at=now + timedelta(hours=24)).on_conflict_do_nothing())
            if result.rowcount == 0:
                prior = uow.connection.execute(select(idempotency).where(idempotency.c.scope_id == actor.scope_id,
                    idempotency.c.actor_id == actor.actor_id, idempotency.c.operation == "submit_job",
                    idempotency.c.key == key)).mappings().one()
                if prior["request_hash"] != digest:
                    raise ServiceError(ErrorCode.IDEMPOTENCY_CONFLICT, "idempotency key has a different request")
                return JobRef.model_validate(prior["receipt"])
            uow.connection.execute(insert(jobs).values(id=job_id, scope_id=actor.scope_id, actor_id=actor.actor_id,
                created_by=actor.actor_id, request_id=command.payload.request_ref.request_id,
                request_version=command.payload.request_ref.version,
                trace_id=trace_id, schema_version="2.0.0", kind=command.kind.value, status="queued", command=body,
                request_hash=digest, row_version=0, created_at=now, updated_at=now, available_at=now,
                deadline_utc=command.deadline_utc, attempt=0, max_attempts=3, cancel_requested=False, lease_epoch=0))
        return receipt

    def _view(self, row):
        failure = row["failure"]
        error = ErrorEnvelope(code=failure["code"], message=failure["safe_message"],
            trace_id=failure["trace_id"], retryable=failure["retryable"]) if failure else None
        return JobView(schema_version="2.0.0", job_id=row["id"], kind=row["kind"], status=row["status"],
            row_version=row["row_version"], created_at=row["created_at"], started_at=row["started_at"],
            finished_at=row["finished_at"], attempt=row["attempt"], max_attempts=row["max_attempts"],
            deadline_utc=row["deadline_utc"], cancel_requested=row["cancel_requested"],
            result_ref=row["result_ref"], error=error, trace_id=row["trace_id"])

    def get(self, job_id, scope_id):
        with self.uow_factory() as uow:
            row = uow.connection.execute(select(jobs).where(jobs.c.id == job_id, jobs.c.scope_id == scope_id)).mappings().first()
            if row is None:
                raise ServiceError(ErrorCode.NOT_FOUND, "job not found")
            return self._view(row)

    def cancel(self, job_id, expected_revision, scope_id):
        with self.uow_factory() as uow:
            row = uow.connection.execute(select(jobs).where(jobs.c.id == job_id, jobs.c.scope_id == scope_id).with_for_update()).mappings().first()
            if row is None:
                raise ServiceError(ErrorCode.NOT_FOUND, "job not found")
            if row["status"] in ("completed", "failed", "cancelled"):
                return self._view(row)
            if row["row_version"] != expected_revision:
                raise ServiceError(ErrorCode.STALE_SNAPSHOT, "job revision changed")
            values = dict(cancel_requested=True, updated_at=utcnow(), row_version=row["row_version"] + 1)
            if row["status"] == "queued":
                values.update(status="cancelled", finished_at=utcnow())
            result = uow.connection.execute(update(jobs).where(jobs.c.id == job_id).values(**values).returning(jobs)).mappings().one()
            return self._view(result)

    def _attempt(self, connection, row, outcome, now, failure=None, result=None):
        connection.execute(insert(attempts).values(id=uuid4(), job_id=row["id"], attempt_no=row["attempt"],
            schema_version="2.0.0", status="recorded", row_version=0, created_at=now, updated_at=now,
            created_by=row["created_by"],
            lease_owner=row["lease_owner"], lease_epoch=row["lease_epoch"], started_at=row["started_at"],
            finished_at=now, outcome=outcome, failure=failure, result_ref=result))

    def claim(self, owner_id, lease_seconds=15):
        now = utcnow()
        with self.uow_factory() as uow:
            # Lock one eligible row. Other worker processes skip it rather than waiting.
            row = uow.connection.execute(select(jobs).where(or_(
                (jobs.c.status == "queued") & (jobs.c.available_at <= now),
                (jobs.c.status == "running") & (jobs.c.lease_expires_at <= now)))
                .order_by(jobs.c.created_at, jobs.c.id).with_for_update(skip_locked=True).limit(1)).mappings().first()
            if row is None:
                return None
            failure = stored_failure(ErrorEnvelope(code=ErrorCode.DEPENDENCY_UNAVAILABLE, message="worker lease expired",
                trace_id=row["trace_id"], retryable=True))
            if row["status"] == "running":
                self._attempt(uow.connection, row, "lease_lost", now, failure=failure)
            if row["cancel_requested"] or row["deadline_utc"] <= now or row["attempt"] >= row["max_attempts"]:
                cancelled = row["cancel_requested"]
                if not cancelled:
                    failure["safe_message"] = "job deadline or attempt limit reached"
                    failure["retryable"] = False
                uow.connection.execute(update(jobs).where(jobs.c.id == row["id"]).values(
                    status="cancelled" if cancelled else "failed", finished_at=now, updated_at=now,
                    lease_owner=None, lease_expires_at=None, failure=None if cancelled else failure,
                    row_version=row["row_version"] + 1))
                return None
            expires = min(now + timedelta(seconds=lease_seconds), row["deadline_utc"])
            claimed = uow.connection.execute(update(jobs).where(jobs.c.id == row["id"]).values(
                status="running", lease_owner=owner_id, lease_epoch=row["lease_epoch"] + 1,
                lease_expires_at=expires, started_at=now, updated_at=now, failure=None,
                attempt=row["attempt"] + 1, row_version=row["row_version"] + 1).returning(jobs)).mappings().one()
            token = LeaseToken(row["id"], owner_id, claimed["lease_epoch"], expires)
            return token, JobRequest.model_validate_json(json.dumps(claimed["command"])), claimed["scope_id"], claimed["trace_id"]

    def heartbeat(self, token, seconds=15):
        now = utcnow()
        with self.uow_factory() as uow:
            row = uow.connection.execute(update(jobs).where(jobs.c.id == token.job_id,
                jobs.c.status == "running", jobs.c.lease_owner == token.owner_id,
                jobs.c.lease_epoch == token.epoch, jobs.c.lease_expires_at > now)
                .values(lease_expires_at=func.least(now + timedelta(seconds=seconds), jobs.c.deadline_utc))
                .returning(jobs.c.cancel_requested)).first()
            return None if row is None else row.cancel_requested

    def finish(self, token, result: JobResultRef | None = None, failure: ErrorEnvelope | None = None):
        now = utcnow()
        with self.uow_factory() as uow:
            row = uow.connection.execute(select(jobs).where(jobs.c.id == token.job_id,
                jobs.c.status == "running", jobs.c.lease_owner == token.owner_id,
                jobs.c.lease_epoch == token.epoch, jobs.c.lease_expires_at > now).with_for_update()).mappings().first()
            if row is None:
                return WorkLeaseLost(token.job_id)
            if result is not None and result.family.value != row["kind"]:
                raise ServiceError(ErrorCode.INVALID_INPUT, "result family mismatch")
            if row["cancel_requested"]:
                status, result, failure = "cancelled", None, None
            elif result is not None and failure is None and now < row["deadline_utc"]:
                status = "completed"
            elif result is not None and failure is None:
                # A result that arrives after its deadline was never allowed to commit.
                status = "failed"
                failure = ErrorEnvelope(code=ErrorCode.DEPENDENCY_UNAVAILABLE,
                    message="job deadline expired before the result was committed",
                    trace_id=row["trace_id"], retryable=False)
            elif failure is not None and result is None:
                status = "failed"
            else:
                raise ServiceError(ErrorCode.INVALID_INPUT, "job completion requires result or failure")
            stored_result = result.model_dump(mode="json") if result else None
            failure_data = stored_failure(failure) if failure else None
            self._attempt(uow.connection, row, status, now, failure_data, stored_result)
            available = now + timedelta(seconds=min(2 ** row["attempt"], 8))
            retry = status == "failed" and failure.retryable and row["attempt"] < row["max_attempts"] and available < row["deadline_utc"]
            uow.connection.execute(update(jobs).where(jobs.c.id == token.job_id).values(
                status="queued" if retry else status, result_ref=stored_result, failure=None if retry else failure_data,
                updated_at=now, finished_at=None if retry else now, available_at=available,
                lease_owner=None, lease_expires_at=None, row_version=row["row_version"] + 1))
            return WorkRetryScheduled(token.job_id, available) if retry else WorkTerminal(token.job_id, status)
