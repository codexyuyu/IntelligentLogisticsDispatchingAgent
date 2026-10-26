"""Owner: B | Pure transport validation; no solver, Pydantic, HTTP, or DB imports.

The validator intentionally recomputes capacity, temperature, loading windows,
service windows, freshness, shift limits, travel-time continuity, distance, and
route load from plain Python mappings. It is independent from the OR-Tools model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class TransportValidation:
    passed: bool
    violations: tuple[str, ...]


def _by_id(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, Mapping[str, Any]]:
    return {str(row[key]): row for row in rows}


def _matrix_lookup(matrix: Mapping[str, Any], from_node: str, to_node: str) -> tuple[int | None, int | None]:
    node_ids = list(matrix["node_ids"])
    try:
        a = node_ids.index(from_node)
        b = node_ids.index(to_node)
    except ValueError:
        return None, None
    return matrix["duration_s"][a][b], matrix["distance_m"][a][b]


def validate_transport(*, request: Mapping[str, Any], result: Mapping[str, Any]) -> TransportValidation:
    """Recompute transport facts independently from the solver model."""
    metadata = result.get("metadata", {})
    if metadata.get("status") not in {"feasible", "optimal"} or not metadata.get("has_solution"):
        return TransportValidation(False, ("no_feasible_solution",))

    snapshot = request["snapshot"]
    orders = _by_id(snapshot["orders"], "order_id")
    all_vehicles = _by_id(snapshot["vehicles"], "vehicle_id")
    handoffs = _by_id(request["warehouse_handoffs"], "order_id")
    selected_ids = list(request["order_ids"])
    selected_orders = {oid: orders[oid] for oid in selected_ids if oid in orders}
    scoped_warehouse_ids = {selected_orders[oid]["warehouse_id"] for oid in selected_orders}
    if len(scoped_warehouse_ids) == 1:
        scoped_warehouse = next(iter(scoped_warehouse_ids))
        vehicles = {vid: v for vid, v in all_vehicles.items() if v["warehouse_id"] == scoped_warehouse}
    else:
        vehicles = {}
        violations_seed = ["multi_warehouse_request"]
    violations: list[str] = locals().get("violations_seed", [])

    if set(selected_orders) != set(selected_ids):
        missing = sorted(set(selected_ids) - set(selected_orders))
        violations.extend(f"unknown_order:{oid}" for oid in missing)

    matrix = snapshot["matrix"]
    matrix_nodes = set(matrix["node_ids"])
    if len(matrix_nodes) != len(matrix["node_ids"]):
        violations.append("matrix_duplicate_nodes")

    routes = result.get("routes", ())
    seen_orders: list[str] = []
    seen_vehicles: set[str] = set()

    for route in routes:
        vehicle_id = route.get("vehicle_id")
        if vehicle_id not in vehicles:
            violations.append(f"unknown_vehicle:{vehicle_id}")
            continue
        if vehicle_id in seen_vehicles:
            violations.append(f"duplicate_vehicle_route:{vehicle_id}")
        seen_vehicles.add(vehicle_id)
        vehicle = vehicles[vehicle_id]
        stops = list(route.get("stops", ()))
        if len(stops) < 2:
            violations.append(f"route_too_short:{vehicle_id}")
            continue
        if stops[0].get("stop_kind") != "depot_start" or stops[-1].get("stop_kind") != "depot_end":
            violations.append(f"depot_boundary:{vehicle_id}")
        if stops[0].get("node_id") != vehicle["start_node_id"]:
            violations.append(f"start_node:{vehicle_id}")
        if stops[-1].get("node_id") != vehicle["end_node_id"]:
            violations.append(f"end_node:{vehicle_id}")

        start_at = int(stops[0].get("arrival_at_s", -1))
        end_at = int(stops[-1].get("arrival_at_s", -1))
        shift = vehicle["shift_window"]
        if start_at < max(int(shift["start_s"]), int(vehicle["available_at_s"])):
            violations.append(f"shift_start:{vehicle_id}")
        if end_at > int(shift["end_s"]):
            violations.append(f"shift_end:{vehicle_id}")
        if end_at < start_at:
            violations.append(f"route_time_reversed:{vehicle_id}")

        total_weight = 0
        total_volume = 0
        for oid in selected_ids:
            if oid not in selected_orders:
                continue
        route_order_ids = []
        for stop in stops[1:-1]:
            if stop.get("stop_kind") != "delivery":
                violations.append(f"unexpected_stop_kind:{vehicle_id}")
                continue
            order_ids = tuple(stop.get("order_ids", ()))
            if len(order_ids) != 1:
                violations.append(f"delivery_order_cardinality:{vehicle_id}")
                continue
            oid = str(order_ids[0])
            route_order_ids.append(oid)
            seen_orders.append(oid)
            if oid not in selected_orders:
                violations.append(f"order_not_requested:{oid}")
                continue
            order = selected_orders[oid]
            if stop.get("node_id") != order["delivery_node_id"]:
                violations.append(f"order_node_mismatch:{oid}")
            if vehicle["warehouse_id"] != order["warehouse_id"]:
                violations.append(f"warehouse_mismatch:{oid}:{vehicle_id}")
            if vehicle["temperature_zone"] != order["temperature_zone"]:
                violations.append(f"temperature:{oid}:{vehicle_id}")
            handoff = handoffs.get(oid)
            if not handoff:
                violations.append(f"missing_handoff:{oid}")
            else:
                if start_at < int(handoff["ready_at_s"]):
                    violations.append(f"ready_at:{oid}:{vehicle_id}")
                if start_at > int(handoff["loading_window"]["end_s"]):
                    violations.append(f"loading_window:{oid}:{vehicle_id}")

            arrival = int(stop["arrival_at_s"])
            service_start = int(stop["service_start_at_s"])
            departure = int(stop["departure_at_s"])
            if arrival != service_start:
                violations.append(f"service_start_semantics:{oid}")
            if departure - service_start != int(order["service_duration_s"]):
                violations.append(f"service_duration:{oid}")
            window = order["service_window"]
            if not int(window["start_s"]) <= service_start <= int(window["end_s"]):
                violations.append(f"service_window:{oid}")
            if departure > int(order["freshness_deadline_s"]):
                violations.append(f"freshness:{oid}")

            total_weight += int(order["weight_kg"])
            total_volume += int(order["volume_l"])

        if total_weight > int(vehicle["remaining_weight_kg"]):
            violations.append(f"weight_capacity:{vehicle_id}")
        if total_volume > int(vehicle["remaining_volume_l"]):
            violations.append(f"volume_capacity:{vehicle_id}")

        # Recompute route continuity and loads from the plain output.
        expected_load_w = total_weight
        expected_load_v = total_volume
        first = stops[0]
        if int(first.get("load_weight_kg", -1)) != expected_load_w:
            violations.append(f"start_load_weight:{vehicle_id}")
        if int(first.get("load_volume_l", -1)) != expected_load_v:
            violations.append(f"start_load_volume:{vehicle_id}")

        recomputed_distance = 0
        for prev, curr in zip(stops, stops[1:]):
            prev_depart = int(prev["departure_at_s"])
            curr_arrive = int(curr["arrival_at_s"])
            duration_s, distance_m = _matrix_lookup(matrix, prev["node_id"], curr["node_id"])
            if duration_s is None or distance_m is None:
                violations.append(f"unreachable_arc:{vehicle_id}:{prev['node_id']}->{curr['node_id']}")
                continue
            if curr_arrive < prev_depart + int(duration_s):
                violations.append(f"travel_time:{vehicle_id}:{prev['node_id']}->{curr['node_id']}")
            recomputed_distance += int(distance_m)
        if int(route.get("distance_m", -1)) != recomputed_distance:
            violations.append(f"distance_mismatch:{vehicle_id}")
        if int(route.get("duration_s", -1)) != end_at - start_at:
            violations.append(f"duration_mismatch:{vehicle_id}")

        for stop in stops[1:-1]:
            if stop.get("stop_kind") != "delivery" or len(tuple(stop.get("order_ids", ()))) != 1:
                continue
            oid = str(tuple(stop["order_ids"])[0])
            order = selected_orders.get(oid)
            if order is None:
                continue
            expected_load_w -= int(order["weight_kg"])
            expected_load_v -= int(order["volume_l"])
            if int(stop.get("load_weight_kg", -1)) != expected_load_w:
                violations.append(f"load_weight_transition:{oid}")
            if int(stop.get("load_volume_l", -1)) != expected_load_v:
                violations.append(f"load_volume_transition:{oid}")
        if int(stops[-1].get("load_weight_kg", -1)) != 0 or int(stops[-1].get("load_volume_l", -1)) != 0:
            violations.append(f"end_load_not_zero:{vehicle_id}")

    arrival_by_vehicle = {a["vehicle_id"]: a for a in result.get("warehouse_arrivals", ())}
    if set(arrival_by_vehicle) != set(vehicles):
        violations.append("warehouse_arrival_coverage")
    for route in routes:
        vehicle_id = route.get("vehicle_id")
        arrival = arrival_by_vehicle.get(vehicle_id)
        if arrival is None:
            continue
        stops = list(route.get("stops", ()))
        if stops and int(arrival.get("arrival_at_s", -1)) != int(stops[-1].get("arrival_at_s", -2)):
            violations.append(f"warehouse_arrival_time:{vehicle_id}")
        route_order_ids = tuple(oid for stop in stops if stop.get("stop_kind") == "delivery" for oid in tuple(stop.get("order_ids", ())))
        if tuple(arrival.get("order_ids", ())) != route_order_ids:
            violations.append(f"warehouse_arrival_orders:{vehicle_id}")

    # First-phase contract: every in-scope vehicle has a route and every required order is served once.
    if set(seen_vehicles) != set(vehicles):
        violations.append("vehicle_coverage")
    required = {oid for oid in selected_ids if selected_orders.get(oid, {}).get("required") is True}
    duplicates = {oid for oid in seen_orders if seen_orders.count(oid) > 1}
    if duplicates:
        violations.extend(f"duplicate_order:{oid}" for oid in sorted(duplicates))
    if not required.issubset(set(seen_orders)):
        violations.extend(f"required_unserved:{oid}" for oid in sorted(required - set(seen_orders)))

    return TransportValidation(not violations, tuple(violations))
