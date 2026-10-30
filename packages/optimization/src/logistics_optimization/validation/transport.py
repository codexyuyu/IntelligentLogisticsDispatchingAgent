"""Independent transport validation (P10-01 subset).

The frozen ``TransportPlan`` carries routes and cost; optional route-stop rows add
service-window, sequence and order-coverage checks. The validator never trusts the solver's
own status and never mutates the plan.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from logistics_domain.planning import (
    RouteStop,
    Severity,
    TransportPlan,
    ValidationReport,
    Violation,
    content_hash,
)
from logistics_domain.transport import TransportProblem


def validate_transport(plan: TransportPlan, problem: TransportProblem,
                       stops: tuple[RouteStop, ...] = ()) -> ValidationReport:
    violations: list[Violation] = []
    vehicles = {vehicle.vehicle_id for vehicle in problem.vehicles}
    route_ids = set()
    used_vehicles = set()
    for route in plan.routes:
        if route.vehicle_id not in vehicles:
            violations.append(Violation(code="unknown_vehicle", severity=Severity.HARD,
                entity_refs=(), field_path="route.vehicle_id", actual=str(route.vehicle_id),
                expected="vehicle in problem", message="route uses a vehicle outside the problem"))
        if route.id in route_ids:
            violations.append(Violation(code="duplicate_route", severity=Severity.HARD,
                entity_refs=(), field_path="route.id", actual=str(route.id),
                expected="unique route id", message="plan repeats a route id"))
        route_ids.add(route.id)
        if route.vehicle_id in used_vehicles:
            violations.append(Violation(code="vehicle_twice", severity=Severity.HARD,
                entity_refs=(), field_path="route.vehicle_id", actual=str(route.vehicle_id),
                expected="one route per vehicle", message="a vehicle is assigned more than one route"))
        used_vehicles.add(route.vehicle_id)
        if route.total_distance_m < 0:
            violations.append(Violation(code="negative_distance", severity=Severity.HARD,
                entity_refs=(), field_path="route.total_distance_m",
                actual=str(route.total_distance_m), expected=">= 0",
                message="route distance is negative"))
    cost_sum = (plan.cost.distance_cents + plan.cost.fixed_vehicle_cents
                + plan.cost.service_cents + plan.cost.overtime_cents + plan.cost.setup_cents)
    if cost_sum != plan.cost.total_cents:
        violations.append(Violation(code="cost_sum", severity=Severity.HARD,
            entity_refs=(), field_path="plan.cost.total_cents",
            actual=str(plan.cost.total_cents), expected=str(cost_sum),
            message="plan cost total does not equal its components"))
    node_windows = {node.id: node.hard_window for node in problem.nodes}
    vehicle_by_id = {vehicle.vehicle_id: vehicle for vehicle in problem.vehicles}
    cargo_by_order = {}
    for cargo in problem.snapshot.cargo:
        cargo_by_order.setdefault(cargo.order_id, []).append(cargo)
    orders_by_route = {}
    visited_orders = set()
    seen_stops = set()
    sequences: dict = {}
    if stops:
        for stop in stops:
            if stop.id in seen_stops:
                violations.append(Violation(code="duplicate_stop", severity=Severity.HARD,
                    entity_refs=(), field_path="stop.id", actual=str(stop.id),
                    expected="unique stop id", message="plan repeats a route stop"))
            seen_stops.add(stop.id)
            if stop.route_id not in route_ids:
                violations.append(Violation(code="stop_route", severity=Severity.HARD,
                    entity_refs=(), field_path="stop.route_id", actual=str(stop.route_id),
                    expected="route in plan", message="stop references a route outside the plan"))
            previous = sequences.get(stop.route_id)
            if previous is not None and stop.sequence <= previous:
                violations.append(Violation(code="stop_sequence", severity=Severity.HARD,
                    entity_refs=(), field_path="stop.sequence", actual=str(stop.sequence),
                    expected=f"> {previous}", message="route stops are not strictly ordered"))
            sequences[stop.route_id] = stop.sequence
            if not stop.arrival_s <= stop.service_start_s <= stop.departure_s:
                violations.append(Violation(code="stop_times", severity=Severity.HARD,
                    entity_refs=(), field_path="stop.service_start_s",
                    actual=str(stop.service_start_s), expected="arrival<=start<=departure",
                    message="route stop times are inconsistent"))
            window = node_windows.get(stop.node_id)
            if window is not None and not window.contains_start(stop.service_start_s):
                violations.append(Violation(code="time_window", severity=Severity.HARD,
                    entity_refs=(), field_path="stop.service_start_s",
                    actual=str(stop.service_start_s),
                    expected=f"[{window.earliest_s},{window.latest_s}]",
                    message="service start is outside the hard window"))
            visited_orders.update(stop.task_ids)
            orders_by_route.setdefault(stop.route_id, set()).update(stop.task_ids)
        for route_id, order_ids in orders_by_route.items():
            vehicle = vehicle_by_id.get(next(
                (route.vehicle_id for route in plan.routes if route.id == route_id), None))
            route_stops = sorted((stop for stop in stops if stop.route_id == route_id),
                                 key=lambda stop: stop.sequence)
            if vehicle is None:
                continue
            previous_load = None
            for stop in route_stops:
                if (stop.load_before.weight_g > vehicle.capacity_weight_g
                        or stop.load_before.volume_cm3 > vehicle.capacity_volume_cm3
                        or stop.load_after.weight_g > vehicle.capacity_weight_g
                        or stop.load_after.volume_cm3 > vehicle.capacity_volume_cm3):
                    violations.append(Violation(code="vehicle_capacity", severity=Severity.HARD,
                        entity_refs=(), field_path="stop.load_after",
                        actual=f"{stop.load_after.weight_g}/{stop.load_after.volume_cm3}",
                        expected=f"<={vehicle.capacity_weight_g}/{vehicle.capacity_volume_cm3}",
                        message="route stop load exceeds vehicle capacity"))
                if previous_load is not None and stop.load_before != previous_load:
                    violations.append(Violation(code="load_continuity", severity=Severity.HARD,
                        entity_refs=(), field_path="stop.load_before",
                        actual=str(stop.load_before), expected=str(previous_load),
                        message="load before a stop differs from the previous stop load after"))
                previous_load = stop.load_after
            for order_id in order_ids:
                for cargo in cargo_by_order.get(order_id, ()):
                    if vehicle.allowed_cargo_types and cargo.cargo_type not in vehicle.allowed_cargo_types:
                        violations.append(Violation(code="cargo_type", severity=Severity.HARD,
                            entity_refs=(), field_path="route.vehicle_id", actual=cargo.cargo_type.value,
                            expected="compatible vehicle cargo class", message="vehicle cargo class mismatch"))
                    if not (cargo.min_temp_decic <= vehicle.setpoint_decic
                            <= cargo.max_temp_decic):
                        violations.append(Violation(code="temperature",
                            severity=Severity.HARD, entity_refs=(),
                            field_path="route.vehicle_id", actual=str(vehicle.setpoint_decic),
                            expected=f"[{cargo.min_temp_decic},{cargo.max_temp_decic}]",
                            message="vehicle setpoint is outside the cargo temperature range"))
        required = {node.order_id for node in problem.nodes
                    if node.order_id is not None and node.kind.value == "pickup"}
        missing = required - visited_orders
        if missing:
            violations.append(Violation(code="order_coverage", severity=Severity.HARD,
                entity_refs=(), field_path="stops.task_ids",
                actual=str(len(missing)) + " missing", expected="every required order",
                message="not every required order appears in the route stops"))
    valid = not any(violation.severity == Severity.HARD for violation in violations)
    content = {"plan": plan, "stops": stops}
    return ValidationReport(id=uuid4(), candidate_hash=content_hash(content),
        snapshot_hash=problem.snapshot.hash, rules_version="1.0.0", valid=valid,
        required_codes=(), checked_codes=(), unsupported_codes=(),
        violations=tuple(violations),
        validated_at=datetime.now(timezone.utc).replace(microsecond=0))


__all__ = ["validate_transport"]
