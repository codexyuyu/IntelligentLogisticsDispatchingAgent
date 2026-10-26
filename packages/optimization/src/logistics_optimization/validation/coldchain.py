"""Independent cold-chain checks over a warehouse solution.

Only checks that the current snapshot can evidence are reported. Missing
pre-cooling/loading operations are surfaced as ``not_checked`` rather than
silently treated as zero exposure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import pairwise
from uuid import UUID

from logistics_domain.coldchain import CapacityUnit, ExposureScope
from logistics_domain.planning import Severity, Violation
from logistics_domain.warehouse import WarehouseProblem, WarehouseSolution


@dataclass
class ColdChainValidation:
    violations: list[Violation] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)


def _merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _peak(entries: list[tuple[int, int, int]]) -> int:
    events = []
    for start, end, amount in entries:
        events.append((start, amount))
        events.append((end, -amount))
    active = peak = 0
    for _, delta in sorted(events, key=lambda item: (item[0], item[1])):
        active += delta
        peak = max(peak, active)
    return peak


def validate_coldchain(problem: WarehouseProblem, solution: WarehouseSolution) -> ColdChainValidation:
    coldchain = problem.snapshot.coldchain
    outcome = ColdChainValidation()
    if coldchain is None:
        return outcome

    by_task: dict[UUID, list] = {}
    for assignment in solution.assignments:
        by_task.setdefault(assignment.task_id, []).append(assignment)
    task_by_id = {task.id: task for task in problem.tasks}
    def violation(code, actual, expected, message):
        outcome.violations.append(Violation(code, Severity.HARD, (), 'coldchain',
                                           str(actual), str(expected), message))
    if coldchain.horizon_s != problem.snapshot.scope.horizon_s:
        violation('coldchain_horizon', coldchain.horizon_s, problem.snapshot.scope.horizon_s,
                  'coldchain and planning horizons differ')

    for requirement in coldchain.precool_requirements:
        precool = by_task.get(requirement.precool_operation_id)
        if not precool:
            outcome.unsupported.append("r05.precool:missing_operation")
            continue
        task = task_by_id.get(requirement.precool_operation_id)
        if task is None or task.duration_s < requirement.min_duration_s:
            outcome.violations.append(Violation(code="coldchain_precool_duration",
                severity=Severity.HARD, entity_refs=(), field_path="precool.min_duration_s",
                actual=str(task.duration_s if task else "missing"),
                expected=f">= {requirement.min_duration_s}",
                message="pre-cooling task is shorter than its declared minimum"))
        precool_end = max(item.end_s for item in precool)
        if not any(a.resource_id in requirement.eligible_resource_ids for a in precool):
            violation('coldchain_precool_resource', 'ineligible', 'eligible resource', 'pre-cooling resource mismatch')
        for loading_id in requirement.loading_operation_ids:
            loading = by_task.get(loading_id)
            if not loading:
                outcome.unsupported.append("r05.precool:missing_loading_operation")
                continue
            if min(item.start_s for item in loading) < precool_end:
                outcome.violations.append(Violation(code="coldchain_precool_precedence",
                    severity=Severity.HARD, entity_refs=(), field_path="precool.loading",
                    actual=str(min(item.start_s for item in loading)),
                    expected=f">= {precool_end}",
                    message="loading starts before pre-cooling finishes"))
        outcome.checked.append("r05.precool")

    occupancy_intervals = []
    exposure: dict[str, list[tuple[int, int]]] = {}
    for occupancy in coldchain.occupancies:
        if occupancy.inbound_operation_id is not None:
            inbound = by_task.get(occupancy.inbound_operation_id)
            if not inbound:
                outcome.unsupported.append("r05.occupancy:missing_inbound")
                continue
            start = max(item.end_s for item in inbound)
        else:
            start = 0 if occupancy.origin == "initial_stock" else int(occupancy.declared_start_s or 0)
        if occupancy.outbound_operation_id is not None:
            outbound = by_task.get(occupancy.outbound_operation_id)
            if not outbound:
                outcome.unsupported.append("r05.occupancy:missing_outbound")
                continue
            end = min(item.start_s for item in outbound)
        else:
            end = coldchain.horizon_s
        if end < start or start < 0 or end > coldchain.horizon_s:
            violation('coldchain_occupancy_window', f'{start}..{end}', f'0..{coldchain.horizon_s}',
                      'storage occupancy has reversed or out-of-horizon endpoints')
        if end <= start:
            continue
        occupancy_intervals.append((occupancy, start, end))
        exposure.setdefault(occupancy.batch_id, []).append((start, end))

    locations = {item.location_id: item for item in coldchain.storage_locations}
    by_location_unit: dict[tuple[UUID, CapacityUnit, int, int], list[tuple[int, int, int, int]]] = {}
    for occupancy, start, end in occupancy_intervals:
        location = locations.get(occupancy.location_id)
        if location is None:
            outcome.violations.append(Violation(code="coldchain_unknown_location",
                severity=Severity.HARD, entity_refs=(), field_path="occupancy.location_id",
                actual=str(occupancy.location_id), expected="declared storage location",
                message="storage occupancy references an unknown location"))
            continue
        declared = {item.unit: item.amount for item in location.capacities}
        clipped: list[tuple[int, int]] = []
        if location.available_windows:
            for window in location.available_windows:
                left, right = max(start, window.earliest_s), min(end, window.latest_s)
                if right > left:
                    clipped.append((left, right))
            clipped = _merge(clipped)
            covered = sum(right - left for left, right in clipped)
            if covered != end - start:
                outcome.violations.append(Violation(code="coldchain_storage_window",
                    severity=Severity.HARD, entity_refs=(), field_path="storage.available_windows",
                    actual=f"[{start},{end})", expected="inside available windows",
                    message="storage occupancy lies outside the location availability windows"))
            if not clipped:
                continue
        else:
            clipped = [(start, end)]
        if location.capacity_periods:
            for left, right in clipped:
                covered = sum(max(0, min(right, period.end_s) - max(left, period.start_s))
                              for period in location.capacity_periods)
                if covered != right - left:
                    outcome.violations.append(Violation(code="coldchain_capacity_uncovered",
                        severity=Severity.HARD, entity_refs=(), field_path="storage.capacity_periods",
                        actual=f"[{left},{right})", expected="covered by capacity periods",
                        message="storage occupancy has no effective capacity period"))
            for period in location.capacity_periods:
                period_caps = {item.unit: item.amount for item in period.capacities}
                for use in occupancy.capacity_use:
                    if use.unit not in period_caps:
                        outcome.violations.append(Violation(code="coldchain_undeclared_capacity",
                            severity=Severity.HARD, entity_refs=(), field_path="capacity_use",
                            actual=use.unit.value, expected="capacity in active period",
                            message="occupancy consumes a capacity dimension absent from its period"))
                        continue
                    for left, right in clipped:
                        overlap_left, overlap_right = max(left, period.start_s), min(right, period.end_s)
                        if overlap_right <= overlap_left:
                            continue
                        by_location_unit.setdefault(
                            (location.location_id, use.unit, period.start_s, period.end_s),
                            []).append((overlap_left, overlap_right, use.amount, period_caps[use.unit]))
        else:
            for use in occupancy.capacity_use:
                if use.unit not in declared:
                    outcome.violations.append(Violation(code="coldchain_undeclared_capacity",
                        severity=Severity.HARD, entity_refs=(), field_path="capacity_use",
                        actual=use.unit.value, expected="declared capacity unit",
                        message="occupancy consumes an undeclared capacity dimension"))
                    continue
                for left, right in clipped:
                    by_location_unit.setdefault((location.location_id, use.unit, 0, 10**18),
                        []).append((left, right, use.amount, declared[use.unit]))
    for (_location_id, _unit, _period_start, _period_end), entries in by_location_unit.items():
        capacity = entries[0][3]
        peak = _peak([(start, end, amount) for start, end, amount, _ in entries])
        if peak > capacity:
            outcome.violations.append(Violation(code="coldchain_capacity",
                severity=Severity.HARD, entity_refs=(), field_path="storage.capacity",
                actual=str(peak), expected=f"<= {capacity}",
                message="time-varying storage capacity is exceeded"))
    if occupancy_intervals:
        outcome.checked.append("r05.storage_capacity")
        outcome.checked.append("r05.occupancy")

    zones = {z.zone_id: z for z in coldchain.zones}
    batches = {b.batch_id: b for b in coldchain.batch_compatibility}
    zone_entries = {}
    for occupancy, start, end in occupancy_intervals:
        location = locations.get(occupancy.location_id)
        zone = zones.get(location.zone_id) if location else None
        batch = batches.get(occupancy.batch_id)
        if zone is None or batch is None:
            outcome.unsupported.append('r05.compatibility:missing_zone_or_batch')
            continue
        if (location.warehouse_id != zone.warehouse_id or batch.warehouse_id != zone.warehouse_id
                or not batch.min_temperature_decic <= zone.setpoint_decic <= batch.max_temperature_decic):
            violation('coldchain_temperature', zone.setpoint_decic, 'batch temperature/warehouse',
                      'storage temperature or warehouse is incompatible with batch')
        for use in occupancy.capacity_use:
            zone_entries.setdefault((zone.zone_id, use.unit), []).append((start, end, use.amount))
    for (zone_id, unit), entries in zone_entries.items():
        capacity = next((c.amount for c in zones[zone_id].capacities if c.unit == unit), 0)
        peak = _peak(entries)
        if peak > capacity:
            violation('coldchain_zone_capacity', peak, capacity, 'aggregate zone capacity exceeded')
    if coldchain.compatibility_policy:
        banned = {frozenset(p) for p in coldchain.compatibility_policy.incompatible_class_pairs}
        for i, (a, start, end) in enumerate(occupancy_intervals):
            for b, other_start, other_end in occupancy_intervals[i+1:]:
                if a.batch_id not in batches or b.batch_id not in batches:
                    continue
                if a.location_id not in locations or b.location_id not in locations:
                    continue
                if (locations[a.location_id].zone_id == locations[b.location_id].zone_id
                        and start < other_end and other_start < end
                        and frozenset((batches[a.batch_id].compatibility_class,
                                       batches[b.batch_id].compatibility_class)) in banned):
                    violation('coldchain_incompatible_batches', f'{a.batch_id}/{b.batch_id}',
                              'nonoverlapping storage', 'incompatible batches overlap in one zone')

    # Check declared cleaning even when no separate warehouse SetupPolicy was supplied.
    primary = {}
    for assignment in solution.assignments:
        task = task_by_id.get(assignment.task_id)
        if task and assignment.resource_id in task.requirements[0].eligible_ids:
            primary.setdefault(assignment.resource_id, []).append(assignment)
    for resource, assignments in primary.items():
        ordered = sorted(assignments, key=lambda a: (a.start_s, str(a.task_id)))
        for left, right in pairwise(ordered):
            a, b = task_by_id[left.task_id].setup_class, task_by_id[right.task_id].setup_class
            if a == b:
                continue
            durations = [r.duration_s for p in coldchain.setup_policies for r in p.rules
                         if r.from_class == a and r.to_class == b]
            if not durations:
                durations = [p.default_duration_s for p in coldchain.setup_policies if p.default_duration_s is not None]
            if durations and (right.start_s-left.end_s < max(durations) or not any(
                    s.resource_id == resource and s.from_class == a and s.to_class == b
                    and s.end_s-s.start_s >= max(durations) and left.end_s <= s.start_s
                    and s.end_s <= right.start_s for s in solution.setup_operations)):
                violation('coldchain_changeover', f'{a}->{b}', max(durations), 'required cleaning gap missing')

    limits = {item.batch_id: item for item in coldchain.exposure_limits}
    for batch_id, intervals in exposure.items():
        limit = limits.get(batch_id)
        if limit is None:
            outcome.unsupported.append(f"r05.exposure:{batch_id}:no_limit")
            continue
        intervals = list(intervals) if ExposureScope.IN_WAREHOUSE in limit.scopes else []
        for req in coldchain.precool_requirements:
            if req.batch_id != batch_id or req.precool_operation_id not in by_task:
                continue
            ready = max(a.end_s for a in by_task[req.precool_operation_id])
            for loading_id in req.loading_operation_ids:
                loading = by_task.get(loading_id, ())
                if not loading:
                    continue
                start, end = min(a.start_s for a in loading), max(a.end_s for a in loading)
                if ExposureScope.WAITING in limit.scopes and start > ready:
                    intervals.append((ready, start))
                if ExposureScope.LOADING in limit.scopes:
                    intervals.append((start, end))
        if ExposureScope.TRANSPORT in limit.scopes:
            outcome.unsupported.append(f'r05.exposure:{batch_id}:transport_requires_joint_evidence')
        if not intervals:
            outcome.unsupported.append(f'r05.exposure:{batch_id}:no_measured_segments')
            continue
        total = sum(end - start for start, end in _merge(intervals))
        if total > limit.max_exposure_s:
            outcome.violations.append(Violation(code="coldchain_exposure",
                severity=Severity.HARD, entity_refs=(), field_path="exposure.in_warehouse",
                actual=str(total), expected=f"<= {limit.max_exposure_s}",
                message="cumulative in-warehouse exposure exceeds its limit"))
        outcome.checked.append(f"r05.exposure:{batch_id}")
    if limits and not exposure:
        outcome.unsupported.append("r05.exposure:no_measured_segments")
    return outcome
