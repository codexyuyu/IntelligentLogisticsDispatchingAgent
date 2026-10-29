"""车辆延误局部重解：真实求解器 + 独立校验 + 显式失败。

不构造示意路线：无法求解或校验不通过时，服务必须返回 not_resolved。
"""

import json
from pathlib import Path
from uuid import UUID

import pytest

from logistics_backend.application.optimization import build_transport_problem
from logistics_backend.application.scenario_import import prepare_scenario
from logistics_backend.application.vehicle_delay_reschedule import (
    NOT_RESOLVED,
    RESOLVED,
    VehicleDelayRequest,
    build_local_problem,
    remaining_stop_order_ids,
    resolve_vehicle_delay,
)
from logistics_contracts.integration import ScenarioImport
from logistics_contracts.mapping import budget_dto, policy_dto, scope_dto
from logistics_contracts.planning import MatrixRefDTO
from logistics_contracts.transport import TransportRequestDTO
from logistics_domain.planning import DisturbanceWeights, ObjectivePolicy, SolveBudget
from logistics_optimization.transport.solver import OrToolsTransportSolver

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / "data" / "scenarios" / "partner_coldchain_synthetic.json"
HORIZON_S = 86400


def _policy():
    return ObjectivePolicy("1.0.0", 100000, 1, 1, DisturbanceWeights(0, 0, 0, 0))


def _budget(ms=4000):
    from datetime import UTC, datetime, timedelta

    return SolveBudget(
        wall_time_ms=ms,
        deadline_utc=(datetime.now(UTC) + timedelta(seconds=120)).replace(microsecond=0),
        max_candidates=1,
        seed=0,
        worker_count=1,
        deterministic_test_mode=False,
    )


@pytest.fixture(scope="module")
def base():
    """真实场景 → 真实求解，得到基础运输方案。"""

    payload = json.loads(SCENARIO.read_text(encoding="utf-8"))
    command = ScenarioImport.model_validate(payload)
    prepared = prepare_scenario(command)
    assert prepared["status"] == "checked", prepared
    snapshot = ScenarioImport.model_validate(prepared["payload"]).snapshot.to_domain()
    matrix = snapshot.matrices[0]
    policy = _policy()
    request = TransportRequestDTO(
        scope=scope_dto(snapshot.scope),
        order_ids=snapshot.scope.order_ids,
        vehicle_ids=snapshot.scope.vehicle_ids,
        matrix_ref=MatrixRefDTO(matrix_id=matrix.id, version=matrix.version, hash=matrix.hash),
        budget=budget_dto(_budget()),
        objective_policy=policy_dto(policy),
    )
    problem = build_transport_problem(snapshot, request)
    solution = OrToolsTransportSolver().solve(problem, _budget())
    assert solution.candidate is not None, solution.status
    return problem, solution.candidate, solution.stops


def test_base_plan_is_feasible_and_has_routes(base):
    problem, plan, stops = base
    assert plan.routes
    assert stops
    assert problem.vehicles


def test_small_delay_resolves_with_real_solver_output(base):
    problem, plan, stops = base
    vehicle_id = plan.routes[0].vehicle_id

    outcome = resolve_vehicle_delay(
        problem, plan, stops,
        VehicleDelayRequest(vehicle_id=vehicle_id, delay_s=60, event_time_s=0),
    )

    assert outcome.status == RESOLVED, (outcome.reason, outcome.detail)
    assert outcome.validation is not None and outcome.validation.valid
    assert outcome.solution is not None and outcome.solution.candidate is not None
    # 求解证据必须来自真实引擎，不是拼出来的
    assert outcome.solution.solver_evidence
    assert any(e.engine_name for e in outcome.solution.solver_evidence)
    # 受影响订单必须是该车在原方案里真实存在的订单
    plan_orders = set(problem.snapshot.scope.order_ids)
    assert outcome.affected_order_ids
    assert set(outcome.affected_order_ids) <= plan_orders
    # 局部问题只含这一个车辆
    assert len(outcome.local_problem.vehicles) == 1
    assert outcome.local_problem.vehicles[0].vehicle_id == vehicle_id


def test_delay_beyond_vehicle_window_is_not_resolved(base):
    problem, plan, stops = base
    vehicle_id = plan.routes[0].vehicle_id

    outcome = resolve_vehicle_delay(
        problem, plan, stops,
        VehicleDelayRequest(vehicle_id=vehicle_id, delay_s=HORIZON_S, event_time_s=0),
    )

    assert outcome.status == NOT_RESOLVED
    assert outcome.reason in {"delay_exceeds_vehicle_window", "local_transport_infeasible"}


def test_unknown_vehicle_is_rejected(base):
    problem, plan, stops = base

    outcome = resolve_vehicle_delay(
        problem, plan, stops,
        VehicleDelayRequest(vehicle_id=UUID(int=424242), delay_s=60, event_time_s=0),
    )

    assert outcome.status == NOT_RESOLVED
    assert outcome.reason == "vehicle_not_in_plan"
    assert outcome.solution is None


def test_event_after_finished_route_has_nothing_to_resolve(base):
    problem, plan, stops = base
    vehicle_id = plan.routes[0].vehicle_id

    outcome = resolve_vehicle_delay(
        problem, plan, stops,
        VehicleDelayRequest(vehicle_id=vehicle_id, delay_s=60, event_time_s=HORIZON_S),
    )

    assert outcome.status == NOT_RESOLVED
    assert outcome.reason == "no_remaining_service_after_event"


def test_remaining_orders_skip_already_served_stops(base):
    problem, plan, stops = base
    route = plan.routes[0]
    route_stops = sorted(
        (s for s in stops if s.route_id == route.id), key=lambda s: s.sequence
    )
    if len(route_stops) < 2:
        pytest.skip("场景中该车只有一个停靠点，无法验证已完成站点的过滤")

    # 取货段被切掉后，订单仍有送货段，按订单去重后数量可能不变；
    # 因此这里验证两点：结果单调收缩，且切点超过最后一站后彻底为空。
    mid = route_stops[1].service_start_s + 1
    early = remaining_stop_order_ids(problem, plan, stops, route.vehicle_id, 0)
    later = remaining_stop_order_ids(problem, plan, stops, route.vehicle_id, mid)
    assert set(later) <= set(early)

    after_last = route_stops[-1].service_start_s + 1
    assert remaining_stop_order_ids(problem, plan, stops, route.vehicle_id, after_last) == ()


def test_request_validates_budget_and_delay():
    with pytest.raises(ValueError):
        VehicleDelayRequest(vehicle_id=UUID(int=1), delay_s=-1, event_time_s=0)
    with pytest.raises(ValueError):
        VehicleDelayRequest(vehicle_id=UUID(int=1), delay_s=10, event_time_s=0, budget_ms=50)


def test_build_local_problem_pins_single_vehicle(base):
    problem, plan, stops = base
    vehicle_id = plan.routes[0].vehicle_id

    local, order_ids, reason = build_local_problem(
        problem, plan, stops,
        VehicleDelayRequest(vehicle_id=vehicle_id, delay_s=120, event_time_s=30),
    )

    assert reason is None
    assert local is not None
    assert len(local.vehicles) == 1
    # 可用窗口下界必须被推到 event_time + delay
    assert local.vehicles[0].available_window.earliest_s >= 30 + 120
    # 只保留受影响订单的节点
    assert {n.order_id for n in local.nodes if n.order_id} == set(order_ids)
