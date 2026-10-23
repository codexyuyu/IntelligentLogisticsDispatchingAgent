"""Independent warehouse validation (P10-02 subset)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from uuid import uuid4

from logistics_domain.planning import Severity, ValidationReport, Violation, content_hash
from logistics_domain.warehouse import WarehouseProblem, WarehouseSolution


def validate_warehouse(problem: WarehouseProblem,
                       solution: WarehouseSolution) -> ValidationReport:
    violations: list[Violation] = []
    tasks = {task.id: task for task in problem.tasks}
    resources = problem.snapshot.resources
    resource_by_id = {item.id: item for item in (
        *resources.warehouses, *resources.zones, *resources.locations,
        *resources.docks, *resources.workers, *resources.equipment)}
    equipment = {item.id: item for item in resources.equipment}
    docks = {item.id: item for item in resources.docks}
    locations = {item.id: item for item in resources.locations}
    zones = {item.id: item for item in resources.zones}
    cargo = {item.id: item for item in problem.snapshot.cargo}
    assigned: dict = {}
    by_resource: dict = {}
    for assignment in solution.assignments:
        task = tasks.get(assignment.task_id)
        if task is None:
            violations.append(Violation(code="unknown_task", severity=Severity.HARD,
                entity_refs=(), field_path="assignment.task_id",
                actual=str(assignment.task_id), expected="task in problem",
                message="assignment references an unknown warehouse task"))
            continue
        if assignment.task_id in assigned:
            violations.append(Violation(code="task_twice", severity=Severity.HARD,
                entity_refs=(), field_path="assignment.task_id",
                actual=str(assignment.task_id), expected="one assignment per task",
                message="a warehouse task is assigned more than once"))
        assigned[assignment.task_id] = assignment
        eligible = {resource_id for requirement in task.requirements
                    for resource_id in requirement.eligible_ids}
        if eligible and assignment.resource_id not in eligible:
            violations.append(Violation(code="ineligible_resource", severity=Severity.HARD,
                entity_refs=(), field_path="assignment.resource_id",
                actual=str(assignment.resource_id), expected="eligible resource",
                message="assignment uses a resource outside the task requirements"))
        resource = resource_by_id.get(assignment.resource_id)
        if resource is None:
            violations.append(Violation(code="unknown_resource", severity=Severity.HARD,
                entity_refs=(), field_path="assignment.resource_id",
                actual=str(assignment.resource_id), expected="resource in snapshot",
                message="assignment references a resource outside the snapshot"))
        else:
            resource_warehouse = getattr(resource, "warehouse_id", None)
            if resource_warehouse is not None and resource_warehouse != task.warehouse_id:
                violations.append(Violation(code="resource_warehouse", severity=Severity.HARD,
                    entity_refs=(), field_path="assignment.resource_id",
                    actual=str(resource_warehouse), expected=str(task.warehouse_id),
                    message="resource belongs to a different warehouse"))
            dock = docks.get(assignment.resource_id)
            if dock is not None and task.kind not in dock.supported_operations:
                violations.append(Violation(code="dock_operation", severity=Severity.HARD,
                    entity_refs=(), field_path="assignment.resource_id",
                    actual=task.kind.value, expected="supported dock operation",
                    message="dock does not support the task operation"))
            equipment_item = equipment.get(assignment.resource_id)
            if equipment_item is not None and assignment.units > equipment_item.quantity_capacity:
                violations.append(Violation(code="equipment_capacity", severity=Severity.HARD,
                    entity_refs=(), field_path="assignment.units",
                    actual=str(assignment.units),
                    expected=f"<= {equipment_item.quantity_capacity}",
                    message="assignment exceeds equipment quantity capacity"))
            matching = [requirement for requirement in task.requirements
                        if assignment.resource_id in requirement.eligible_ids]
            for requirement in matching:
                if assignment.units < requirement.units:
                    violations.append(Violation(code="insufficient_units", severity=Severity.HARD,
                        entity_refs=(), field_path="assignment.units",
                        actual=str(assignment.units), expected=f">= {requirement.units}",
                        message="assignment provides fewer units than required"))
        if assignment.start_s < task.window.earliest_s or assignment.end_s > task.window.latest_s:
            violations.append(Violation(code="time_window", severity=Severity.HARD,
                entity_refs=(), field_path="assignment.start_s",
                actual=f"{assignment.start_s}..{assignment.end_s}",
                expected=f"[{task.window.earliest_s},{task.window.latest_s}]",
                message="assignment lies outside the task start window"))
        if assignment.end_s - assignment.start_s != task.duration_s:
            violations.append(Violation(code="duration", severity=Severity.HARD,
                entity_refs=(), field_path="assignment.end_s",
                actual=str(assignment.end_s - assignment.start_s),
                expected=str(task.duration_s), message="assignment duration differs from task"))
        by_resource.setdefault(assignment.resource_id, []).append(assignment)
    missing = set(tasks) - set(assigned)
    if solution.assignments and missing:
        violations.append(Violation(code="task_coverage", severity=Severity.HARD,
            entity_refs=(), field_path="solution.assignments",
            actual=str(len(missing)) + " missing", expected="every task assigned",
            message="not every warehouse task has an assignment"))
    for resource_id, assignments in by_resource.items():
        assignments.sort(key=lambda item: item.start_s)
        equipment_item = equipment.get(resource_id)
        if equipment_item is not None:
            events = []
            for item in assignments:
                events.append((item.start_s, item.units))
                events.append((item.end_s, -item.units))
            active = peak = 0
            for _, delta in sorted(events, key=lambda pair: (pair[0], pair[1])):
                active += delta
                peak = max(peak, active)
            if peak > equipment_item.quantity_capacity:
                violations.append(Violation(code="equipment_overlap",
                    severity=Severity.HARD, entity_refs=(),
                    field_path="assignment.resource_id", actual=str(peak),
                    expected=f"<= {equipment_item.quantity_capacity}",
                    message="concurrent equipment demand exceeds capacity"))
            continue
        for left, right in zip(assignments, assignments[1:]):
            if left.end_s > right.start_s:
                violations.append(Violation(code="resource_overlap", severity=Severity.HARD,
                    entity_refs=(), field_path="assignment.resource_id",
                    actual=str(resource_id), expected="no overlap",
                    message="two warehouse assignments overlap on the same resource"))
    for task in problem.tasks:
        assignment = assigned.get(task.id)
        if assignment is None:
            continue
        for predecessor_id in task.predecessor_ids:
            predecessor = assigned.get(predecessor_id)
            if predecessor is not None and predecessor.end_s > assignment.start_s:
                violations.append(Violation(code="precedence", severity=Severity.HARD,
                    entity_refs=(), field_path="assignment.start_s",
                    actual=str(assignment.start_s), expected=f">= {predecessor.end_s}",
                    message="task starts before its predecessor finishes"))
    location_weight = defaultdict(int)
    location_volume = defaultdict(int)
    zone_weight = defaultdict(int)
    zone_volume = defaultdict(int)
    for interval in solution.storage_allocations:
        location = locations.get(interval.location_id)
        if location is None:
            violations.append(Violation(code="unknown_location", severity=Severity.HARD,
                entity_refs=(), field_path="storage.location_id",
                actual=str(interval.location_id), expected="location in snapshot",
                message="storage allocation references an unknown location"))
            continue
        location_weight[interval.location_id] += interval.weight_g
        location_volume[interval.location_id] += interval.volume_cm3
        zone = zones.get(location.zone_id)
        if zone is None:
            violations.append(Violation(code="unknown_zone", severity=Severity.HARD,
                entity_refs=(), field_path="storage.location_id",
                actual=str(location.zone_id), expected="zone in snapshot",
                message="storage location references an unknown zone"))
            continue
        zone_weight[location.zone_id] += interval.weight_g
        zone_volume[location.zone_id] += interval.volume_cm3
        cargo_item = cargo.get(interval.cargo_id)
        if cargo_item is None:
            violations.append(Violation(code="unknown_cargo", severity=Severity.HARD,
                entity_refs=(), field_path="storage.cargo_id",
                actual=str(interval.cargo_id), expected="cargo in snapshot",
                message="storage allocation references unknown cargo"))
        elif not cargo_item.min_temp_decic <= zone.setpoint_decic <= cargo_item.max_temp_decic:
            violations.append(Violation(code="temperature_setpoint", severity=Severity.HARD,
                entity_refs=(), field_path="storage.zone_id",
                actual=str(zone.setpoint_decic),
                expected=f"[{cargo_item.min_temp_decic},{cargo_item.max_temp_decic}]",
                message="zone setpoint is outside the cargo temperature range"))
    for location_id, weight in location_weight.items():
        location = locations[location_id]
        if weight > location.capacity_weight_g or location_volume[location_id] > location.capacity_volume_cm3:
            violations.append(Violation(code="location_capacity", severity=Severity.HARD,
                entity_refs=(), field_path="storage.location_id", actual=str(location_id),
                expected=f"weight<={location.capacity_weight_g}, volume<={location.capacity_volume_cm3}",
                message="storage allocation exceeds location capacity"))
    for zone_id, weight in zone_weight.items():
        zone = zones[zone_id]
        if weight > zone.capacity_weight_g or zone_volume[zone_id] > zone.capacity_volume_cm3:
            violations.append(Violation(code="zone_capacity", severity=Severity.HARD,
                entity_refs=(), field_path="storage.zone_id", actual=str(zone_id),
                expected=f"weight<={zone.capacity_weight_g}, volume<={zone.capacity_volume_cm3}",
                message="storage allocation exceeds zone capacity"))
    cost = solution.objective.business_cost_cents if solution.objective is not None else None
    if cost is not None and cost < 0:
        violations.append(Violation(code="negative_cost", severity=Severity.HARD,
            entity_refs=(), field_path="objective.business_cost_cents", actual=str(cost),
            expected=">= 0", message="objective cost is negative"))
    valid = not any(violation.severity == Severity.HARD for violation in violations)
    return ValidationReport(id=uuid4(),
        candidate_hash=content_hash({"assignments": solution.assignments,
            "storage": solution.storage_allocations, "setup": solution.setup_operations}),
        snapshot_hash=problem.snapshot.hash, rules_version="1.0.0", valid=valid,
        required_codes=(), checked_codes=(), unsupported_codes=(),
        violations=tuple(violations),
        validated_at=datetime.now(timezone.utc).replace(microsecond=0))


__all__ = ["validate_warehouse"]
