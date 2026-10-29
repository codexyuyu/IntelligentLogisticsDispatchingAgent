"""Vehicle-delay local reschedule (V1 vertical slice).

只重解「延误车辆未完成的订单」，其余车辆保持原路线不动。

设计约束（刻意为之）：
* 求解必须来自真实 OR-Tools；没有可用解就返回 not_resolved，绝不构造示意路线；
* 独立校验不通过同样 not_resolved，不把求解器的 feasible 当成业务可通过；
* 本模块不写数据库、不产生版本、不替调用方做提交决定。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from logistics_domain.planning import (
    RouteStop,
    SolveBudget,
    SolveStatus,
    TransportPlan,
    ValidationReport,
)
from logistics_domain.primitives import TimeWindow
from logistics_domain.transport import RoutingNodeKind, TransportProblem, TransportSolution
from logistics_optimization.transport.solver import OrToolsTransportSolver
from logistics_optimization.validation.transport import validate_transport

RESOLVED = "resolved"
NOT_RESOLVED = "not_resolved"

FEASIBLE_STATUSES = (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE)


@dataclass(frozen=True, slots=True)
class VehicleDelayRequest:
    """一次车辆延误重解请求。时间单位为秒，与快照 epoch 对齐。"""

    vehicle_id: UUID
    delay_s: int
    event_time_s: int
    budget_ms: int = 4000

    def __post_init__(self) -> None:
        if self.delay_s < 0:
            raise ValueError("delay_s must be non-negative")
        if self.event_time_s < 0:
            raise ValueError("event_time_s must be non-negative")
        if not 100 <= self.budget_ms <= 12000:
            raise ValueError("budget_ms must be within 100..12000")


@dataclass(frozen=True, slots=True)
class VehicleDelayOutcome:
    """重解结果。status 只有两种，reason 在 not_resolved 时必填。"""

    status: str
    reason: str | None
    affected_order_ids: tuple[UUID, ...]
    local_problem: TransportProblem | None = None
    solution: TransportSolution | None = None
    validation: ValidationReport | None = None
    detail: dict = field(default_factory=dict)

    @property
    def resolved(self) -> bool:
        return self.status == RESOLVED


def _default_budget(budget_ms: int) -> SolveBudget:
    return SolveBudget(
        wall_time_ms=budget_ms,
        deadline_utc=(datetime.now(UTC) + timedelta(seconds=60)).replace(microsecond=0),
        max_candidates=1,
        seed=0,
        worker_count=1,
        deterministic_test_mode=False,
    )


def remaining_stop_order_ids(
    problem: TransportProblem,
    plan: TransportPlan,
    stops: tuple[RouteStop, ...],
    vehicle_id: UUID,
    event_time_s: int,
) -> tuple[UUID, ...]:
    """延误车辆在 event_time_s 之后仍需执行服务的订单集合，按首次出现顺序去重。"""

    route_ids = {route.id for route in plan.routes if route.vehicle_id == vehicle_id}
    if not route_ids:
        return ()
    node_by_id = {node.id: node for node in problem.nodes}
    ordered: list[UUID] = []
    for stop in sorted((s for s in stops if s.route_id in route_ids), key=lambda s: s.sequence):
        if stop.service_start_s < event_time_s:
            continue
        node = node_by_id.get(stop.node_id)
        if node is None or node.order_id is None:
            continue
        if node.order_id not in ordered:
            ordered.append(node.order_id)
    return tuple(ordered)


def build_local_problem(
    problem: TransportProblem,
    plan: TransportPlan,
    stops: tuple[RouteStop, ...],
    request: VehicleDelayRequest,
) -> tuple[TransportProblem | None, tuple[UUID, ...], str | None]:
    """返回 (局部问题, 受影响订单, 失败原因)。失败时问题为 None。"""

    if not any(route.vehicle_id == request.vehicle_id for route in plan.routes):
        return None, (), "vehicle_not_in_plan"

    order_ids = remaining_stop_order_ids(
        problem, plan, stops, request.vehicle_id, request.event_time_s
    )
    if not order_ids:
        return None, (), "no_remaining_service_after_event"

    state = next(
        (v for v in problem.vehicles if v.vehicle_id == request.vehicle_id), None
    )
    if state is None:
        return None, (), "vehicle_state_missing"

    lower = max(state.available_window.earliest_s, request.event_time_s + request.delay_s)
    upper = state.available_window.latest_s
    if lower >= upper:
        return None, order_ids, "delay_exceeds_vehicle_window"

    wanted = set(order_ids)
    nodes = tuple(
        node
        for node in problem.nodes
        if node.order_id in wanted or node.kind == RoutingNodeKind.DEPOT
    )
    if not nodes:
        return None, order_ids, "affected_nodes_missing"

    local = replace(
        problem,
        nodes=nodes,
        vehicles=(replace(state, available_window=TimeWindow(lower, upper)),),
    )
    return local, order_ids, None


def resolve_vehicle_delay(
    problem: TransportProblem,
    plan: TransportPlan,
    stops: tuple[RouteStop, ...],
    request: VehicleDelayRequest,
    *,
    budget: SolveBudget | None = None,
) -> VehicleDelayOutcome:
    """对单个车辆延误做局部重解，并做独立硬约束校验。"""

    local, order_ids, reason = build_local_problem(problem, plan, stops, request)
    if local is None:
        return VehicleDelayOutcome(status=NOT_RESOLVED, reason=reason, affected_order_ids=order_ids)

    solution = OrToolsTransportSolver().solve(local, budget or _default_budget(request.budget_ms))
    if solution.status not in FEASIBLE_STATUSES or solution.candidate is None:
        return VehicleDelayOutcome(
            status=NOT_RESOLVED,
            reason="local_transport_infeasible",
            affected_order_ids=order_ids,
            local_problem=local,
            solution=solution,
            detail={"solver_status": solution.status.value if hasattr(solution.status, "value") else str(solution.status)},
        )

    report = validate_transport(solution.candidate, local, solution.stops)
    if not report.valid:
        return VehicleDelayOutcome(
            status=NOT_RESOLVED,
            reason="local_transport_validation_failed",
            affected_order_ids=order_ids,
            local_problem=local,
            solution=solution,
            validation=report,
            detail={
                "violations": [
                    {"code": v.code, "severity": v.severity.value, "message": v.message}
                    for v in report.violations[:10]
                ]
            },
        )

    return VehicleDelayOutcome(
        status=RESOLVED,
        reason=None,
        affected_order_ids=order_ids,
        local_problem=local,
        solution=solution,
        validation=report,
        detail={
            "solver_status": solution.status.value if hasattr(solution.status, "value") else str(solution.status),
            "engine": [e.engine_name for e in solution.solver_evidence],
            "route_count": len(solution.candidate.routes),
            "stop_count": len(solution.stops),
            "unserved_order_ids": [str(o) for o in solution.optional_unserved_order_ids],
        },
    )
