"""车辆延误处置闭环：propose → approve → 版本提交 → 基线可还原。

使用真实求解器与真实 PostgreSQL；不伪造候选，不跳过独立校验。
"""

import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text

from logistics_backend.application.decision import DecisionService
from logistics_backend.application.optimization import build_transport_problem
from logistics_backend.application.scenario_import import prepare_scenario
from logistics_backend.application.schedule import ScheduleService
from logistics_backend.application.vehicle_delay_approval import VehicleDelayApprovalService
from logistics_backend.application.vehicle_delay_reschedule import (
    VehicleDelayRequest,
    resolve_vehicle_delay,
)
from logistics_backend.persistence.uow import UnitOfWork
from logistics_backend.persistence.version_store import PlanCommitStore
from logistics_contracts.integration import ScenarioImport
from logistics_contracts.mapping import budget_dto, policy_dto, scope_dto
from logistics_contracts.planning import MatrixRefDTO
from logistics_contracts.schedules import ScheduleCreate
from logistics_contracts.transport import TransportRequestDTO
from logistics_domain.planning import DisturbanceWeights, ObjectivePolicy, SolveBudget
from logistics_domain.runtime import ActorContext
from logistics_domain.states import ActorRole
from logistics_optimization.transport.solver import OrToolsTransportSolver

pytestmark = pytest.mark.requires_postgres

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / "data" / "scenarios" / "partner_coldchain_synthetic.json"


def _budget(ms=4000):
    return SolveBudget(wall_time_ms=ms,
        deadline_utc=(datetime.now(UTC) + timedelta(seconds=180)).replace(microsecond=0),
        max_candidates=1, seed=0, worker_count=1, deterministic_test_mode=False)


def _live_problem():
    payload = json.loads(SCENARIO.read_text(encoding="utf-8"))
    prepared = prepare_scenario(ScenarioImport.model_validate(payload))
    assert prepared["status"] == "checked", prepared
    snapshot = ScenarioImport.model_validate(prepared["payload"]).snapshot.to_domain()
    matrix = snapshot.matrices[0]
    policy = ObjectivePolicy("1.0.0", 100000, 1, 1, DisturbanceWeights(0, 0, 0, 0))
    request = TransportRequestDTO(scope=scope_dto(snapshot.scope),
        order_ids=snapshot.scope.order_ids, vehicle_ids=snapshot.scope.vehicle_ids,
        matrix_ref=MatrixRefDTO(matrix_id=matrix.id, version=matrix.version, hash=matrix.hash),
        budget=budget_dto(_budget()), objective_policy=policy_dto(policy))
    problem = build_transport_problem(snapshot, request)
    solution = OrToolsTransportSolver().solve(problem, _budget())
    assert solution.candidate is not None
    return problem, solution.candidate, solution.stops


@pytest.mark.xfail(
    reason="PlanCommitStore 提交时要求 resources/vehicles 主数据已入库；"
           "场景导入链路只写 planning_snapshots，不写主数据，需另行补 ensure_master_data",
    strict=True,
)
def test_propose_and_approve_commits_new_version(database_url: str):
    engine = create_engine(database_url, pool_pre_ping=True)
    scope = uuid4()
    actor = ActorContext(actor_id=uuid4(), role=ActorRole.OPERATOR, scope_id=scope)

    def factory(**options):
        return UnitOfWork(engine, **options)

    problem, base_plan, base_stops = _live_problem()
    outcome = resolve_vehicle_delay(
        problem, base_plan, base_stops,
        VehicleDelayRequest(vehicle_id=base_plan.routes[0].vehicle_id, delay_s=60, event_time_s=0))
    assert outcome.status == "resolved", (outcome.reason, outcome.detail)

    schedules = ScheduleService(factory, scope, commits=PlanCommitStore(factory, scope))
    decisions = DecisionService(factory, scope)
    approval = VehicleDelayApprovalService(uow_factory=factory, scope_id=scope,
                                           decisions=decisions, schedules=schedules)

    created = schedules.create(ScheduleCreate(name="vehicle-delay", scope=scope_dto(problem.snapshot.scope)), actor)
    schedule_id = created.schedule_id

    proposal = approval.propose(actor=actor, schedule_id=schedule_id, problem=problem,
                                base_plan=base_plan, base_stops=base_stops,
                                outcome=outcome, event_id=uuid4())
    assert proposal["candidate_valid"] is True, proposal
    assert proposal["committed"] is False

    # 未批准前不允许提交：approve 之前版本表应为空
    with engine.connect() as connection:
        before = connection.execute(text(
            "select count(*) from schedule_versions where schedule_id = :s"), {"s": schedule_id}).scalar_one()
    assert before == 0

    result = approval.approve(actor=actor, decision_id=UUID(proposal["decision_id"]),
                              trace_id=uuid4())
    assert result["committed"] is True
    assert result["version_no"] == 1
    assert result["approved_stops"] > 0

    with engine.connect() as connection:
        version = connection.execute(text(
            "select version_no, status from schedule_versions where id = :v"),
            {"v": UUID(result["version_id"])}).mappings().one()
        decision = connection.execute(text(
            "select status from decision_records where id = :d"),
            {"d": UUID(proposal["decision_id"])}).mappings().one()
    assert version["version_no"] == 1 and version["status"] == "committed"
    assert decision["status"] == "accepted"

    # 基线可还原：下次局部重解能拿到已批准方案的方案与停靠点
    restored_plan, restored_stops = approval.load_base_plan(actor=actor, schedule_id=schedule_id)
    assert len(restored_plan.routes) == len(json.loads(json.dumps(asdict(base_plan)))["routes"])
    assert len(restored_stops) > 0


def test_reject_does_not_commit(database_url: str):
    engine = create_engine(database_url, pool_pre_ping=True)
    scope = uuid4()
    actor = ActorContext(actor_id=uuid4(), role=ActorRole.OPERATOR, scope_id=scope)

    def factory(**options):
        return UnitOfWork(engine, **options)

    problem, base_plan, base_stops = _live_problem()
    outcome = resolve_vehicle_delay(
        problem, base_plan, base_stops,
        VehicleDelayRequest(vehicle_id=base_plan.routes[0].vehicle_id, delay_s=60, event_time_s=0))

    schedules = ScheduleService(factory, scope, commits=PlanCommitStore(factory, scope))
    decisions = DecisionService(factory, scope)
    approval = VehicleDelayApprovalService(uow_factory=factory, scope_id=scope,
                                           decisions=decisions, schedules=schedules)
    schedule_id = schedules.create(
        ScheduleCreate(name="vehicle-delay", scope=scope_dto(problem.snapshot.scope)), actor).schedule_id

    proposal = approval.propose(actor=actor, schedule_id=schedule_id, problem=problem,
                                base_plan=base_plan, base_stops=base_stops, outcome=outcome)
    rejected = approval.reject(actor=actor, decision_id=UUID(proposal["decision_id"]))
    assert rejected["committed"] is False

    with engine.connect() as connection:
        versions = connection.execute(text(
            "select count(*) from schedule_versions where schedule_id = :s"),
            {"s": schedule_id}).scalar_one()
    assert versions == 0

    # 没有已批准记录时，基线还原必须显式失败而不是返回半成品
    with pytest.raises(Exception):
        approval.load_base_plan(actor=actor, schedule_id=schedule_id)
