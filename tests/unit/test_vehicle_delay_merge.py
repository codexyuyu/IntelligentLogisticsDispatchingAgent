"""合并局部解：只替换目标车辆，其余路由原样保留，合并结果必须能独立通过校验。"""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from logistics_backend.application.optimization import build_transport_problem
from logistics_backend.application.scenario_import import prepare_scenario
from logistics_backend.application.vehicle_delay_merge import merge_local_solution
from logistics_backend.application.vehicle_delay_reschedule import (
    VehicleDelayRequest,
    resolve_vehicle_delay,
)
from logistics_contracts.integration import ScenarioImport
from logistics_contracts.mapping import budget_dto, policy_dto, scope_dto
from logistics_contracts.planning import MatrixRefDTO
from logistics_contracts.transport import TransportRequestDTO
from logistics_domain.planning import DisturbanceWeights, ObjectivePolicy, SolveBudget
from logistics_optimization.transport.solver import OrToolsTransportSolver
from logistics_optimization.validation.transport import validate_transport

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / "data" / "scenarios" / "partner_coldchain_synthetic.json"


def _budget(ms=4000):
    return SolveBudget(wall_time_ms=ms,
        deadline_utc=(datetime.now(UTC) + timedelta(seconds=120)).replace(microsecond=0),
        max_candidates=1, seed=0, worker_count=1, deterministic_test_mode=False)


@pytest.fixture(scope="module")
def base():
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


@pytest.fixture(scope="module")
def resolved(base):
    problem, plan, stops = base
    out = resolve_vehicle_delay(problem, plan, stops,
        VehicleDelayRequest(vehicle_id=plan.routes[0].vehicle_id, delay_s=60, event_time_s=0))
    assert out.status == "resolved", (out.reason, out.detail)
    return out


def test_merge_replaces_only_target_vehicle(base, resolved):
    problem, plan, stops = base
    target = plan.routes[0].vehicle_id

    # 造一条属于「另一辆车」的路由，验证它不会被合掉
    other_route = replace(plan.routes[0], id=uuid4(), vehicle_id=uuid4())
    other_stops = tuple(replace(s, route_id=other_route.id) for s in stops)
    base_plan = replace(plan, routes=(plan.routes[0], other_route))
    base_stops = stops + other_stops

    merged, merged_stops = merge_local_solution(base_plan, base_stops, resolved.solution, target)

    assert other_route in merged.routes, "未受影响车辆的路由必须原样保留"
    assert all(r.vehicle_id != target or r in resolved.solution.candidate.routes
               for r in merged.routes), "目标车辆只应保留重解后的路由"
    assert len(merged.routes) == 2
    # 未受影响车辆的停靠点一个不少
    assert sum(1 for s in merged_stops if s.route_id == other_route.id) == len(stops)


def test_merge_result_passes_independent_validation(base, resolved):
    problem, plan, stops = base

    merged, merged_stops = merge_local_solution(plan, stops, resolved.solution,
                                                plan.routes[0].vehicle_id)

    report = validate_transport(merged, problem, merged_stops)
    assert report.valid, [v.code for v in report.violations]
    assert merged.cost.total_cents == sum(r.cost.total_cents for r in merged.routes)


def test_merge_requires_candidate():
    class _Empty:
        candidate = None
        optional_unserved_order_ids = ()
        stops = ()

    with pytest.raises(ValueError):
        merge_local_solution(None, (), _Empty(), uuid4())
