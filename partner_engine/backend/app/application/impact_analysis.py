"""B-04 impact analysis: identify the smallest safe rescheduling scope.

Supported events (R20):
  departure_delayed   one vehicle leaves late; its whole route is replanned
  dock_unavailable    a warehouse cannot load before a given time; vehicles that would
                      have loaded earlier are replanned, later ones stay locked
  cargo_quarantined   specific orders are blocked by quality control; every other order
                      keeps its plan
``weather_changed`` and ``demand_changed`` remain unimplemented (see docs/B04_EVENT_TYPES_R20.md).
"""
from __future__ import annotations

from app.contracts.events import DispatchEvent
from app.contracts.planning import CandidatePlan, VehicleRoute
from app.contracts.reschedule import ImpactAnalysis

SUPPORTED_EVENTS = ("departure_delayed", "dock_unavailable", "cargo_quarantined")


def route_order_ids(route: VehicleRoute) -> list[str]:
    return [oid for stop in route.stops if stop.stop_kind == "delivery" for oid in stop.order_ids]


def selected_order_ids(plan: CandidatePlan) -> set[str]:
    """Orders this plan is responsible for: served ones plus explicitly unserved ones."""
    served = {oid for route in plan.routing.routes for oid in route_order_ids(route)}
    return served | {u.order_id for u in plan.routing.unserved_orders}


def find_affected_work(*, event: DispatchEvent, plan: CandidatePlan) -> ImpactAnalysis:
    """Return affected/locked work without mutating the existing plan."""
    if event.event_type == "departure_delayed":
        return _departure_delayed(event, plan)
    if event.event_type == "dock_unavailable":
        return _dock_unavailable(event, plan)
    if event.event_type == "cargo_quarantined":
        return _cargo_quarantined(event, plan)
    raise ValueError(f"b04_event_type_not_implemented:{event.event_type}")


def _departure_delayed(event: DispatchEvent, plan: CandidatePlan) -> ImpactAnalysis:
    routes = {route.vehicle_id: route for route in plan.routing.routes}
    target_route = routes.get(event.object_id)
    if target_route is None:
        raise ValueError(f"vehicle_route_not_found:{event.object_id}")
    affected = route_order_ids(target_route)
    if event.payload.affected_order_ids:
        requested = set(event.payload.affected_order_ids)
        missing = sorted(requested - set(affected))
        if missing:
            raise ValueError("event_orders_not_on_target_route:" + ",".join(missing))
    affected_ids = tuple(dict.fromkeys(affected))
    locked = tuple(sorted(selected_order_ids(plan) - set(affected_ids)))
    return ImpactAnalysis(
        event_id=event.event_id,
        affected_order_ids=affected_ids,
        locked_order_ids=locked,
        affected_vehicle_ids=(event.object_id,),
        affected_route_ids=(event.object_id,),
        reason="车辆出发延误，整条受影响车辆路线进入局部重排，其余订单保持锁定。",
    )


def _dock_unavailable(event: DispatchEvent, plan: CandidatePlan) -> ImpactAnalysis:
    until = event.payload.unavailable_until_s
    if until is None or until <= 0:
        raise ValueError("dock_unavailable_requires_positive_unavailable_until_s")
    warehouse_id = event.object_id
    handoff_by_order = {h.order_id: h for h in plan.warehouse.warehouse_handoffs}
    known_warehouses = {h.warehouse_id for h in plan.warehouse.warehouse_handoffs}
    if warehouse_id not in known_warehouses:
        raise ValueError(f"dock_warehouse_not_in_plan:{warehouse_id}")

    affected, vehicles = [], []
    for route in plan.routing.routes:
        orders = [oid for oid in route_order_ids(route)
                  if handoff_by_order[oid].warehouse_id == warehouse_id]
        if not orders:
            continue
        if route.stops[0].departure_at_s < until:
            # This vehicle would have to load before the dock reopens.
            affected.extend(orders)
            vehicles.append(route.vehicle_id)
    affected_ids = tuple(dict.fromkeys(affected))
    locked = tuple(sorted(selected_order_ids(plan) - set(affected_ids)))
    return ImpactAnalysis(
        event_id=event.event_id,
        affected_order_ids=affected_ids,
        locked_order_ids=locked,
        affected_vehicle_ids=tuple(sorted(vehicles)),
        affected_route_ids=tuple(sorted(vehicles)),
        reason=(f"{warehouse_id} 月台在 {until}s 前不可用；计划发车早于该时刻的车辆进入局部重排，"
                "其余订单保持锁定。"),
    )


def _cargo_quarantined(event: DispatchEvent, plan: CandidatePlan) -> ImpactAnalysis:
    quarantined = tuple(dict.fromkeys(event.payload.affected_order_ids))
    if not quarantined:
        raise ValueError("cargo_quarantined_requires_affected_order_ids")
    selected = selected_order_ids(plan)
    unknown = sorted(set(quarantined) - selected)
    if unknown:
        raise ValueError("quarantined_orders_not_in_plan:" + ",".join(unknown))
    vehicles = sorted({route.vehicle_id for route in plan.routing.routes
                       for oid in route_order_ids(route) if oid in set(quarantined)})
    locked = tuple(sorted(selected - set(quarantined)))
    return ImpactAnalysis(
        event_id=event.event_id,
        affected_order_ids=quarantined,
        locked_order_ids=locked,
        affected_vehicle_ids=tuple(vehicles),
        affected_route_ids=tuple(vehicles),
        reason="订单被质检隔离，不再参与本次配送；其余订单保持既有计划。",
    )
