"""Independent cold-chain checks over a warehouse solution.

Only checks that the current snapshot can evidence are reported. Missing
pre-cooling/loading operations are surfaced as ``not_checked`` rather than
silently treated as zero exposure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
        if end <= start:
            continue
        occupancy_intervals.append((occupancy, start, end))
        exposure.setdefault(occupancy.batch_id, []).append((start, end))

    locations = {item.location_id: item for item in coldchain.storage_locations}
    by_location_unit: dict[tuple[UUID, CapacityUnit], list[tuple[int, int, int]]] = {}
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
        for use in occupancy.capacity_use:
            if use.unit not in declared:
                outcome.violations.append(Violation(code="coldchain_undeclared_capacity",
                    severity=Severity.HARD, entity_refs=(), field_path="capacity_use",
                    actual=use.unit.value, expected="declared capacity unit",
                    message="occupancy consumes an undeclared capacity dimension"))
                continue
            for left, right in clipped:
                by_location_unit.setdefault((location.location_id, use.unit), []).append(
                    (left, right, use.amount))
    for (location_id, unit), entries in by_location_unit.items():
        capacity = next(item.amount for item in locations[location_id].capacities
                        if item.unit == unit)
        peak = _peak(entries)
        if peak > capacity:
            outcome.violations.append(Violation(code="coldchain_capacity",
                severity=Severity.HARD, entity_refs=(), field_path="storage.capacity",
                actual=str(peak), expected=f"<= {capacity}",
                message="time-varying storage capacity is exceeded"))
    if occupancy_intervals:
        outcome.checked.append("r05.storage_capacity")
        outcome.checked.append("r05.occupancy")

    limits = {item.batch_id: item for item in coldchain.exposure_limits}
    for batch_id, intervals in exposure.items():
        limit = limits.get(batch_id)
        if limit is None or ExposureScope.IN_WAREHOUSE not in limit.scopes:
            outcome.unsupported.append(f"r05.exposure:{batch_id}:no_limit")
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
