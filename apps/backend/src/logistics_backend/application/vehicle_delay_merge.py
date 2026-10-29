"""把局部重解的结果合并回完整运输方案。

合并规则刻意保守：
* 只有被重解车辆的路由被替换，其余车辆原样保留（这正是「局部」的含义）；
* 未受影响订单的停靠点一个不改，避免求解器顺手把它们挪走；
* 成本按分项相加，不重算——重算等于另做一次求解，会引入未被校验的数字。
"""

from __future__ import annotations

from uuid import UUID

from logistics_domain.planning import CostBreakdown, Route, RouteStop, TransportPlan
from logistics_domain.transport import TransportSolution


def merge_local_solution(
    base_plan: TransportPlan,
    base_stops: tuple[RouteStop, ...],
    solution: TransportSolution,
    vehicle_id: UUID,
) -> tuple[TransportPlan, tuple[RouteStop, ...]]:
    """用局部解替换指定车辆的路由，返回合并后的完整方案。"""

    if solution.candidate is None:
        raise ValueError("local solution has no candidate to merge")

    replaced_route_ids = {route.id for route in base_plan.routes if route.vehicle_id == vehicle_id}

    kept_routes = tuple(r for r in base_plan.routes if r.vehicle_id != vehicle_id)
    kept_stops = tuple(s for s in base_stops if s.route_id not in replaced_route_ids)

    merged_routes = kept_routes + tuple(solution.candidate.routes)
    merged_stops = kept_stops + tuple(solution.stops)

    costs = [route.cost for route in merged_routes] or [CostBreakdown(0, 0, 0, 0, 0, 0)]
    total = CostBreakdown(
        distance_cents=sum(c.distance_cents for c in costs),
        fixed_vehicle_cents=sum(c.fixed_vehicle_cents for c in costs),
        service_cents=sum(c.service_cents for c in costs),
        overtime_cents=sum(c.overtime_cents for c in costs),
        setup_cents=sum(c.setup_cents for c in costs),
        total_cents=sum(c.total_cents for c in costs),
    )

    unserved = tuple(dict.fromkeys(
        (*base_plan.unserved_order_ids, *solution.optional_unserved_order_ids)
    ))
    merged = TransportPlan(routes=merged_routes, unserved_order_ids=unserved, cost=total)
    return merged, merged_stops


def route_order_ids(route: Route, stops: tuple[RouteStop, ...]) -> tuple[UUID, ...]:
    """按序取一条路由上的节点引用，供合并后的一致性检查使用。"""

    return tuple(stop.node_id for stop in sorted(
        (s for s in stops if s.route_id == route.id), key=lambda s: s.sequence
    ))
