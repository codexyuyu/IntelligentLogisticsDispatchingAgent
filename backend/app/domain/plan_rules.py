"""B-03 warehouse/transport coordination rules.

Pure cross-domain validation for the end-to-end plan.  It intentionally does not
call OR-Tools, touch HTTP/DB, or depend on solver internals.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence


def _by_id(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, Mapping[str, Any]]:
    return {str(row[key]): row for row in rows}


def _violation(rule_id: str, object_ids: Sequence[str], message: str) -> dict[str, Any]:
    return {"rule_id": rule_id, "object_ids": tuple(str(x) for x in object_ids), "message": message}


def validate_plan(*, snapshot: Mapping[str, Any], order_ids: Sequence[str], warehouse: Mapping[str, Any], routing: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Validate warehouse -> loading -> transport -> delivery continuity.

    B-03 rules:
      1) Every requested order has exactly one warehouse handoff.
      2) A route serving an order cannot start before the warehouse ready_at.
      3) A route serving an order must start inside its loading window.
      4) Vehicle/warehouse/order scope must match.
      5) Every required order is served exactly once.
      6) Delivery service must finish by the order freshness deadline.
      7) Route arrival timestamps must be monotonic and consistent with the route duration.
      8) Returned-to-warehouse time must not precede the last delivery on that route.
    """
    violations: list[dict[str, Any]] = []
    orders = _by_id(snapshot.get("orders", ()), "order_id")
    vehicles = _by_id(snapshot.get("vehicles", ()), "vehicle_id")
    handoffs = _by_id(warehouse.get("warehouse_handoffs", ()), "order_id")
    routes = list(routing.get("routes", ()))

    selected_ids = [str(x) for x in order_ids]
    for oid in selected_ids:
        if oid not in orders:
            violations.append(_violation("b03.order.exists", (oid,), "订单不在快照中"))
        if oid not in handoffs:
            violations.append(_violation("b03.handoff.exists", (oid,), "订单缺少仓运交接信息"))

    # Independent cross-domain proof that no handoff can claim goods were
    # ready before their warehouse work really finished. This intentionally
    # recomputes from the source operations rather than calling CP-SAT helpers.
    if warehouse.get("operations"):
        op_source = _by_id(snapshot.get("operations", ()), "operation_id")
        op_scheduled = _by_id(warehouse.get("operations", ()), "operation_id")
        for oid in selected_ids:
            op_ids = [op_id for op_id, op in op_source.items() if oid in op.get("order_ids", ())]
            missing_ops = [op_id for op_id in op_ids if op_id not in op_scheduled]
            for op_id in missing_ops:
                violations.append(_violation("b03.handoff.operation_ready", (oid, op_id), "订单仓储作业未排程"))
            if oid in handoffs and not missing_ops:
                real_ready = max((int(op_scheduled[op_id]["end_s"]) for op_id in op_ids), default=0)
                if int(handoffs[oid]["ready_at_s"]) != real_ready:
                    violations.append(_violation("b03.handoff.operation_ready", (oid,), "交接 ready_at 与实际仓储作业完工时刻不一致"))

    seen_order: list[str] = []
    route_return_by_vehicle: dict[str, int] = {}

    for route in routes:
        vehicle_id = str(route.get("vehicle_id"))
        vehicle = vehicles.get(vehicle_id)
        if vehicle is None:
            violations.append(_violation("b03.vehicle.exists", (vehicle_id,), "运输方案引用未知车辆"))
            continue

        stops = list(route.get("stops", ()))
        if len(stops) < 2:
            violations.append(_violation("b03.route.boundary", (vehicle_id,), "运输路线缺少仓库起止节点"))
            continue

        start = stops[0]
        end = stops[-1]
        start_at = int(start.get("departure_at_s", start.get("arrival_at_s", -1)))
        end_at = int(end.get("arrival_at_s", -1))
        route_return_by_vehicle[vehicle_id] = end_at

        if start.get("stop_kind") != "depot_start" or end.get("stop_kind") != "depot_end":
            violations.append(_violation("b03.route.boundary", (vehicle_id,), "路线首尾必须为仓库起止节点"))

        previous_departure = start_at
        for stop in stops[1:]:
            arrival = int(stop.get("arrival_at_s", -1))
            departure = int(stop.get("departure_at_s", arrival))
            if arrival < previous_departure:
                violations.append(_violation("b03.route.monotonic", (vehicle_id,), "运输时间线不是单调递增"))
            if departure < arrival:
                violations.append(_violation("b03.route.stop_order", (vehicle_id,), "节点 departure 早于 arrival"))
            previous_departure = departure

            if stop.get("stop_kind") != "delivery":
                continue
            stop_orders = tuple(str(x) for x in stop.get("order_ids", ()))
            if len(stop_orders) != 1:
                violations.append(_violation("b03.delivery.cardinality", (vehicle_id,), "配送节点必须对应一个订单"))
                continue
            oid = stop_orders[0]
            seen_order.append(oid)
            order = orders.get(oid)
            handoff = handoffs.get(oid)
            if order is None:
                violations.append(_violation("b03.order.exists", (oid, vehicle_id), "配送节点包含未知订单"))
                continue
            if handoff is None:
                continue

            if str(vehicle.get("warehouse_id")) != str(order.get("warehouse_id")):
                violations.append(_violation("b03.scope.warehouse", (oid, vehicle_id), "车辆、订单不属于同一仓库"))
            if int(start_at) < int(handoff["ready_at_s"]):
                violations.append(_violation("b03.handoff.ready_at", (oid, vehicle_id), "车辆出发早于仓库 ready_at"))
            if int(start_at) < int(handoff["loading_window"]["start_s"]) or int(start_at) > int(handoff["loading_window"]["end_s"]):
                violations.append(_violation("b03.handoff.loading_window", (oid, vehicle_id), "车辆出发不在装车时间窗内"))

            delivery_departure = int(stop["departure_at_s"])
            if delivery_departure > int(order["freshness_deadline_s"]):
                violations.append(_violation("b03.delivery.freshness", (oid, vehicle_id), "客户交付完成时间超过 freshness deadline"))

        route_duration = int(route.get("duration_s", -1))
        if route_duration != end_at - start_at:
            violations.append(_violation("b03.route.duration", (vehicle_id,), "路线 duration 与首尾时间不一致"))

    required = {oid for oid in selected_ids if orders.get(oid, {}).get("required") is True}
    counts: dict[str, int] = {}
    for oid in seen_order:
        counts[oid] = counts.get(oid, 0) + 1
    for oid in selected_ids:
        if counts.get(oid, 0) > 1:
            violations.append(_violation("b03.order.duplicate", (oid,), "订单被多辆车/多条路线重复服务"))
    missing_required = sorted(required - set(seen_order))
    for oid in missing_required:
        violations.append(_violation("b03.order.required_served", (oid,), "必服务订单未进入运输方案"))

    arrivals = {str(a.get("vehicle_id")): a for a in routing.get("warehouse_arrivals", ())}
    for vehicle_id, route_end in route_return_by_vehicle.items():
        arrival = arrivals.get(vehicle_id)
        if arrival is None:
            violations.append(_violation("b03.return_arrival.exists", (vehicle_id,), "车辆缺少回仓到达信息"))
            continue
        if int(arrival.get("arrival_at_s", -1)) < int(route_end):
            violations.append(_violation("b03.return_arrival.time", (vehicle_id,), "车辆回仓时间早于运输路线结束时间"))

    return tuple(violations)
