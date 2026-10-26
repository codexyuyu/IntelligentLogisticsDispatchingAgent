"""Planned metrics only. Missing observations are never converted to zero."""
from collections import Counter
from dataclasses import asdict, dataclass
from app.contracts.entities import PlanningSnapshot
from app.contracts.planning import CandidatePlan

DEFINITION_VERSION = "1.0.0"
UNITS = {
    "demand_satisfaction": "ratio", "on_time_rate": "ratio", "mean_delay": "s",
    "transport_distance": "m", "transport_cost": "cent", "vehicle_utilization": "ratio",
    "warehouse_utilization": "ratio", "dock_utilization": "ratio", "equipment_utilization": "ratio",
    "solve_time": "ms", "exception_detection_time": "ms", "reschedule_time": "ms",
    "changed_tasks": "count", "disturbance": "ratio",
}

@dataclass(frozen=True)
class Metric:
    name: str
    scope_id: str
    source: str
    window_start: int
    window_end: int
    definition_version: str
    unit: str
    sample_count: int
    numerator: float | None
    denominator: float | None
    value: float | None
    missing_reason: str | None
    provenance: str

    def to_dict(self):
        return asdict(self)


def union_seconds(intervals, start, end):
    """Half-open intervals clipped to one observation window."""
    if end <= start:
        raise ValueError("invalid_window")
    clipped = []
    for a, b in intervals:
        if b < a:
            raise ValueError("reversed_interval")
        a, b = max(a, start), min(b, end)
        if a < b:
            clipped.append((a, b))
    total = 0
    cursor = start
    for a, b in sorted(clipped):
        total += max(0, b - max(a, cursor))
        cursor = max(cursor, b)
    return total


def planned_metrics(snapshot: PlanningSnapshot, plan: CandidatePlan, *, window_start: int,
                    window_end: int, scope_id: str) -> dict[str, Metric]:
    if type(window_start) is not int or type(window_end) is not int or window_end <= window_start:
        raise ValueError("invalid_window")
    if (plan.snapshot_id, plan.snapshot_version) != (snapshot.snapshot_id, snapshot.version):
        raise ValueError("snapshot_version_mismatch")
    for result in (plan.routing, plan.warehouse):
        if (result.snapshot_id, result.snapshot_version) != (snapshot.snapshot_id, snapshot.version):
            raise ValueError("result_snapshot_mismatch")
    orders = {o.order_id: o for o in snapshot.orders}
    if len(orders) != len(snapshot.orders):
        raise ValueError("duplicate_order")
    delivered = {}
    for route in plan.routing.routes:
        for stop in route.stops:
            if stop.stop_kind == "delivery":
                for oid in stop.order_ids:
                    if oid not in orders or oid in delivered:
                        raise ValueError("unknown_or_duplicate_delivery")
                    delivered[oid] = stop.departure_at_s
    unserved = [o.order_id for o in plan.routing.unserved_orders]
    if len(set(unserved)) != len(unserved) or set(unserved) & delivered.keys() or set(unserved) - orders.keys():
        raise ValueError("invalid_unserved_scope")
    # Scope is the entire snapshot: missing/failed orders remain in the denominator.
    ends = [s.departure_at_s for r in plan.routing.routes for s in r.stops]
    ends += [o.end_s for o in plan.warehouse.operations]
    if window_start > snapshot.simulation_time_s or any(t > window_end for t in ends):
        raise ValueError("partial_plan_window_not_supported")
    result = {}
    def emit(name, numerator=None, denominator=None, count=0, reason=None, provenance="contract_missing_observation"):
        if reason is None and denominator == 0:
            reason = "ZERO_DENOMINATOR"
        value = None if reason else (numerator / denominator if denominator is not None else numerator)
        result[name] = Metric(name, scope_id, "planned", window_start, window_end, DEFINITION_VERSION,
                              UNITS[name], count, numerator, denominator, value, reason, provenance)
    for name in UNITS:
        emit(name, reason="MISSING_REQUIRED_OBSERVATION")
    valid = plan.validation.status == "passed" and plan.routing.metadata.has_solution and plan.warehouse.metadata.has_solution
    if not valid:
        for name in UNITS:
            emit(name, reason="PLAN_NOT_VALIDATED")
        return result
    due = {o.order_id: o.service_window.end_s + o.service_duration_s for o in snapshot.orders}
    emit("demand_satisfaction", len(delivered), len(orders), len(orders), provenance="snapshot demand; no cancellation events supplied")
    emit("on_time_rate", sum(t <= due[o] for o,t in delivered.items()), len(orders), len(orders), provenance="hard latest service start + service duration; soft_due absent")
    emit("mean_delay", sum(max(0,t-due[o]) for o,t in delivered.items()), len(delivered), len(delivered), provenance="delivered orders including zero delay; hard-window fallback")
    emit("transport_distance", sum(r.distance_m for r in plan.routing.routes), count=len(plan.routing.routes), provenance="all planned route distances; not actual driven distance")
    vehicles = {v.vehicle_id: v for v in snapshot.vehicles}
    busy = {key: [] for key in vehicles}
    for route in plan.routing.routes:
        if route.vehicle_id not in vehicles or len(route.stops) < 2:
            raise ValueError("invalid_vehicle_route")
        if any(stop.order_ids for stop in route.stops if stop.stop_kind == "delivery"):
            busy[route.vehicle_id].append((route.stops[0].departure_at_s, route.stops[-1].arrival_at_s))
    available = total_busy = 0
    for key, vehicle in vehicles.items():
        a, b = max(vehicle.shift_window.start_s, vehicle.available_at_s), vehicle.shift_window.end_s
        if any(x < a or y > b for x,y in busy[key]):
            raise ValueError("vehicle_busy_outside_availability")
        available += union_seconds([(a,b)] if a < b else [], window_start, window_end)
        total_busy += union_seconds(busy[key], window_start, window_end)
    emit("vehicle_utilization", total_busy, available, len(vehicles), provenance="planned route driving/service/waiting; snapshot shift and available_at")
    # Engine metadata is not a monotonic measurement around all calls: do not label its sum solve_time.
    return result


def task_change_metrics(before, after, completed_ids=(), shift_scale_s=3600):
    """Evaluation-only records: task_id -> (resource_ids, start_s, predecessor_id).

    Caller supplies stable task identity and frozen completed facts; this is not
    a new scheduling DTO. Missing completed facts or any change are rejected.
    """
    if shift_scale_s <= 0:
        raise ValueError("invalid_shift_scale")
    for key in completed_ids:
        if key not in before or key not in after or before[key] != after[key]:
            raise ValueError("completed_fact_changed")
    for values in (before, after):
        for resources, start, predecessor in values.values():
            if type(start) is not int or start < 0 or len(set(resources)) != len(resources):
                raise ValueError("invalid_task_observation")
    frozen = set(completed_ids)
    old, new = set(before)-frozen, set(after)-frozen
    members = old ^ new
    common = old & new
    n = max(1, len(old | new))
    assignment = {k for k in common if set(before[k][0]) != set(after[k][0])}
    time = {k for k in common if before[k][1] != after[k][1]}
    sequence = {k for k in common if before[k][2] != after[k][2]}
    shifts = sum(min(1, abs(after[k][1]-before[k][1])/shift_scale_s) for k in common)
    return {"changed_tasks": len(members | assignment | time | sequence),
            "disturbance": .4*len(assignment)/n + .3*shifts/n + .2*len(sequence)/n + .1*len(members)/n,
            "added": sorted(new-old), "removed": sorted(old-new), "normalization_count": n,
            "policy_version": "1.0.0", "shift_scale_s": shift_scale_s}


def capacity_utilization(usage, availability, *, window_start, window_end):
    """Integrate explicit disjoint unit-capacity observations per physical resource.

    Rows are (resource_id, start_s, end_s, units). No pooled/individual aliases
    may appear together. Overlapping usage adds units, availability overlaps
    are rejected (caller must normalize outages). Unknown coverage is an error.
    """
    if window_end <= window_start:
        raise ValueError("invalid_window")
    for rows in (usage, availability):
        for key,a,b,units in rows:
            if b <= a or units <= 0:
                raise ValueError("invalid_capacity_observation")
    total = capacity = 0
    keys = {r[0] for r in usage} | {r[0] for r in availability}
    for key in keys:
        u = [r for r in usage if r[0] == key]
        v = [r for r in availability if r[0] == key]
        boundaries = sorted({window_start,window_end} | {max(window_start,min(window_end,t)) for r in u+v for t in r[1:3]})
        for a,b in zip(boundaries,boundaries[1:]):
            amounts = [r[3] for r in v if r[1] <= a < r[2]]
            if len(amounts)>1:
                raise ValueError("overlapping_capacity_definitions")
            limit = amounts[0] if amounts else 0
            occupied = sum(r[3] for r in u if r[1] <= a < r[2])
            if occupied > limit:
                raise ValueError("capacity_exceeded_or_missing_availability")
            total += occupied*(b-a)
            capacity += limit*(b-a)
    return {"numerator":total,"denominator":capacity,
            "value":total/capacity if capacity else None,
            "missing_reason":None if capacity else "ZERO_DENOMINATOR"}
