"""Independent R05 checks over a solved warehouse schedule.

The checks here re-derive every R05 fact from the snapshot and the *result*, and
never call the CP-SAT model builder or the timeline builder used by the solver.
If the solver silently drops a constraint, these functions still see the plan.

Missing evidence is never a pass: uncovered scopes, undeclared capacity
dimensions and absent batch profiles are reported as not-checked rule ids.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.contracts.coldchain import (
    CapacityAmount,
    ColdChainSnapshot,
    ScheduledOccupancy,
    SetupPolicy,
)
from app.contracts.common import RuleEvidence, Violation
from app.contracts.entities import Operation, ScheduledOperation
from app.contracts.planning import WarehouseScheduleRequest, WarehouseScheduleResult

RULES = (
    'r05.occupancy_declaration',
    'r05.storage_capacity',
    'r05.resource_requirements',
    'r05.resource_capacity',
    'r05.changeover',
    'r05.precool',
    'r05.exposure',
    'r05.batch_compatibility',
)


@dataclass
class CheckOutcome:
    violations: list[Violation] = field(default_factory=list)
    not_checked: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.violations:
            return 'failed'
        if self.not_checked:
            return 'not_checked'
        return 'passed'


def _setup_duration(policy: SetupPolicy, from_class: str, to_class: str) -> int | None:
    if from_class == to_class:
        return 0
    for rule in policy.rules:
        if rule.from_class == from_class and rule.to_class == to_class:
            return rule.duration_s
    return policy.default_duration_s


def _merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Union of half-open intervals; touching intervals merge."""
    merged: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _peak(entries: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    """Peak load of half-open ``[start, end)`` entries carrying a positive amount.

    Returns ``(peak, peak_start, peak_end)`` where the interval brackets the peak.
    Releases are applied before acquisitions at the same second, so a batch that
    leaves at ``t`` does not compete with one that enters at ``t``.
    """
    events: list[tuple[int, int]] = []
    for start, end, amount in entries:
        events.append((start, amount))
        events.append((end, -amount))
    events.sort(key=lambda item: (item[0], item[1]))
    current = 0
    peak = 0
    peak_at = 0
    for position, (moment, delta) in enumerate(events):
        current += delta
        if current > peak:
            peak = current
            peak_at = moment
    if not entries:
        return 0, 0, 0
    following = [moment for moment, _ in events if moment > peak_at]
    end = following[0] if following else peak_at
    return peak, peak_at, end


def derived_occupancies(request: WarehouseScheduleRequest,
                        result: WarehouseScheduleResult) -> tuple[ScheduledOccupancy, ...]:
    """Re-derive planned occupancies without the solver's timeline builder."""
    coldchain = request.snapshot.coldchain
    if coldchain is None:
        return ()
    scheduled = {item.operation_id: item for item in result.operations}
    horizon = coldchain.horizon_s
    derived: list[ScheduledOccupancy] = []
    for declared in coldchain.occupancies:
        if ((declared.inbound_operation_id is not None
             and declared.inbound_operation_id not in scheduled)
                or (declared.outbound_operation_id is not None
                    and declared.outbound_operation_id not in scheduled)):
            # Bounded by work outside this request: not part of this plan.
            continue
        if declared.origin == 'initial_stock':
            start = 0
        elif declared.inbound_operation_id is not None:
            inbound = scheduled.get(declared.inbound_operation_id)
            start = inbound.end_s if inbound is not None else 0
        else:
            start = int(declared.declared_start_s or 0)
        outbound = (scheduled.get(declared.outbound_operation_id)
                    if declared.outbound_operation_id is not None else None)
        end = outbound.start_s if outbound is not None else horizon
        if end <= start:
            continue
        derived.append(ScheduledOccupancy(
            occupancy_id=declared.occupancy_id,
            batch_id=declared.batch_id,
            location_id=declared.location_id,
            capacity_use=declared.capacity_use,
            start_s=start,
            end_s=end,
        ))
    return tuple(derived)


def check_occupancy_declaration(
    coldchain: ColdChainSnapshot,
    request: WarehouseScheduleRequest,
    result: WarehouseScheduleResult,
    outcome: CheckOutcome,
) -> None:
    declared_by_id = {item.occupancy_id: item for item in coldchain.occupancies}
    plan = result.coldchain
    if plan is None:
        outcome.not_checked.append('r05.occupancy_declaration:no_plan')
        return
    planned_by_id = {item.occupancy_id: item for item in plan.occupancies}
    derived_by_id = {item.occupancy_id: item for item in derived_occupancies(request, result)}

    for occupancy_id, declared in sorted(declared_by_id.items()):
        planned = planned_by_id.get(occupancy_id)
        derived = derived_by_id.get(occupancy_id)
        if derived is None:
            # Declared batch is never stored in the plan; nothing to check but it
            # must not silently appear as a stored interval either.
            if planned is not None:
                outcome.violations.append(Violation(
                    rule_id='r05.occupancy_declaration',
                    object_ids=(occupancy_id,),
                    message='plan stores a batch whose declared interval is empty',
                ))
            continue
        if planned is None:
            outcome.violations.append(Violation(
                rule_id='r05.occupancy_declaration',
                object_ids=(occupancy_id,),
                message='declared occupancy missing from the plan',
            ))
            continue
        if planned.model_dump(exclude={'start_s', 'end_s'}) != derived.model_dump(exclude={'start_s', 'end_s'}):
            outcome.violations.append(Violation(
                rule_id='r05.occupancy_declaration',
                object_ids=(occupancy_id,),
                message='planned occupancy differs from the declared batch/location/quantity',
            ))
        if (planned.start_s, planned.end_s) != (derived.start_s, derived.end_s):
            outcome.violations.append(Violation(
                rule_id='r05.occupancy_declaration',
                object_ids=(occupancy_id,),
                message='planned occupancy interval does not match its inbound/outbound operations',
                evidence=RuleEvidence(
                    rule_version=coldchain.rule_version,
                    interval_start_s=planned.start_s, interval_end_s=planned.end_s,
                    detail=f'derived [{derived.start_s},{derived.end_s})',
                ),
            ))
    for occupancy_id in sorted(set(planned_by_id) - set(declared_by_id)):
        outcome.violations.append(Violation(
            rule_id='r05.occupancy_declaration',
            object_ids=(occupancy_id,),
            message='plan contains an occupancy that the snapshot never declared',
        ))


def check_storage_capacity(
    coldchain: ColdChainSnapshot,
    result: WarehouseScheduleResult,
    outcome: CheckOutcome,
) -> None:
    if result.coldchain is None:
        outcome.not_checked.append('r05.storage_capacity:no_plan')
        return
    locations = {item.location_id: item for item in coldchain.storage_locations}
    occupancies = result.coldchain.occupancies
    if not locations:
        outcome.not_checked.append('r05.storage_capacity:no_storage_locations')
        return

    by_location: dict[str, list[ScheduledOccupancy]] = {}
    for occupancy in occupancies:
        by_location.setdefault(occupancy.location_id, []).append(occupancy)

    for location_id, items in sorted(by_location.items()):
        location = locations.get(location_id)
        if location is None:
            outcome.violations.append(Violation(
                rule_id='r05.storage_capacity',
                object_ids=tuple(sorted({item.occupancy_id for item in items})) + (location_id,),
                message='occupancy references a storage location that is not declared',
            ))
            continue
        capacity_by_unit = {amount.unit: amount.amount for amount in location.capacities}
        amounts: dict[str, list[tuple[int, int, int]]] = {}
        for occupancy in items:
            for use in occupancy.capacity_use:
                amounts.setdefault(use.unit, []).append(
                    (occupancy.start_s, occupancy.end_s, use.amount)
                )
        for unit, entries in sorted(amounts.items()):
            limit = capacity_by_unit.get(unit)
            if limit is None:
                outcome.not_checked.append(f'r05.storage_capacity:{location_id}:{unit}')
                continue
            peak, peak_start, peak_end = _peak(entries)
            if peak > limit:
                outcome.violations.append(Violation(
                    rule_id='r05.storage_capacity',
                    object_ids=(location_id,),
                    message=f'peak occupancy {peak} exceeds capacity {limit} in {unit}',
                    evidence=RuleEvidence(
                        rule_version=coldchain.rule_version, capacity_unit=unit,
                        observed_value=peak, limit_value=limit,
                        interval_start_s=peak_start, interval_end_s=peak_end,
                    ),
                ))
        for occupancy in items:
            for use in occupancy.capacity_use:
                if use.unit not in capacity_by_unit:
                    outcome.violations.append(Violation(
                        rule_id='r05.storage_capacity',
                        object_ids=(occupancy.occupancy_id, location_id),
                        message=f'location does not declare the {use.unit} capacity dimension',
                    ))


def check_resource_requirements(
    request: WarehouseScheduleRequest,
    result: WarehouseScheduleResult,
    outcome: CheckOutcome,
) -> None:
    requested = set(request.order_ids)
    operations = {op.operation_id: op for op in request.snapshot.operations}
    resources = {res.resource_id: res for res in request.snapshot.resources}
    scheduled = {item.operation_id: item for item in result.operations}
    requirements_present = False
    for operation_id, operation in sorted(operations.items()):
        if not operation.requirements:
            continue
        if operation.order_ids and not any(oid in requested for oid in operation.order_ids):
            # Outside this request's order scope: not part of this schedule.
            continue
        requirements_present = True
        item = scheduled.get(operation_id)
        if item is None:
            outcome.violations.append(Violation(
                rule_id='r05.resource_requirements',
                object_ids=(operation_id,),
                message='operation with resource requirements is not scheduled',
            ))
            continue
        assignments: dict[str, list] = {}
        for assignment in item.resource_assignments:
            assignments.setdefault(assignment.requirement_id, []).append(assignment)
        for requirement in operation.requirements:
            got = assignments.get(requirement.requirement_id, [])
            if len(got) != 1:
                outcome.violations.append(Violation(
                    rule_id='r05.resource_requirements',
                    object_ids=(operation_id, requirement.requirement_id),
                    message=f'requirement has {len(got)} assignments, expected exactly 1',
                ))
                continue
            assignment = got[0]
            if assignment.resource_id not in requirement.eligible_resource_ids:
                outcome.violations.append(Violation(
                    rule_id='r05.resource_requirements',
                    object_ids=(operation_id, assignment.resource_id),
                    message='assigned resource is not eligible for the requirement',
                ))
            if assignment.quantity_units != requirement.quantity_units:
                outcome.violations.append(Violation(
                    rule_id='r05.resource_requirements',
                    object_ids=(operation_id, requirement.requirement_id),
                    message='assigned quantity differs from the requirement',
                ))
            if assignment.resource_id not in resources:
                outcome.violations.append(Violation(
                    rule_id='r05.resource_requirements',
                    object_ids=(operation_id, assignment.resource_id),
                    message='assigned resource does not exist in the snapshot',
                ))
            elif not any(
                item.start_s >= window.start_s and item.end_s <= window.end_s
                for window in resources[assignment.resource_id].available_windows
            ):
                outcome.violations.append(Violation(
                    rule_id='r05.resource_requirements',
                    object_ids=(operation_id, assignment.resource_id),
                    message='assigned resource is not available for the whole requirement interval',
                ))
        for extra in sorted(set(assignments) - {r.requirement_id for r in operation.requirements}):
            outcome.violations.append(Violation(
                rule_id='r05.resource_requirements',
                object_ids=(operation_id, extra),
                message='assignment references an undeclared requirement',
            ))
        primary = assignments.get(operation.primary_requirement_id, [])
        if len(primary) != 1 or primary[0].resource_id != item.resource_id:
            outcome.violations.append(Violation(
                rule_id='r05.resource_requirements',
                object_ids=(operation_id, item.resource_id),
                message='operation resource_id is not the primary requirement assignment',
            ))
    if not requirements_present:
        outcome.not_checked.append('r05.resource_requirements:no_multi_resource_operations')


def check_resource_capacity(
    request: WarehouseScheduleRequest,
    result: WarehouseScheduleResult,
    outcome: CheckOutcome,
) -> None:
    resources = {res.resource_id: res for res in request.snapshot.resources}
    scheduled = {item.operation_id: item for item in result.operations}
    loads: dict[str, list[tuple[int, int, int]]] = {}
    for item in result.operations:
        if item.scheduled_kind != 'task':
            continue
        if item.resource_assignments:
            for assignment in item.resource_assignments:
                loads.setdefault(assignment.resource_id, []).append(
                    (item.start_s, item.end_s, assignment.quantity_units)
                )
        else:
            loads.setdefault(item.resource_id, []).append((item.start_s, item.end_s, 1))
    for resource_id, entries in sorted(loads.items()):
        resource = resources.get(resource_id)
        if resource is None:
            continue  # covered by warehouse.resource_availability
        peak, peak_start, peak_end = _peak(entries)
        if peak > resource.capacity_units:
            outcome.violations.append(Violation(
                rule_id='r05.resource_capacity',
                object_ids=(resource_id,),
                message=f'peak usage {peak} exceeds resource capacity {resource.capacity_units}',
                evidence=RuleEvidence(
                    rule_version=request.snapshot.rule_version,
                    capacity_unit='quantity_units', observed_value=peak,
                    limit_value=resource.capacity_units,
                    interval_start_s=peak_start, interval_end_s=peak_end,
                ),
            ))
    if not scheduled:
        return


def check_changeovers(
    coldchain: ColdChainSnapshot,
    request: WarehouseScheduleRequest,
    result: WarehouseScheduleResult,
    outcome: CheckOutcome,
) -> None:
    policies = {policy.policy_id: policy for policy in coldchain.setup_policies}
    resources = {res.resource_id: res for res in request.snapshot.resources}
    operations = {op.operation_id: op for op in request.snapshot.operations}
    if not policies:
        outcome.not_checked.append('r05.changeover:no_setup_policy')
        return

    by_resource: dict[str, list[ScheduledOperation]] = {}
    for item in result.operations:
        if item.scheduled_kind != 'task':
            continue
        by_resource.setdefault(item.resource_id, []).append(item)

    checked_any = False
    for resource_id, items in sorted(by_resource.items()):
        resource = resources.get(resource_id)
        if resource is None or resource.setup_policy_id is None:
            continue
        policy = policies.get(resource.setup_policy_id)
        if policy is None:
            outcome.violations.append(Violation(
                rule_id='r05.changeover',
                object_ids=(resource_id, resource.setup_policy_id),
                message='resource references a setup policy that is not declared',
            ))
            continue
        items = sorted(items, key=lambda entry: (entry.start_s, entry.end_s, entry.operation_id))
        checked_any = True
        initial = resource.initial_setup_class
        first_class = operations.get(items[0].operation_id).setup_class if items else None
        if initial is not None and first_class is not None and first_class != initial:
            duration = _setup_duration(policy, initial, first_class)
            if duration is None:
                outcome.violations.append(Violation(
                    rule_id='r05.changeover',
                    object_ids=(resource_id, items[0].operation_id),
                    message=f'no changeover rule for initial class {initial} -> {first_class}',
                ))
            elif items[0].start_s < duration:
                outcome.violations.append(Violation(
                    rule_id='r05.changeover',
                    object_ids=(resource_id, items[0].operation_id),
                    message=f'first operation starts at {items[0].start_s}s but needs {duration}s from the initial class',
                    evidence=RuleEvidence(
                        rule_version=coldchain.rule_version,
                        interval_start_s=0, interval_end_s=items[0].start_s,
                        detail=f'required {duration}s',
                    ),
                ))
        for previous, current in zip(items, items[1:]):
            previous_class = operations.get(previous.operation_id).setup_class
            current_class = operations.get(current.operation_id).setup_class
            if previous_class is None or current_class is None or previous_class == current_class:
                continue
            duration = _setup_duration(policy, previous_class, current_class)
            if duration is None:
                outcome.violations.append(Violation(
                    rule_id='r05.changeover',
                    object_ids=(previous.operation_id, current.operation_id, resource_id),
                    message=f'no changeover rule for {previous_class} -> {current_class}',
                ))
                continue
            gap = current.start_s - previous.end_s
            if gap < duration:
                outcome.violations.append(Violation(
                    rule_id='r05.changeover',
                    object_ids=(previous.operation_id, current.operation_id, resource_id),
                    message=f'changeover gap {gap}s is shorter than the required {duration}s',
                    evidence=RuleEvidence(
                        rule_version=coldchain.rule_version,
                        interval_start_s=previous.end_s, interval_end_s=current.start_s,
                        detail=f'required {duration}s',
                    ),
                ))
            if policy.rendering == 'explicit_operation':
                matching = [
                    item for item in result.operations
                    if item.scheduled_kind == 'setup'
                    and item.setup_for_operation_id == current.operation_id
                    and item.resource_id == resource_id
                ]
                if not matching:
                    outcome.violations.append(Violation(
                        rule_id='r05.changeover',
                        object_ids=(current.operation_id, resource_id),
                        message='policy requires an explicit setup operation that is missing',
                    ))
    if not checked_any:
        outcome.not_checked.append('r05.changeover:no_resource_with_policy')


def check_precool(
    coldchain: ColdChainSnapshot,
    request: WarehouseScheduleRequest,
    result: WarehouseScheduleResult,
    outcome: CheckOutcome,
) -> None:
    if not coldchain.precool_requirements:
        outcome.not_checked.append('r05.precool:no_precool_requirement')
        return
    requested = set(request.order_ids)
    operations = {op.operation_id: op for op in request.snapshot.operations}
    scheduled = {item.operation_id: item for item in result.operations}
    for requirement in coldchain.precool_requirements:
        source = operations.get(requirement.precool_operation_id)
        if source is not None and source.order_ids and not any(
                oid in requested for oid in source.order_ids):
            # Pre-cooling for an order outside this request: not part of this plan.
            continue
        precool = scheduled.get(requirement.precool_operation_id)
        if precool is None:
            outcome.violations.append(Violation(
                rule_id='r05.precool',
                object_ids=(requirement.precool_operation_id,),
                message='pre-cooling operation is not scheduled',
            ))
            continue
        if precool.resource_id not in requirement.eligible_resource_ids:
            outcome.violations.append(Violation(
                rule_id='r05.precool',
                object_ids=(precool.operation_id, precool.resource_id),
                message='pre-cooling ran on a resource that is not eligible',
            ))
        duration = precool.end_s - precool.start_s
        if duration < requirement.min_duration_s:
            outcome.violations.append(Violation(
                rule_id='r05.precool',
                object_ids=(precool.operation_id,),
                message=f'pre-cooling lasts {duration}s, minimum is {requirement.min_duration_s}s',
                evidence=RuleEvidence(
                    rule_version=coldchain.rule_version,
                    interval_start_s=precool.start_s, interval_end_s=precool.end_s,
                    detail=f'required >= {requirement.min_duration_s}s',
                ),
            ))
        for loading_id in requirement.loading_operation_ids:
            loading = scheduled.get(loading_id)
            if loading is None:
                outcome.violations.append(Violation(
                    rule_id='r05.precool',
                    object_ids=(loading_id,),
                    message='loading operation is not scheduled',
                ))
                continue
            if loading.start_s < precool.end_s:
                outcome.violations.append(Violation(
                    rule_id='r05.precool',
                    object_ids=(precool.operation_id, loading_id),
                    message='loading starts before pre-cooling finishes',
                    evidence=RuleEvidence(
                        rule_version=coldchain.rule_version,
                        interval_start_s=min(precool.end_s, loading.start_s),
                        interval_end_s=max(precool.end_s, loading.start_s),
                    ),
                ))


def check_exposure(
    coldchain: ColdChainSnapshot,
    request: WarehouseScheduleRequest,
    result: WarehouseScheduleResult,
    outcome: CheckOutcome,
) -> None:
    if not coldchain.exposure_limits:
        outcome.not_checked.append('r05.exposure:no_exposure_limit')
        return
    if result.coldchain is None:
        outcome.not_checked.append('r05.exposure:no_plan')
        return
    segments_by_batch: dict[str, list] = {}
    for segment in result.coldchain.exposure_segments:
        segments_by_batch.setdefault(segment.batch_id, []).append(segment)

    requested = set(request.order_ids)
    in_scope_batches = {order.batch_id for order in request.snapshot.orders
                        if order.order_id in requested}
    for limit in coldchain.exposure_limits:
        if in_scope_batches and limit.batch_id not in in_scope_batches:
            # The batch is not part of this request, so it has no plan evidence.
            continue
        segments = segments_by_batch.get(limit.batch_id, [])
        covered = {segment.scope for segment in segments}
        missing = [scope for scope in limit.scopes if scope not in covered]
        for scope in missing:
            outcome.not_checked.append(f'r05.exposure:{limit.limit_id}:{scope}')
        counted = [segment for segment in segments if segment.scope in limit.scopes]
        if not counted:
            continue
        intervals = _merge([(segment.start_s, segment.end_s) for segment in counted])
        total = sum(end - start for start, end in intervals)
        if total > limit.max_exposure_s:
            outcome.violations.append(Violation(
                rule_id='r05.exposure',
                object_ids=(limit.limit_id, limit.batch_id),
                message=f'cumulative exposure {total}s exceeds the limit {limit.max_exposure_s}s',
                evidence=RuleEvidence(
                    rule_version=coldchain.rule_version, capacity_unit='duration_s',
                    observed_value=total, limit_value=limit.max_exposure_s,
                    interval_start_s=intervals[0][0],
                    interval_end_s=max(end for _, end in intervals),
                    detail='union of exposure segments, overlaps counted once',
                ),
            ))


def check_batch_compatibility(
    coldchain: ColdChainSnapshot,
    result: WarehouseScheduleResult,
    outcome: CheckOutcome,
) -> None:
    if result.coldchain is None:
        outcome.not_checked.append('r05.batch_compatibility:no_plan')
        return
    zones = {zone.zone_id: zone for zone in coldchain.zones}
    locations = {item.location_id: item for item in coldchain.storage_locations}
    profiles = {profile.batch_id: profile for profile in coldchain.batch_compatibility}
    if not profiles:
        outcome.not_checked.append('r05.batch_compatibility:no_batch_profile')
        return

    for occupancy in result.coldchain.occupancies:
        profile = profiles.get(occupancy.batch_id)
        if profile is None:
            outcome.not_checked.append(f'r05.batch_compatibility:{occupancy.batch_id}')
            continue
        location = locations.get(occupancy.location_id)
        if location is None:
            continue
        zone = zones.get(location.zone_id)
        if zone is None:
            outcome.not_checked.append(f'r05.batch_compatibility:{location.location_id}:zone')
            continue
        if zone.temperature_zone != profile.temperature_zone:
            outcome.violations.append(Violation(
                rule_id='r05.batch_compatibility',
                object_ids=(occupancy.occupancy_id, zone.zone_id),
                message=f'batch zone {profile.temperature_zone} does not match location zone {zone.temperature_zone}',
            ))
        if not (profile.min_temperature_decic <= zone.setpoint_decic <= profile.max_temperature_decic):
            outcome.violations.append(Violation(
                rule_id='r05.batch_compatibility',
                object_ids=(occupancy.occupancy_id, zone.zone_id),
                message='location set point is outside the batch temperature range',
                evidence=RuleEvidence(
                    rule_version=coldchain.rule_version, capacity_unit='decic',
                    observed_value=zone.setpoint_decic,
                    limit_value=profile.max_temperature_decic,
                    detail=f'allowed [{profile.min_temperature_decic}, {profile.max_temperature_decic}] decic',
                ),
            ))

    policy = coldchain.compatibility_policy
    if policy is None:
        outcome.not_checked.append('r05.batch_compatibility:no_compatibility_policy')
        return
    occupancies = list(result.coldchain.occupancies)
    for index, left in enumerate(occupancies):
        for right in occupancies[index + 1:]:
            if left.location_id != right.location_id or left.batch_id == right.batch_id:
                continue
            left_profile = profiles.get(left.batch_id)
            right_profile = profiles.get(right.batch_id)
            if left_profile is None or right_profile is None:
                continue
            if left_profile.compatibility_class is None or right_profile.compatibility_class is None:
                outcome.not_checked.append(f'r05.batch_compatibility:mixing:{left.location_id}')
                continue
            if not policy.forbidden(left_profile.compatibility_class,
                                    right_profile.compatibility_class):
                continue
            if left.start_s < right.end_s and right.start_s < left.end_s:
                outcome.violations.append(Violation(
                    rule_id='r05.batch_compatibility',
                    object_ids=(left.occupancy_id, right.occupancy_id, left.location_id),
                    message='incompatible batches overlap in the same storage location',
                    evidence=RuleEvidence(
                        rule_version=coldchain.rule_version,
                        interval_start_s=max(left.start_s, right.start_s),
                        interval_end_s=min(left.end_s, right.end_s),
                    ),
                ))


def check_coldchain(request: WarehouseScheduleRequest,
                    result: WarehouseScheduleResult) -> CheckOutcome | None:
    """Run every R05 rule; ``None`` when the scenario declares no R05 data."""
    coldchain = request.snapshot.coldchain
    if coldchain is None:
        return None
    outcome = CheckOutcome()
    check_occupancy_declaration(coldchain, request, result, outcome)
    check_storage_capacity(coldchain, result, outcome)
    check_resource_requirements(request, result, outcome)
    check_resource_capacity(request, result, outcome)
    check_changeovers(coldchain, request, result, outcome)
    check_precool(coldchain, request, result, outcome)
    check_exposure(coldchain, request, result, outcome)
    check_batch_compatibility(coldchain, result, outcome)
    return outcome


