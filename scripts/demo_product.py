"""Repeatable first-product demo: seed -> schedule -> candidate -> commit -> current version.

This is a local smoke for the real PostgreSQL chain, not a Gate and not a substitute for the
independent validator/acceptance suite. Run after `alembic upgrade head`:

    $env:DEMO_DATABASE_URL='postgresql+psycopg://test:test@127.0.0.1:55432/dsh_test'
    .venv/Scripts/python.exe scripts/demo_product.py
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import create_engine

from logistics_backend.application.schedule import ScheduleService
from logistics_backend.cli.seed import seed
from logistics_backend.persistence.snapshots import PlanningSnapshotStore
from logistics_backend.persistence.uow import UnitOfWork
from logistics_backend.persistence.version_store import PlanCommitStore
from logistics_contracts.mapping import (
    plan_dto,
    problem_dto,
    scope_dto,
    warehouse_problem_dto,
    warehouse_solution_dto,
)
from logistics_contracts.planning import CommitCommandDTO
from logistics_contracts.schedules import CandidateCreate, CommitRequest, ScheduleCreate
from logistics_domain.planning import (
    CostBreakdown,
    EngineMetadata,
    ObjectiveBreakdown,
    ObjectivePolicy,
    OperationAssignment,
    PlanningScope,
    ResourceRequirement,
    SolverEvidence,
    SolveBudget,
    SolveStatus,
    TransportPlan,
    TravelMatrix,
    WarehouseTask,
    DisturbanceWeights,
)
from logistics_domain.primitives import Load, TimeWindow
from logistics_domain.resources import CargoType, OperationKind
from logistics_domain.runtime import ActorContext
from logistics_domain.states import ActorRole, EntityState, ResourceKind
from logistics_domain.transport import TransportProblem, VehicleState
from logistics_domain.warehouse import WarehouseProblem, WarehouseSolution

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "data" / "scenarios" / "tiny_master.json"


def main() -> int:
    url = os.environ.get("DEMO_DATABASE_URL") or os.environ.get("LOGISTICS_DATABASE_URL")
    if not url:
        raise SystemExit("set DEMO_DATABASE_URL (isolated PostgreSQL) before running")
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    scope_id = UUID(scenario["scope_id"])
    seed("tiny_master", url)

    orders = tuple(UUID(value) for value in scenario["order_ids"])
    warehouse_ids = tuple(UUID(value) for value in scenario["warehouse_ids"])
    vehicle_ids = tuple(UUID(value) for value in scenario["vehicle_ids"])
    epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)

    engine = create_engine(url, pool_pre_ping=True)
    factory = lambda **options: UnitOfWork(engine, **options)
    snapshots = PlanningSnapshotStore(factory, scope_id)
    commits = PlanCommitStore(factory, scope_id)
    schedules = ScheduleService(factory, scope_id, snapshots, commits)
    actor = ActorContext(actor_id=uuid4(), role=ActorRole.OPERATOR, scope_id=scope_id)

    scope = PlanningScope(orders, warehouse_ids, vehicle_ids, epoch, 86400)
    snapshot = snapshots.capture(scope)
    matrix = TravelMatrix(uuid4(), 1, (uuid4(),), ((0,),), ((0,),), "demo", epoch, "a" * 64)
    vehicle = VehicleState(vehicle_id=vehicle_ids[0], driver_id=None,
        start_node_id=matrix.node_ids[0], end_node_id=matrix.node_ids[0],
        start_load=Load(0, 0), capacity_weight_g=10000, capacity_volume_cm3=10000,
        setpoint_decic=40, available_window=TimeWindow(0, 86400), max_drive_s=3600,
        allowed_cargo_types=(CargoType.GENERAL,))
    policy = ObjectivePolicy("1.0.0", 0, 0, 0, DisturbanceWeights(0, 0, 0, 0))
    transport = TransportProblem(snapshot, (), (vehicle,), matrix, (), policy)

    warehouse_task = WarehouseTask(id=uuid4(), status=EntityState.PENDING,
        created_at=epoch, updated_at=epoch, row_version=0, schema_version="2.0.0",
        created_by=actor.actor_id, order_id=orders[0], warehouse_id=snapshot.resources.warehouses[0].id,
        kind=OperationKind.RECEIVE, duration_s=10, window=TimeWindow(0, 100),
        predecessor_ids=(), requirements=(ResourceRequirement(ResourceKind.DOCK,
            (snapshot.resources.docks[0].id,), 1),), setup_class="receive")
    warehouse_problem = WarehouseProblem(snapshot, (warehouse_task,), policy,
        SolveBudget(1000, epoch, 1, 0))
    metadata = EngineMetadata("ortools_cp_sat", "9", "a" * 64, 0, 1, "b" * 64,
        1, 0, "optimal", True, None, None)
    evidence = SolverEvidence(uuid4(), "cp_sat", "9", "b" * 64, "a" * 64, "a" * 64,
        SolveStatus.OPTIMAL, None)
    warehouse_solution = WarehouseSolution(SolveStatus.OPTIMAL, metadata,
        (OperationAssignment(warehouse_task.id, snapshot.resources.docks[0].id, 0, 10, 1),),
        (), (), ObjectiveBreakdown(100, 0, 0, 0, 0, 100), None, (), (evidence,))

    schedule = schedules.create(ScheduleCreate(name=f"demo-{uuid4().hex[:8]}",
        scope=scope_dto(snapshot.scope)), actor)
    plan = TransportPlan((), orders, CostBreakdown(0, 0, 0, 0, 0, 0))
    candidate = schedules.create_candidate(schedule.schedule_id, CandidateCreate(
        problem=problem_dto(transport), plan=plan_dto(plan), stops=(),
        solver_evidence_refs=(uuid4(),),
        warehouse_problem=warehouse_problem_dto(warehouse_problem),
        warehouse_solution=warehouse_solution_dto(warehouse_solution)), actor)
    command = CommitCommandDTO(schedule_id=schedule.schedule_id,
        candidate_id=candidate.candidate_id, candidate_hash=candidate.content_hash,
        expected_active_version_id=None, snapshot_hash=snapshot.hash,
        idempotency_key=f"demo-{uuid4().hex[:8]}", confirmation_token=None)
    receipt = schedules.commit(schedule.schedule_id, CommitRequest(command=command),
                               actor, uuid4())
    current = schedules.current_version(schedule.schedule_id, actor)
    engine.dispose()
    print(json.dumps({
        "schedule_id": str(schedule.schedule_id),
        "candidate_id": str(candidate.candidate_id),
        "candidate_valid": candidate.valid,
        "version_no": receipt.version_no,
        "version_id": str(receipt.version_id),
        "current_tasks": len(current.tasks),
        "current_hash": current.version.content_hash,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
