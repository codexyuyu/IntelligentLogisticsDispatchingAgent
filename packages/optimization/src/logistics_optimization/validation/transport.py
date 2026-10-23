"""Independent transport validation subset (P10-01).

The frozen ``TransportPlan`` carries routes and cost but not the route-stop rows; stop-level
time/capacity validation is performed by the joint validator (P10-02) once route stops are
bound to the plan. This module never trusts the solver's own status and checks the parts the
plan actually exposes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from logistics_domain.planning import Severity, TransportPlan, ValidationReport, Violation, content_hash
from logistics_domain.transport import TransportProblem


def validate_transport(plan: TransportPlan, problem: TransportProblem) -> ValidationReport:
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
    valid = not any(violation.severity == Severity.HARD for violation in violations)
    return ValidationReport(id=uuid4(), candidate_hash=content_hash(plan),
        snapshot_hash=problem.snapshot.hash, rules_version="1.0.0", valid=valid,
        required_codes=(), checked_codes=(), unsupported_codes=(),
        violations=tuple(violations),
        validated_at=datetime.now(timezone.utc).replace(microsecond=0))


__all__ = ["validate_transport"]
