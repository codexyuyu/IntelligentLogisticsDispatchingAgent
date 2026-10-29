"""Deterministic *planned* event replay from independently checked joint plans.

These events are forecasts, not observed EventKind incidents or actual warehouse
task transitions. Reconciliation is a separate gate before any persistence.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID, uuid5

TIMELINE_NAMESPACE = UUID("66df7114-c45e-4be1-af25-eefbdba9e207")
KINDS = (
    "warehouse_work_finished",
    "warehouse_work_start",
    "loading_ready",
    "order_handoff",
    "vehicle_departure",
    "order_delivered",
    "vehicle_return",
)
PRIORITY = {kind: number for number, kind in enumerate(KINDS)}


class TimelineValidationError(ValueError):
    def __init__(self, issues):
        self.issues = tuple(issues)
        super().__init__("timeline reconciliation failed: " + ", ".join(self.issues))


def build_timeline(result, run_id=None):
    """Return reproducible events and seven explicit cross-system checks."""
    if result.get("status") != "checked" or result.get("joint_validation", {}).get("valid") is not True:
        raise TimelineValidationError(("unvalidated_plan_must_not_be_replayed",))

    warehouse = result["warehouse_problem"]
    snapshot = warehouse["snapshot"]
    tasks = {item["id"]: item for item in warehouse["tasks"]}
    assignments = result["warehouse_solution"]["assignments"]
    transport = result["transport_solution"]
    routes = transport["candidate"]["routes"]
    route_stops = defaultdict(list)
    nodes = {item["id"]: item for item in result["transport_problem"]["nodes"]}
    for stop in transport["stops"]:
        route_stops[stop["route_id"]].append(stop)

    events = []

    def add(kind, at, object_id, *, order_id=None, vehicle_id=None, route_id=None, node_id=None):
        if at < 0:
            raise TimelineValidationError(("negative_event_time",))
        token = ":".join(map(str, (run_id, kind, at, object_id, order_id, vehicle_id, route_id)))
        events.append(
            {
                "id": str(uuid5(TIMELINE_NAMESPACE, token)),
                "kind": kind,
                "time_s": at,
                "object_id": str(object_id),
                "order_id": order_id,
                "vehicle_id": vehicle_id,
                "route_id": route_id,
                "node_id": node_id,
            }
        )

    spans = {}
    for assignment in assignments:
        task_id = assignment["task_id"]
        if task_id not in tasks:
            raise TimelineValidationError(("unknown_warehouse_task_assignment",))
        if task_id not in spans:
            spans[task_id] = [assignment["start_s"], assignment["end_s"]]
        else:
            spans[task_id][0] = min(spans[task_id][0], assignment["start_s"])
            spans[task_id][1] = max(spans[task_id][1], assignment["end_s"])
    if set(spans) != set(tasks):
        raise TimelineValidationError(("missing_warehouse_task_assignments",))

    by_order = defaultdict(list)
    for task_id, task in tasks.items():
        start, end = spans[task_id]
        if task["order_id"]:
            by_order[task["order_id"]].append(task_id)
        add("warehouse_work_start", start, task_id, order_id=task["order_id"])
        add("warehouse_work_finished", end, task_id, order_id=task["order_id"])

    ready = {order_id: max(spans[task_id][1] for task_id in ids) for order_id, ids in by_order.items()}
    for order_id, at in ready.items():
        add("loading_ready", at, order_id, order_id=order_id)

    pickups, deliveries, pickup_departures = {}, {}, {}
    depart_times, return_times = {}, {}
    matrix = result["transport_problem"]["matrix"]
    matrix_indices = {node_id: i for i, node_id in enumerate(matrix["node_ids"])}
    route_vehicles = [route["vehicle_id"] for route in routes]
    for route in routes:
        stops = sorted(route_stops.get(route["id"], ()), key=lambda stop: stop["sequence"])
        if not stops:
            raise TimelineValidationError(("empty_vehicle_route",))
        vehicle_id = route["vehicle_id"]
        first_pickup_departure = None
        for stop in stops:
            node = nodes.get(stop["node_id"])
            if node is None:
                raise TimelineValidationError(("route_stop_unknown_node",))
            order_id = node["order_id"]
            if node["kind"] == "pickup":
                if order_id in pickups:
                    raise TimelineValidationError(("duplicate_order_pickup",))
                pickups[order_id] = stop["service_start_s"]
                pickup_departures[order_id] = stop["departure_s"]
                add(
                    "order_handoff",
                    stop["service_start_s"],
                    order_id,
                    order_id=order_id,
                    vehicle_id=vehicle_id,
                    route_id=route["id"],
                    node_id=stop["node_id"],
                )
                if first_pickup_departure is None:
                    first_pickup_departure = stop["departure_s"]
            elif node["kind"] == "delivery":
                if order_id in deliveries:
                    raise TimelineValidationError(("duplicate_order_delivery",))
                deliveries[order_id] = stop["departure_s"]
                add(
                    "order_delivered",
                    stop["departure_s"],
                    order_id,
                    order_id=order_id,
                    vehicle_id=vehicle_id,
                    route_id=route["id"],
                    node_id=stop["node_id"],
                )
        if first_pickup_departure is None:
            raise TimelineValidationError(("route_without_pickup",))
        depart_times[vehicle_id] = first_pickup_departure
        add(
            "vehicle_departure",
            first_pickup_departure,
            vehicle_id,
            vehicle_id=vehicle_id,
            route_id=route["id"],
            node_id=stops[0]["node_id"],
        )
        last_location = nodes[stops[-1]["node_id"]]["location_id"]
        try:
            travel = matrix["travel_s"][matrix_indices[last_location]][matrix_indices[route["end_node_id"]]]
        except (KeyError, IndexError) as exc:
            raise TimelineValidationError(("return_matrix_arc_missing",)) from exc
        if travel is None:
            raise TimelineValidationError(("return_matrix_arc_missing",))
        return_at = stops[-1]["departure_s"] + travel
        return_times[vehicle_id] = return_at
        add(
            "vehicle_return",
            return_at,
            vehicle_id,
            vehicle_id=vehicle_id,
            route_id=route["id"],
            node_id=route["end_node_id"],
        )

    events.sort(key=lambda item: (item["time_s"], PRIORITY[item["kind"]], item["object_id"], item["id"]))
    for seq, event in enumerate(events):
        event["sequence"] = seq

    scope_orders = set(snapshot["scope"]["order_ids"])
    unserved = set(transport["candidate"]["unserved_order_ids"])
    served = scope_orders - unserved
    counts = {kind: sum(event["kind"] == kind for event in events) for kind in KINDS}
    checks = {
        "event_delivery_mismatch": set(deliveries) == served and counts["order_delivered"] == len(served),
        "event_handoff_mismatch": set(pickups) == served and counts["order_handoff"] == len(served),
        "duplicate_vehicle_route": len(route_vehicles) == len(set(route_vehicles)),
        "vehicle_departure_event_mismatch": counts["vehicle_departure"] == len(routes),
        "vehicle_return_event_mismatch": counts["vehicle_return"] == len(routes),
        "handoff_before_warehouse_operations_finished": all(
            order_id in ready and pickups[order_id] >= ready[order_id] for order_id in served if order_id in pickups
        ),
        "departure_before_loading_ready": all(
            order_id in ready and pickup_departures[order_id] >= ready[order_id]
            for order_id in served
            if order_id in pickup_departures
        ),
    }
    # Prevent a missing pickup from being skipped by the conditional checks.
    if set(pickups) != served:
        checks["handoff_before_warehouse_operations_finished"] = False
        checks["departure_before_loading_ready"] = False
    identity = len(scope_orders) == len(deliveries) + len(unserved) and not (set(deliveries) & unserved)
    issues = [name for name, passed in checks.items() if not passed]
    if not identity or set(deliveries) | unserved != scope_orders:
        issues.append("orders_delivery_unserved_identity")
    if issues:
        raise TimelineValidationError(issues)

    order_details = [
        {
            "order_id": order_id,
            "warehouse_task_count": len(by_order.get(order_id, ())),
            "loading_ready": order_id in ready,
            "loading_ready_at_s": ready.get(order_id),
            "routing_status": "unserved" if order_id in unserved else "planned_delivery",
            "planned_delivery_at_s": deliveries.get(order_id),
            "planned_vehicle_id": next(
                (
                    event["vehicle_id"]
                    for event in events
                    if event["kind"] == "order_delivered" and event["order_id"] == order_id
                ),
                None,
            ),
            "unserved_reason": "solver_unserved" if order_id in unserved else None,
        }
        for order_id in sorted(scope_orders)
    ]
    return {
        "schema_version": "2.0.0",
        "source_kind": "planned_validated",
        "event_count": len(events),
        "events": events,
        "reconciliation": {
            "passed": True,
            "checks": checks,
            "scope_orders": len(scope_orders),
            "planned_delivery_orders": len(deliveries),
            "explicitly_unserved_orders": len(unserved),
            "order_details": order_details,
        },
    }


def state_at_time(timeline, result, at_s):
    """The ten requested state collections at a replay timestamp."""
    if at_s < 0:
        raise ValueError("time_s must be non-negative")
    events = [event for event in timeline["events"] if event["time_s"] <= at_s]

    def ids(kind, field="object_id"):
        return {event[field] for event in events if event["kind"] == kind}

    started = ids("warehouse_work_start")
    finished = ids("warehouse_work_finished")
    departed = ids("vehicle_departure")
    returned = ids("vehicle_return")
    handed = ids("order_handoff")
    delivered = ids("order_delivered")
    vehicles = {vehicle["id"] for vehicle in result["warehouse_problem"]["snapshot"]["vehicles"]}
    route_vehicles = {route["vehicle_id"] for route in result["transport_solution"]["candidate"]["routes"]}
    in_transit = departed - returned
    last_position = {}
    stops = result["transport_solution"]["stops"]
    node_vehicle = {route["id"]: route["vehicle_id"] for route in result["transport_solution"]["candidate"]["routes"]}
    for stop in sorted(stops, key=lambda item: (item["departure_s"], item["sequence"])):
        vehicle_id = node_vehicle.get(stop["route_id"])
        if vehicle_id in in_transit and stop["departure_s"] <= at_s:
            last_position[vehicle_id] = stop["node_id"]
    return {
        "schema_version": "2.0.0",
        "source_kind": "planned_validated",
        "time_s": at_s,
        "completed_order_ids": sorted(delivered),
        "completed_operation_ids": sorted(finished),
        "active_operation_ids": sorted(started - finished),
        "in_transit_vehicle_ids": sorted(in_transit),
        "returned_vehicle_ids": sorted(returned),
        "not_yet_departed_vehicle_ids": sorted(route_vehicles - departed),
        "onboard_pending_order_ids": sorted(handed - delivered),
        "available_depot_vehicle_ids": sorted(vehicles - in_transit),
        "halted_vehicle_positions": last_position,
        "interrupted_operation_ids": [],
    }
