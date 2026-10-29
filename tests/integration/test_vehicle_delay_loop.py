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


MASTER_SCOPE = UUID("11111111-1111-4111-8111-111111111111")
"""主数据由既有 seed 命令灌入该固定 scope；合成场景与 tiny_master 共用同一套 id。"""


def _cleanup(engine) -> None:
    """清掉流程性表，保留主数据；与既有 P03-04 集成测试的清理口径一致。"""

    with engine.begin() as connection:
        connection.execute(text(
            "TRUNCATE reservations, audit_entries, outbox, schedule_tasks, "
            "schedule_versions, candidate_plans, validation_reports, decision_records, "
            "planning_snapshots, schedules, idempotency RESTART IDENTITY CASCADE"))


def test_propose_and_approve_commits_new_version(database_url: str):
    from logistics_backend.cli.seed import seed

    engine = create_engine(database_url, pool_pre_ping=True)
    _cleanup(engine)
    seed("tiny_master", database_url)  # 幂等：on_conflict_do_nothing

    scope = MASTER_SCOPE
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

    created = schedules.create(ScheduleCreate(name=f"vehicle-delay-{uuid4().hex[:8]}",
                                              scope=scope_dto(problem.snapshot.scope)), actor)
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
    assert len(restored_plan.routes) == len(base_plan.routes)
    assert len(restored_stops) == len(base_stops)
    assert restored_plan.cost == base_plan.cost
    assert [s.service_start_s for s in restored_stops] == [s.service_start_s for s in base_stops]

    # 事件驱动入口：基于上一次批准的基线再处置一次
    def read_event(event_id, _actor):
        return {"kind": "vehicle_delay",
                "payload": {"vehicle_id": str(base_plan.routes[0].vehicle_id),
                            "delay_s": 30, "event_time_s": 0}}

    second = approval.prepare_from_event(
        actor=actor, event_id=uuid4(), schedule_id=schedule_id, read_event=read_event)
    assert second["candidate_valid"] is True, second
    assert second["committed"] is False
    assert second["decision_id"] != proposal["decision_id"]


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
    schedule_id = schedules.create(ScheduleCreate(
        name=f"vehicle-delay-{uuid4().hex[:8]}",
        scope=scope_dto(problem.snapshot.scope)), actor).schedule_id

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


def _proposal(database_url: str):
    """在共享主数据 scope 上准备一份待审方案（propose 之前不发版本）。"""

    from logistics_backend.cli.seed import seed

    engine = create_engine(database_url, pool_pre_ping=True)
    _cleanup(engine)
    seed("tiny_master", database_url)

    scope = MASTER_SCOPE
    actor = ActorContext(actor_id=uuid4(), role=ActorRole.OPERATOR, scope_id=scope)

    def factory(**options):
        return UnitOfWork(engine, **options)

    problem, base_plan, base_stops = _live_problem()
    outcome = resolve_vehicle_delay(
        problem, base_plan, base_stops,
        VehicleDelayRequest(vehicle_id=base_plan.routes[0].vehicle_id, delay_s=60, event_time_s=0))
    assert outcome.status == "resolved", (outcome.reason, outcome.detail)

    schedules = ScheduleService(factory, scope, commits=PlanCommitStore(factory, scope))
    approval = VehicleDelayApprovalService(
        uow_factory=factory, scope_id=scope,
        decisions=DecisionService(factory, scope), schedules=schedules)
    schedule_id = schedules.create(ScheduleCreate(
        name=f"vehicle-delay-{uuid4().hex[:8]}",
        scope=scope_dto(problem.snapshot.scope)), actor).schedule_id

    proposal = approval.propose(actor=actor, schedule_id=schedule_id, problem=problem,
                                base_plan=base_plan, base_stops=base_stops,
                                outcome=outcome, event_id=uuid4())
    return engine, actor, approval, schedule_id, proposal


def _version_count(engine, schedule_id) -> int:
    with engine.connect() as connection:
        return connection.execute(text(
            "select count(*) from schedule_versions where schedule_id = :s"),
            {"s": schedule_id}).scalar_one()


def test_approve_is_idempotent(database_url: str):
    engine, actor, approval, schedule_id, proposal = _proposal(database_url)
    decision_id = UUID(proposal["decision_id"])

    first = approval.approve(actor=actor, decision_id=decision_id, trace_id=uuid4())
    assert first["committed"] is True
    assert first["idempotent"] is False
    assert first["version_no"] == 1
    assert _version_count(engine, schedule_id) == 1

    second = approval.approve(actor=actor, decision_id=decision_id, trace_id=uuid4())
    assert second["idempotent"] is True
    assert second["committed"] is True
    assert second["version_id"] == first["version_id"]
    assert second["version_no"] == first["version_no"]
    assert second["content_hash"] == first["content_hash"]

    # 关键：重复批准不得再产生一个版本
    assert _version_count(engine, schedule_id) == 1

    third = approval.approve(actor=actor, decision_id=decision_id, trace_id=uuid4())
    assert third["version_id"] == first["version_id"]
    assert _version_count(engine, schedule_id) == 1


def test_rejected_decision_cannot_be_approved(database_url: str):
    from logistics_backend.errors import ServiceError
    from logistics_domain.states import ErrorCode

    engine, actor, approval, schedule_id, proposal = _proposal(database_url)
    decision_id = UUID(proposal["decision_id"])

    first = approval.reject(actor=actor, decision_id=decision_id)
    assert first["committed"] is False and first["idempotent"] is False

    again = approval.reject(actor=actor, decision_id=decision_id)
    assert again["idempotent"] is True

    with pytest.raises(ServiceError) as exc:
        approval.approve(actor=actor, decision_id=decision_id, trace_id=uuid4())
    assert exc.value.code is ErrorCode.INVALID_TRANSITION
    assert _version_count(engine, schedule_id) == 0


def test_approved_decision_cannot_be_rejected(database_url: str):
    from logistics_backend.errors import ServiceError
    from logistics_domain.states import ErrorCode

    engine, actor, approval, schedule_id, proposal = _proposal(database_url)
    decision_id = UUID(proposal["decision_id"])
    approval.approve(actor=actor, decision_id=decision_id, trace_id=uuid4())

    with pytest.raises(ServiceError) as exc:
        approval.reject(actor=actor, decision_id=decision_id)
    assert exc.value.code is ErrorCode.INVALID_TRANSITION
    assert _version_count(engine, schedule_id) == 1
