"""Independent warehouse validation (P10-02 subset)."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from itertools import pairwise
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
    workers = {item.id: item for item in resources.workers}
    locations = {item.id: item for item in resources.locations}
    zones = {item.id: item for item in resources.zones}
    cargo = {item.id: item for item in problem.snapshot.cargo}
    assigned_by_task: dict = {}
    covered_requirements: set = set()
    by_resource: dict = {}
    for assignment in solution.assignments:
        task = tasks.get(assignment.task_id)
        if task is None:
            violations.append(Violation(code="unknown_task", severity=Severity.HARD,
                entity_refs=(), field_path="assignment.task_id",
                actual=str(assignment.task_id), expected="task in problem",
                message="assignment references an unknown warehouse task"))
            continue
        assigned_by_task.setdefault(assignment.task_id, []).append(assignment)
        if len(assigned_by_task[assignment.task_id]) > len(task.requirements):
            violations.append(Violation(code="too_many_assignments", severity=Severity.HARD,
                entity_refs=(), field_path="assignment.task_id",
                actual=str(len(assigned_by_task[assignment.task_id])),
                expected=f"<= {len(task.requirements)}",
                message="task has more assignments than resource requirements"))
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
            worker = workers.get(assignment.resource_id)
            if task.required_skills and worker is not None:
                if worker is None:
                    violations.append(Violation(code="skill_resource",
                        severity=Severity.HARD, entity_refs=(),
                        field_path="assignment.resource_id",
                        actual=str(assignment.resource_id),
                        expected="worker resource with required skills",
                        message="skill-bearing task is assigned to a non-worker"))
                else:
                    missing_skills = set(task.required_skills) - set(worker.skills)
                    if missing_skills:
                        violations.append(Violation(code="worker_skills",
                            severity=Severity.HARD, entity_refs=(),
                            field_path="assignment.resource_id",
                            actual=",".join(sorted(missing_skills)),
                            expected="all required skills",
                            message="worker lacks a required skill"))
            matching = [requirement for requirement in task.requirements
                        if assignment.resource_id in requirement.eligible_ids]
            if not matching:
                violations.append(Violation(code="ineligible_resource", severity=Severity.HARD,
                    entity_refs=(), field_path="assignment.resource_id",
                    actual=str(assignment.resource_id), expected="resource in a task requirement",
                    message="assignment resource satisfies no task requirement"))
            for requirement in matching:
                requirement_index = task.requirements.index(requirement)
                key = (assignment.task_id, requirement_index)
                if key in covered_requirements:
                    violations.append(Violation(code="duplicate_requirement_assignment",
                        severity=Severity.HARD, entity_refs=(),
                        field_path="assignment.resource_id", actual=str(assignment.resource_id),
                        expected="one assignment per requirement",
                        message="task requirement has more than one assignment"))
                covered_requirements.add(key)
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
    missing = []
    for task in problem.tasks:
        for index, _ in enumerate(task.requirements):
            if (task.id, index) not in covered_requirements:
                missing.append((task.id, index))
    if solution.assignments and missing:
        violations.append(Violation(code="task_coverage", severity=Severity.HARD,
            entity_refs=(), field_path="solution.assignments",
            actual=str(len(missing)) + " missing requirements",
            expected="every task requirement assigned",
            message="not every warehouse task requirement has an assignment"))
    for resource_id, assignments in by_resource.items():
        assignments.sort(key=lambda item: item.start_s)
        equipment_item = equipment.get(resource_id)
        resource = resource_by_id.get(resource_id)
        if resource is not None:
            capacity = equipment_item.quantity_capacity if equipment_item else 1
            points = {p for a in assignments for p in (a.start_s, a.end_s)}
            points.update(p for iv in resource.calendar.intervals for p in (iv.start_s, iv.end_s))
            for left, right in pairwise(sorted(points)):
                load = sum(a.units for a in assignments if a.start_s < right and left < a.end_s)
                allowed = min(capacity, resource.calendar.available_units_at(left))
                if load > allowed:
                    violations.append(Violation('resource_calendar_capacity', Severity.HARD, (),
                        'assignment.resource_id', str(load), str(allowed), 'resource calendar capacity exceeded'))
            if resource.calendar.epoch_utc != problem.snapshot.scope.epoch_utc:
                violations.append(Violation('calendar_epoch', Severity.HARD, (), 'resource.calendar',
                    str(resource_id), 'scope epoch', 'calendar epoch differs from planning scope'))
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
        for left, right in pairwise(assignments):
            if left.end_s > right.start_s:
                violations.append(Violation(code="resource_overlap", severity=Severity.HARD,
                    entity_refs=(), field_path="assignment.resource_id",
                    actual=str(resource_id), expected="no overlap",
                    message="two warehouse assignments overlap on the same resource"))
    for task in problem.tasks:
        task_assignments = assigned_by_task.get(task.id, ())
        if not task_assignments:
            continue
        task_start = min(item.start_s for item in task_assignments)
        if len({(a.start_s, a.end_s) for a in task_assignments}) != 1:
            violations.append(Violation('operation_alignment', Severity.HARD, (), 'assignments',
                str(task.id), 'same start/end', 'simultaneous requirements have different intervals'))
        warehouse = resource_by_id.get(task.warehouse_id)
        task_end = max(a.end_s for a in task_assignments)
        if warehouse is not None:
            points = {task_start, task_end} | {p for iv in warehouse.calendar.intervals
                for p in (iv.start_s, iv.end_s) if task_start < p < task_end}
            if any(warehouse.calendar.available_units_at(t) <= 0 for t in sorted(points)[:-1]):
                violations.append(Violation('warehouse_closed', Severity.HARD, (), 'warehouse.calendar',
                    str(task.id), 'open throughout operation', 'warehouse closed during operation'))
        for predecessor_id in task.predecessor_ids:
            predecessor_assignments = assigned_by_task.get(predecessor_id, ())
            if predecessor_assignments:
                predecessor_end = max(item.end_s for item in predecessor_assignments)
                if predecessor_end > task_start:
                    violations.append(Violation(code="precedence", severity=Severity.HARD,
                        entity_refs=(), field_path="assignment.start_s",
                        actual=str(task_start), expected=f">= {predecessor_end}",
                        message="task starts before its predecessor finishes"))
    location_intervals = defaultdict(list)
    zone_intervals = defaultdict(list)
    # A cold-chain occupancy is identified by its occupancy UUID, rather than by
    # a registered Cargo.id. Cold-chain locations similarly live in the R05
    # snapshot, not necessarily in the legacy resources.locations collection.
    # Validate these records against their source occupancy and task assignments;
    # leave ordinary cargo/storage allocations on the existing validation path.
    coldchain = problem.snapshot.coldchain
    cold_occupancies = {item.occupancy_id: item for item in coldchain.occupancies} if coldchain else {}
    reuse = {item.location_id: item for item in coldchain.reuse_rules} if coldchain else {}
    cold_seen = set()
    for interval in solution.storage_allocations:
        occupancy = cold_occupancies.get(interval.cargo_id)
        if occupancy is not None:
            if interval.cargo_id in cold_seen:
                violations.append(Violation(code="coldchain_storage_duplicate", severity=Severity.HARD,
                    entity_refs=(), field_path="storage.cargo_id", actual=str(interval.cargo_id),
                    expected="one interval per occupancy", message="cold-chain occupancy is exported twice"))
            cold_seen.add(interval.cargo_id)
            quantities = {item.unit.value: item.amount for item in occupancy.capacity_use}
            declared = (quantities.get("quantity_units", 0), quantities.get("weight_g", 0),
                        quantities.get("volume_cm3", 0))
            actual = (interval.quantity_units, interval.weight_g, interval.volume_cm3)
            if interval.location_id != occupancy.location_id or actual != declared:
                violations.append(Violation(code="coldchain_storage_mismatch", severity=Severity.HARD,
                    entity_refs=(), field_path="storage", actual=str((interval.location_id, actual)),
                    expected=str((occupancy.location_id, declared)),
                    message="storage allocation differs from the declared cold-chain occupancy"))
            inbound = assigned_by_task.get(occupancy.inbound_operation_id) if occupancy.inbound_operation_id else None
            outbound = assigned_by_task.get(occupancy.outbound_operation_id) if occupancy.outbound_operation_id else None
            if ((occupancy.inbound_operation_id and not inbound)
                    or (occupancy.outbound_operation_id and not outbound)):
                violations.append(Violation(code="coldchain_storage_unverified", severity=Severity.HARD,
                    entity_refs=(), field_path="storage", actual=str(interval.cargo_id),
                    expected="linked warehouse assignments", message="storage endpoints lack operation evidence"))
            else:
                start = max(item.end_s for item in inbound) if inbound else (occupancy.declared_start_s or 0)
                end = min(item.start_s for item in outbound) if outbound else coldchain.horizon_s
                if not outbound and occupancy.location_id in reuse:
                    end = min(end, start + reuse[occupancy.location_id].max_batch_age_s)
                if (interval.start_s, interval.end_s) != (start, end):
                    violations.append(Violation(code="coldchain_storage_time", severity=Severity.HARD,
                        entity_refs=(), field_path="storage.start_s/end_s",
                        actual=f"{interval.start_s}..{interval.end_s}", expected=f"{start}..{end}",
                        message="storage interval differs from independently derived operation times"))
            continue
        location = locations.get(interval.location_id)
        if location is None:
            violations.append(Violation(code="unknown_location", severity=Severity.HARD,
                entity_refs=(), field_path="storage.location_id",
                actual=str(interval.location_id), expected="location in snapshot",
                message="storage allocation references an unknown location"))
            continue
        zone = zones.get(location.zone_id)
        if zone is None:
            violations.append(Violation(code="unknown_zone", severity=Severity.HARD,
                entity_refs=(), field_path="storage.location_id",
                actual=str(location.zone_id), expected="zone in snapshot",
                message="storage location references an unknown zone"))
            continue
        location_intervals[interval.location_id].append(interval)
        zone_intervals[location.zone_id].append(interval)
        cargo_item = cargo.get(interval.cargo_id)
        if cargo_item is None:
            violations.append(Violation(code="unknown_cargo", severity=Severity.HARD,
                entity_refs=(), field_path="storage.cargo_id",
                actual=str(interval.cargo_id), expected="cargo in snapshot",
                message="storage allocation references unknown cargo"))
            continue
        if (interval.quantity_units > cargo_item.quantity_units
                or interval.weight_g > cargo_item.weight_g
                or interval.volume_cm3 > cargo_item.volume_cm3):
            violations.append(Violation(code="cargo_over_allocated", severity=Severity.HARD,
                entity_refs=(), field_path="storage.cargo_id", actual=str(interval.cargo_id),
                expected="allocation <= cargo quantity/weight/volume",
                message="storage allocation exceeds the registered cargo"))
        if not cargo_item.min_temp_decic <= zone.setpoint_decic <= cargo_item.max_temp_decic:
            violations.append(Violation(code="temperature_setpoint", severity=Severity.HARD,
                entity_refs=(), field_path="storage.zone_id",
                actual=str(zone.setpoint_decic),
                expected=f"[{cargo_item.min_temp_decic},{cargo_item.max_temp_decic}]",
                message="zone setpoint is outside the cargo temperature range"))
    for location_id, intervals in location_intervals.items():
        location = locations[location_id]
        peak_weight = _peak(intervals, "weight_g")
        peak_volume = _peak(intervals, "volume_cm3")
        if peak_weight > location.capacity_weight_g or peak_volume > location.capacity_volume_cm3:
            violations.append(Violation(code="location_capacity", severity=Severity.HARD,
                entity_refs=(), field_path="storage.location_id", actual=str(location_id),
                expected=f"peak_weight<={location.capacity_weight_g}, peak_volume<={location.capacity_volume_cm3}",
                message="storage allocation exceeds location capacity"))
    for zone_id, intervals in zone_intervals.items():
        zone = zones[zone_id]
        peak_weight = _peak(intervals, "weight_g")
        peak_volume = _peak(intervals, "volume_cm3")
        if peak_weight > zone.capacity_weight_g or peak_volume > zone.capacity_volume_cm3:
            violations.append(Violation(code="zone_capacity", severity=Severity.HARD,
                entity_refs=(), field_path="storage.zone_id", actual=str(zone_id),
                expected=f"peak_weight<={zone.capacity_weight_g}, peak_volume<={zone.capacity_volume_cm3}",
                message="storage allocation exceeds zone capacity"))
    for resource_id, assignments in by_resource.items():
        ordered = sorted(assignments, key=lambda item: item.start_s)
        for left, right in pairwise(ordered):
            left_task = tasks.get(left.task_id)
            right_task = tasks.get(right.task_id)
            if left_task is None or right_task is None:
                continue
            if left_task.setup_class == right_task.setup_class:
                continue
            policy_transition = next((transition
                for transition in problem.setup_policy.transitions
                if transition.resource_id == resource_id
                and transition.from_class == left_task.setup_class
                and transition.to_class == right_task.setup_class), None)
            if policy_transition is None or policy_transition.duration_s <= 0:
                continue
            matched = any(setup.resource_id == resource_id
                and setup.from_class == left_task.setup_class
                and setup.to_class == right_task.setup_class
                and setup.start_s >= left.end_s and setup.end_s <= right.start_s
                for setup in solution.setup_operations)
            if not matched:
                violations.append(Violation(code="missing_setup", severity=Severity.HARD,
                    entity_refs=(), field_path="setup_operations",
                    actual=f"{left_task.setup_class}->{right_task.setup_class}",
                    expected="explicit setup between differing classes",
                    message="adjacent tasks with different setup classes lack a setup operation"))
    setup_by_resource = defaultdict(list)
    for setup in solution.setup_operations:
        if setup.resource_id not in resource_by_id:
            violations.append(Violation(code="unknown_setup_resource", severity=Severity.HARD,
                entity_refs=(), field_path="setup.resource_id",
                actual=str(setup.resource_id), expected="resource in snapshot",
                message="setup references an unknown resource"))
        if setup.cost_cents < 0:
            violations.append(Violation(code="negative_setup_cost", severity=Severity.HARD,
                entity_refs=(), field_path="setup.cost_cents", actual=str(setup.cost_cents),
                expected=">= 0", message="setup cost is negative"))
        for assignment in by_resource.get(setup.resource_id, ()):
            if setup.start_s < assignment.end_s and assignment.start_s < setup.end_s:
                violations.append(Violation(code="setup_assignment_overlap",
                    severity=Severity.HARD, entity_refs=(),
                    field_path="setup.resource_id", actual=str(setup.resource_id),
                    expected="no overlap with assignments",
                    message="setup overlaps a production assignment on the resource"))
        setup_by_resource[setup.resource_id].append(setup)
    for resource_id, setups in setup_by_resource.items():
        setups.sort(key=lambda item: item.start_s)
        for left, right in pairwise(setups):
            if left.end_s > right.start_s:
                violations.append(Violation(code="setup_overlap", severity=Severity.HARD,
                    entity_refs=(), field_path="setup.resource_id",
                    actual=str(resource_id), expected="no setup overlap",
                    message="two setup operations overlap on the same resource"))
    from logistics_optimization.validation.coldchain import validate_coldchain

    coldchain = validate_coldchain(problem, solution)
    violations.extend(coldchain.violations)
    cost = solution.objective.business_cost_cents if solution.objective is not None else None
    if cost is not None and cost < 0:
        violations.append(Violation(code="negative_cost", severity=Severity.HARD,
            entity_refs=(), field_path="objective.business_cost_cents", actual=str(cost),
            expected=">= 0", message="objective cost is negative"))
    valid = not coldchain.unsupported and not any(violation.severity == Severity.HARD for violation in violations)
    return ValidationReport(id=uuid4(),
        candidate_hash=content_hash({"assignments": solution.assignments,
            "storage": solution.storage_allocations, "setup": solution.setup_operations}),
        snapshot_hash=problem.snapshot.hash, rules_version="1.0.0", valid=valid,
        required_codes=tuple(sorted(set(coldchain.checked) | set(coldchain.unsupported))), checked_codes=tuple(coldchain.checked),
        unsupported_codes=tuple(coldchain.unsupported),
        violations=tuple(violations),
        validated_at=datetime.now(UTC).replace(microsecond=0))


def _peak(intervals, attribute: str) -> int:
    events = []
    for interval in intervals:
        value = getattr(interval, attribute)
        events.append((interval.start_s, value))
        events.append((interval.end_s, -value))
    active = peak = 0
    for _, delta in sorted(events, key=lambda pair: (pair[0], pair[1])):
        active += delta
        peak = max(peak, active)
    return peak


__all__ = ["validate_warehouse"]
