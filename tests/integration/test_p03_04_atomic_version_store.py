"""Real PostgreSQL commit / idempotency checks for P03-04 (requires TEST_DATABASE_URL)."""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, insert, text

from logistics_backend.persistence.planning_models import (
    candidate_plans,
    planning_snapshots,
    schedules,
)
from logistics_backend.persistence.resource_models import docks, warehouses
from logistics_backend.persistence.uow import UnitOfWork
from logistics_backend.persistence.version_store import PlanCommitStore
from logistics_contracts.planning import CandidatePlanDTO
from logistics_domain.planning import (
    CandidatePlan,
    CommitCommand,
    CostBreakdown,
    ObjectiveBreakdown,
    PlanningScope,
    TransportPlan,
    ValidationReport,
    WarehousePlan,
    content_hash,
)
from logistics_domain.runtime import ActorContext
from logistics_domain.states import ActorRole, EntityState
from logistics_domain.planning import ScheduleTask, TaskKind
from logistics_backend.application.master_data import ServiceError
from logistics_domain.states import ErrorCode

pytestmark = pytest.mark.requires_postgres

EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)
HASH = "a" * 64


def _truncate(engine) -> None:
    with engine.begin() as connection:
        connection.execute(text(
            "TRUNCATE reservations, audit_entries, outbox, schedule_tasks, "
            "schedule_versions, candidate_plans, planning_snapshots, schedules, "
            "docks, warehouses, idempotency RESTART IDENTITY CASCADE"))


def _seed(engine, workspace, schedule_id, candidate_id, snapshot_id, candidate_hash,
          snapshot_hash):
    now = EPOCH
    created_by = uuid4()
    scope = PlanningScope((), (), (), EPOCH, 3600)
    schedule_payload = {
        "id": str(schedule_id), "status": "draft", "schema_version": "2.0.0",
        "row_version": 0, "created_at": now.isoformat(), "updated_at": now.isoformat(),
        "created_by": str(created_by), "name": "schedule", "scope": {
            "order_ids": [], "warehouse_ids": [], "vehicle_ids": [],
            "epoch_utc": now.isoformat(), "horizon_s": 3600},
        "active_version_id": None, "epoch_utc": now.isoformat(), "horizon_s": 3600,
    }
    zero_cost = CostBreakdown(0, 0, 0, 0, 0, 0)
    candidate = CandidatePlan(
        id=candidate_id, schedule_id=schedule_id, base_version_id=None,
        snapshot_id=snapshot_id, snapshot_hash=snapshot_hash, epoch_utc=EPOCH,
        horizon_s=3600, transport_plan=TransportPlan((), (), zero_cost),
        warehouse_plan=WarehousePlan((), (), (), zero_cost), task_assignments=(),
        objective=ObjectiveBreakdown(0, 0, 0, 0, 0, 0), content_hash=candidate_hash,
        solver_evidence_refs=(uuid4(),))
    candidate_payload = json.loads(CandidatePlanDTO.model_validate(
        dataclasses.asdict(candidate)).model_dump_json())
    with UnitOfWork(engine) as uow:
        uow.connection.execute(insert(schedules).values(
            id=schedule_id, scope_id=workspace, status="draft", created_at=now,
            updated_at=now, created_by=created_by, row_version=0,
            schema_version="2.0.0", payload=schedule_payload, name="schedule",
            active_version_id=None, epoch_utc=EPOCH, horizon_s=3600))
        uow.connection.execute(insert(planning_snapshots).values(
            id=snapshot_id, scope_id=workspace, scope_hash=HASH,
            content_hash=snapshot_hash, status="recorded", created_at=now,
            updated_at=now, created_by=created_by, row_version=0,
            schema_version="2.0.0", payload={"id": str(snapshot_id), "hash": snapshot_hash}))
        uow.connection.execute(insert(candidate_plans).values(
            id=candidate_id, scope_id=workspace, schedule_id=schedule_id,
            base_version_id=None, snapshot_id=snapshot_id, snapshot_hash=snapshot_hash,
            content_hash=candidate_hash, created_at=now, payload=candidate_payload))
    return scope


def test_commit_is_atomic_and_idempotent(database_url: str) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    workspace = uuid4()
    try:
        _truncate(engine)
        schedule_id, candidate_id, snapshot_id = uuid4(), uuid4(), uuid4()
        candidate_hash, snapshot_hash = content_hash({"candidate": "x"}), content_hash({"snapshot": "x"})
        _seed(engine, workspace, schedule_id, candidate_id, snapshot_id,
              candidate_hash, snapshot_hash)
        actor = ActorContext(actor_id=uuid4(), role=ActorRole.OPERATOR, scope_id=workspace)
        command = CommitCommand(
            schedule_id=schedule_id, candidate_id=candidate_id,
            candidate_hash=candidate_hash, expected_active_version_id=None,
            snapshot_hash=snapshot_hash, idempotency_key="commit-1",
            confirmation_token=None)
        report = ValidationReport(
            id=uuid4(), candidate_hash=candidate_hash, snapshot_hash=snapshot_hash,
            rules_version="1.0.0", valid=True, required_codes=(), checked_codes=(),
            unsupported_codes=(), violations=(), validated_at=EPOCH)
        store = PlanCommitStore(lambda **options: UnitOfWork(engine, **options), workspace)
        receipt = store.commit(command, report, actor=actor)
        replay = store.commit(command, report, actor=actor)
        assert replay == receipt
        with engine.connect() as connection:
            active = connection.execute(text(
                "select active_version_id from schedules where id = :id"),
                {"id": schedule_id}).scalar_one()
            version = connection.execute(text(
                "select version_no, content_hash, status from schedule_versions where id = :id"),
                {"id": receipt.version_id}).mappings().one()
            outbox_count = connection.execute(text("select count(*) from outbox")).scalar_one()
        assert active == receipt.version_id
        assert version["version_no"] == 1
        assert version["content_hash"] == candidate_hash
        assert version["status"] == "committed"
        assert outbox_count == 1
    finally:
        try:
            _truncate(engine)
        finally:
            engine.dispose()


def _calendar_payload() -> dict:
    return {"schema_version": "2.0.0", "epoch_utc": EPOCH.isoformat(), "version": 0,
            "intervals": [{"start_s": 0, "end_s": 3600, "available_units": 1}]}


def _entity_payload(entity_id, status, created_by, extra: dict) -> dict:
    payload = {"id": str(entity_id), "status": status, "schema_version": "2.0.0",
               "row_version": 0, "created_at": EPOCH.isoformat(),
               "updated_at": EPOCH.isoformat(), "created_by": str(created_by)}
    payload.update(extra)
    return payload


def _insert_candidate(engine, workspace, schedule_id, candidate_id, snapshot_id,
                      candidate_hash, snapshot_hash, assignments=()):
    zero_cost = CostBreakdown(0, 0, 0, 0, 0, 0)
    candidate = CandidatePlan(
        id=candidate_id, schedule_id=schedule_id, base_version_id=None,
        snapshot_id=snapshot_id, snapshot_hash=snapshot_hash, epoch_utc=EPOCH,
        horizon_s=3600, transport_plan=TransportPlan((), (), zero_cost),
        warehouse_plan=WarehousePlan((), (), (), zero_cost),
        task_assignments=tuple(assignments), objective=ObjectiveBreakdown(0, 0, 0, 0, 0, 0),
        content_hash=candidate_hash, solver_evidence_refs=(uuid4(),))
    payload = json.loads(CandidatePlanDTO.model_validate(
        dataclasses.asdict(candidate)).model_dump_json())
    with UnitOfWork(engine) as uow:
        uow.connection.execute(insert(candidate_plans).values(
            id=candidate_id, scope_id=workspace, schedule_id=schedule_id,
            base_version_id=None, snapshot_id=snapshot_id, snapshot_hash=snapshot_hash,
            content_hash=candidate_hash, created_at=EPOCH, payload=payload))


def test_last_dock_capacity_allows_exactly_one_commit(database_url: str) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    workspace, schedule_id, snapshot_id = uuid4(), uuid4(), uuid4()
    warehouse_id, dock_id, created_by = uuid4(), uuid4(), uuid4()
    snapshot_hash = content_hash({"snapshot": "dock"})
    schedule_payload = _entity_payload(schedule_id, "draft", created_by, {
        "name": "schedule", "scope": {"order_ids": [], "warehouse_ids": [],
        "vehicle_ids": [], "epoch_utc": EPOCH.isoformat(), "horizon_s": 3600},
        "active_version_id": None, "epoch_utc": EPOCH.isoformat(), "horizon_s": 3600})
    schedule_payload["name"] = "schedule"
    schedule_payload["scope"] = {"order_ids": [], "warehouse_ids": [],
        "vehicle_ids": [], "epoch_utc": EPOCH.isoformat(), "horizon_s": 3600}
    schedule_payload["active_version_id"] = None
    schedule_payload["epoch_utc"] = EPOCH.isoformat()
    schedule_payload["horizon_s"] = 3600
    warehouse_payload = _entity_payload(warehouse_id, "active", created_by, {
        "code": "WH1", "name": "WH1", "node_id": str(uuid4()), "timezone": "UTC",
        "calendar": _calendar_payload()})
    dock_payload = _entity_payload(dock_id, "available", created_by, {
        "warehouse_id": str(warehouse_id), "code": "D1", "supported_operations": ["load"],
        "allowed_zone_ids": [], "calendar": _calendar_payload()})
    try:
        _truncate(engine)
        with UnitOfWork(engine) as uow:
            uow.connection.execute(insert(warehouses).values(
                id=warehouse_id, scope_id=workspace, status="active", created_at=EPOCH,
                updated_at=EPOCH, created_by=created_by, row_version=0,
                schema_version="2.0.0", payload=warehouse_payload, code="WH1"))
            uow.connection.execute(insert(docks).values(
                id=dock_id, scope_id=workspace, status="available", created_at=EPOCH,
                updated_at=EPOCH, created_by=created_by, row_version=0,
                schema_version="2.0.0", payload=dock_payload, warehouse_id=warehouse_id,
                code="D1"))
        with UnitOfWork(engine) as uow:
            uow.connection.execute(insert(schedules).values(
                id=schedule_id, scope_id=workspace, status="draft", created_at=EPOCH,
                updated_at=EPOCH, created_by=created_by, row_version=0,
                schema_version="2.0.0", payload=schedule_payload, name="schedule",
                active_version_id=None, epoch_utc=EPOCH, horizon_s=3600))
            uow.connection.execute(insert(planning_snapshots).values(
                id=snapshot_id, scope_id=workspace, scope_hash=HASH,
                content_hash=snapshot_hash, status="recorded", created_at=EPOCH,
                updated_at=EPOCH, created_by=created_by, row_version=0,
                schema_version="2.0.0", payload={"id": str(snapshot_id), "hash": snapshot_hash}))
        actor = ActorContext(actor_id=uuid4(), role=ActorRole.OPERATOR, scope_id=workspace)
        candidate1, candidate2 = uuid4(), uuid4()
        hash1, hash2 = content_hash({"candidate": 1}), content_hash({"candidate": 2})
        task1 = ScheduleTask(id=uuid4(), status=EntityState.PLANNED, created_at=EPOCH,
            updated_at=EPOCH, row_version=0, schema_version="2.0.0",
            created_by=actor.actor_id, version_id=candidate1, task_id=uuid4(),
            task_kind=TaskKind.WAREHOUSE, assigned_resource_ids=(dock_id,),
            planned_start_s=0, planned_end_s=10, sequence=0)
        task2 = dataclasses.replace(task1, id=uuid4(), version_id=candidate2,
                                    task_id=uuid4())
        _insert_candidate(engine, workspace, schedule_id, candidate1, snapshot_id,
                          hash1, snapshot_hash, (task1,))
        _insert_candidate(engine, workspace, schedule_id, candidate2, snapshot_id,
                          hash2, snapshot_hash, (task2,))
        store = PlanCommitStore(lambda **options: UnitOfWork(engine, **options), workspace)
        report1 = ValidationReport(id=uuid4(), candidate_hash=hash1,
            snapshot_hash=snapshot_hash, rules_version="1.0.0", valid=True,
            required_codes=(), checked_codes=(), unsupported_codes=(), violations=(),
            validated_at=EPOCH)
        command1 = CommitCommand(schedule_id=schedule_id, candidate_id=candidate1,
            candidate_hash=hash1, expected_active_version_id=None,
            snapshot_hash=snapshot_hash, idempotency_key="dock-1",
            confirmation_token=None)
        receipt = store.commit(command1, report1, actor=actor)
        report2 = dataclasses.replace(report1, id=uuid4(), candidate_hash=hash2)
        command2 = dataclasses.replace(command1, candidate_id=candidate2,
            candidate_hash=hash2, expected_active_version_id=receipt.version_id,
            idempotency_key="dock-2")
        with pytest.raises(ServiceError) as failure:
            store.commit(command2, report2, actor=actor)
        assert failure.value.code == ErrorCode.RESOURCE_CONFLICT
        with engine.connect() as connection:
            assert connection.execute(text("select count(*) from schedule_versions")).scalar_one() == 1
            assert connection.execute(text("select count(*) from reservations")).scalar_one() == 1
    finally:
        try:
            _truncate(engine)
        finally:
            engine.dispose()
