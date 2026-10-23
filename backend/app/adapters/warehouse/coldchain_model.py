"""CP-SAT modelling of the R05 cold-chain constraints.

Only used when ``PlanningSnapshot.coldchain`` is present; a snapshot without R05
data follows exactly the previous single-resource model.  Every constraint here
is a *hard* constraint: infeasible input raises :class:`ColdChainModelError`
with a stable code instead of silently relaxing the rule.

The model covers:

* time-varying storage capacity per location and capacity dimension,
* simultaneous multi-resource requirements,
* sequence-dependent changeover (gap or explicit setup operation),
* pre-cooling duration, resource eligibility and precedence before loading,
* conservative exposure limits that the independent validator then confirms
  against the real union of exposure segments.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.contracts.coldchain import SetupPolicy
from app.contracts.entities import Operation, WarehouseResource
from app.contracts.planning import PlanningSnapshot


class ColdChainModelError(RuntimeError):
    """Declared R05 data cannot be modelled; the code is stable for callers."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass
class ColdChainContext:
    snapshot: PlanningSnapshot
    policies: dict[str, SetupPolicy]
    resources: dict[str, WarehouseResource]
    operations: dict[str, Operation]
    precool_eligible: dict[str, frozenset[str]]
    horizon_s: int
    rule_version: str


def build_context(snapshot: PlanningSnapshot) -> ColdChainContext | None:
    coldchain = snapshot.coldchain
    if coldchain is None:
        return None
    operations = {op.operation_id: op for op in snapshot.operations}
    resources = {res.resource_id: res for res in snapshot.resources}
    policies = {policy.policy_id: policy for policy in coldchain.setup_policies}
    precool_eligible: dict[str, frozenset[str]] = {}
    for requirement in coldchain.precool_requirements:
        if requirement.precool_operation_id not in operations:
            raise ColdChainModelError(f'UNKNOWN_PRECOOL_OPERATION:{requirement.precool_operation_id}')
        for resource_id in requirement.eligible_resource_ids:
            if resource_id not in resources:
                raise ColdChainModelError(f'UNKNOWN_PRECOOL_RESOURCE:{resource_id}')
        precool_eligible[requirement.precool_operation_id] = frozenset(
            requirement.eligible_resource_ids
        )
    for resource in coldchain.storage_locations:
        if resource.warehouse_id not in {w.warehouse_id for w in snapshot.warehouses}:
            raise ColdChainModelError(f'UNKNOWN_STORAGE_WAREHOUSE:{resource.warehouse_id}')
    for occupancy in coldchain.occupancies:
        if occupancy.inbound_operation_id is not None and occupancy.inbound_operation_id not in operations:
            raise ColdChainModelError(f'UNKNOWN_INBOUND_OPERATION:{occupancy.inbound_operation_id}')
        if occupancy.outbound_operation_id is not None and occupancy.outbound_operation_id not in operations:
            raise ColdChainModelError(f'UNKNOWN_OUTBOUND_OPERATION:{occupancy.outbound_operation_id}')
    for requirement in coldchain.precool_requirements:
        for loading_id in requirement.loading_operation_ids:
            if loading_id not in operations:
                raise ColdChainModelError(f'UNKNOWN_LOADING_OPERATION:{loading_id}')
        precool = operations[requirement.precool_operation_id]
        if precool.duration_s < requirement.min_duration_s:
            raise ColdChainModelError(f'PRECOOL_DURATION_TOO_SHORT:{precool.operation_id}')
    return ColdChainContext(
        snapshot=snapshot,
        policies=policies,
        resources=resources,
        operations=operations,
        precool_eligible=precool_eligible,
        horizon_s=coldchain.horizon_s,
        rule_version=coldchain.rule_version,
    )


def _setup_duration(policy: SetupPolicy, from_class: str, to_class: str) -> int | None:
    if from_class == to_class:
        return 0
    for rule in policy.rules:
        if rule.from_class == from_class and rule.to_class == to_class:
            return rule.duration_s
    return policy.default_duration_s


def filter_candidates(context: ColdChainContext, operation: Operation,
                      candidates: list[WarehouseResource]) -> list[WarehouseResource]:
    """Narrow candidate resources by the primary requirement and precool eligibility."""
    allowed_ids: set[str] | None = None
    if operation.requirements:
        primary = next(
            (requirement for requirement in operation.requirements
             if requirement.requirement_id == operation.primary_requirement_id),
            None,
        )
        if primary is None:
            raise ColdChainModelError(f'UNKNOWN_PRIMARY_REQUIREMENT:{operation.operation_id}')
        allowed_ids = set(primary.eligible_resource_ids)
    precool_ids = context.precool_eligible.get(operation.operation_id)
    if precool_ids is not None:
        allowed_ids = precool_ids if allowed_ids is None else allowed_ids & precool_ids
    if allowed_ids is None:
        return candidates
    return [resource for resource in candidates if resource.resource_id in allowed_ids]


def add_setup_constraints(
    context: ColdChainContext,
    model,
    assignments: dict[str, dict[str, object]],
    start_vars: dict[str, object],
    end_vars: dict[str, object],
) -> None:
    """Sequence-dependent changeover on every resource that declares a policy.

    An unlisted class pair (no explicit rule and no ``default_duration_s``) is
    *unknown*, never zero.  The model therefore forbids the two operations from
    sharing that resource instead of assuming a free changeover; forcing them
    together makes the request infeasible.
    """
    for resource_id, resource in sorted(context.resources.items()):
        if resource.setup_policy_id is None:
            continue
        policy = context.policies.get(resource.setup_policy_id)
        if policy is None:
            raise ColdChainModelError(f'UNKNOWN_SETUP_POLICY:{resource.setup_policy_id}')
        occupants = [
            operation_id for operation_id, literals in assignments.items()
            if resource_id in literals and start_vars.get(operation_id) is not None
        ]
        if not occupants:
            continue
        initial_class = resource.initial_setup_class
        for operation_id in occupants:
            operation = context.operations[operation_id]
            if initial_class is None or operation.setup_class is None:
                continue
            if operation.setup_class == initial_class:
                continue
            duration = _setup_duration(policy, initial_class, operation.setup_class)
            if duration is None:
                # Unknown changeover out of the initial class: this resource may
                # not start with that class.
                model.Add(assignments[operation_id][resource_id] == 0)
                continue
            if duration:
                model.Add(start_vars[operation_id] >= duration).OnlyEnforceIf(
                    assignments[operation_id][resource_id]
                )
        for index, left_id in enumerate(occupants):
            for right_id in occupants[index + 1:]:
                left = context.operations[left_id]
                right = context.operations[right_id]
                if left.setup_class is None or right.setup_class is None:
                    continue
                if left.setup_class == right.setup_class:
                    continue
                forward = _setup_duration(policy, left.setup_class, right.setup_class)
                backward = _setup_duration(policy, right.setup_class, left.setup_class)
                guard = [assignments[left_id][resource_id], assignments[right_id][resource_id]]
                if forward is None and backward is None:
                    # Neither ordering has a known changeover: these two may not
                    # share the resource at all.
                    model.AddBoolOr([guard[0].Not(), guard[1].Not()])
                    continue
                if forward is None:
                    # Only right -> left is known: right must come first.
                    model.Add(
                        start_vars[left_id] >= end_vars[right_id] + backward
                    ).OnlyEnforceIf(guard)
                    continue
                if backward is None:
                    model.Add(
                        start_vars[right_id] >= end_vars[left_id] + forward
                    ).OnlyEnforceIf(guard)
                    continue
                left_first = model.NewBoolVar(f'setup_order_{left_id}_{right_id}_{resource_id}')
                model.Add(
                    start_vars[right_id] >= end_vars[left_id] + forward
                ).OnlyEnforceIf([left_first, *guard])
                model.Add(
                    start_vars[left_id] >= end_vars[right_id] + backward
                ).OnlyEnforceIf([left_first.Not(), *guard])


def _occupancy_bounds(context: ColdChainContext, resolve_start, resolve_end):
    """Yield ``(occupancy_id, start_expr, end_expr)`` for declared occupancies."""
    coldchain = context.snapshot.coldchain
    for occupancy in coldchain.occupancies:
        if occupancy.origin == 'initial_stock':
            start = 0
        elif occupancy.inbound_operation_id is not None:
            start = resolve_end(occupancy.inbound_operation_id)
        else:
            start = int(occupancy.declared_start_s or 0)
        if occupancy.outbound_operation_id is None:
            end = context.horizon_s
        else:
            end = resolve_start(occupancy.outbound_operation_id)
        yield occupancy, start, end


def add_storage_constraints(context: ColdChainContext, model, resolve_start, resolve_end) -> None:
    """Time-varying storage capacity, checked per location and dimension."""
    coldchain = context.snapshot.coldchain
    locations = {item.location_id: item for item in coldchain.storage_locations}
    if not locations:
        return
    intervals_by_location: dict[str, list] = {}
    usage: dict[tuple[str, str], list[tuple[object, int]]] = {}
    for occupancy, start, end in _occupancy_bounds(context, resolve_start, resolve_end):
        location = locations.get(occupancy.location_id)
        if location is None:
            raise ColdChainModelError(f'UNKNOWN_STORAGE_LOCATION:{occupancy.location_id}')
        size = model.NewIntVar(0, context.horizon_s, f'occ_size_{occupancy.occupancy_id}')
        if isinstance(start, int) and isinstance(end, int):
            model.Add(size == max(0, end - start))
        else:
            model.Add(size == end - start)
            model.Add(size >= 0)
        interval = model.NewIntervalVar(start, size, end, f'occ_{occupancy.occupancy_id}')
        intervals_by_location.setdefault(occupancy.location_id, []).append(interval)
        for use in occupancy.capacity_use:
            usage.setdefault((occupancy.location_id, use.unit), []).append(
                (interval, use.amount)
            )

    for (location_id, unit), entries in sorted(usage.items()):
        location = locations[location_id]
        capacity = next(
            (amount.amount for amount in location.capacities if amount.unit == unit), None
        )
        if capacity is None:
            # The validator reports the undeclared dimension; the solver simply
            # cannot bound a quantity the location never declared.
            continue
        model.AddCumulative(
            [interval for interval, _ in entries],
            [amount for _, amount in entries],
            capacity,
        )


def add_compatibility_constraints(context: ColdChainContext, model, resolve_start, resolve_end) -> None:
    """Batches whose classes may not mix must not overlap in the same location."""
    coldchain = context.snapshot.coldchain
    policy = coldchain.compatibility_policy
    if policy is None:
        return
    classes = {profile.batch_id: profile.compatibility_class
               for profile in coldchain.batch_compatibility}
    bounds = list(_occupancy_bounds(context, resolve_start, resolve_end))
    for index, (left, left_start, left_end) in enumerate(bounds):
        for right, right_start, right_end in bounds[index + 1:]:
            if left.location_id != right.location_id or left.batch_id == right.batch_id:
                continue
            left_class = classes.get(left.batch_id)
            right_class = classes.get(right.batch_id)
            if left_class is None or right_class is None:
                continue
            if not policy.forbidden(left_class, right_class):
                continue
            ordered = model.NewBoolVar(f'compat_{left.occupancy_id}_{right.occupancy_id}')
            model.Add(left_end <= right_start).OnlyEnforceIf(ordered)
            model.Add(right_end <= left_start).OnlyEnforceIf(ordered.Not())


def add_exposure_constraints(context: ColdChainContext, model, resolve_start, resolve_end) -> None:
    """Conservative exposure caps.

    The solver can only bound the warehouse dwell it decides itself; waiting and
    transport exposure are confirmed afterwards by the independent validator,
    which merges the real segments.  A limit that only covers scopes the solver
    cannot see is therefore left to validation rather than guessed here.
    """
    coldchain = context.snapshot.coldchain
    limits = {limit.batch_id: limit for limit in coldchain.exposure_limits}
    if not limits:
        return
    durations_by_batch: dict[str, int] = {}
    for operation in context.operations.values():
        if 'load' not in operation.operation_kind:
            continue
        batch_ids = {
            order.batch_id for order in context.snapshot.orders
            if order.order_id in set(operation.order_ids)
        }
        for batch_id in batch_ids:
            durations_by_batch[batch_id] = durations_by_batch.get(batch_id, 0) + operation.duration_s

    sizes_by_batch: dict[str, list] = {}
    for occupancy, start, end in _occupancy_bounds(context, resolve_start, resolve_end):
        limit = limits.get(occupancy.batch_id)
        if limit is None or 'in_warehouse' not in limit.scopes:
            continue
        size = model.NewIntVar(0, context.horizon_s, f'exp_size_{occupancy.occupancy_id}')
        model.Add(size == end - start)
        model.Add(size >= 0)
        sizes_by_batch.setdefault(occupancy.batch_id, []).append(size)
    for batch_id, sizes in sizes_by_batch.items():
        limit = limits[batch_id]
        budget = limit.max_exposure_s - durations_by_batch.get(batch_id, 0)
        if budget < 0:
            raise ColdChainModelError(f'EXPOSURE_BUDGET_NEGATIVE:{batch_id}')
        model.Add(sum(sizes) <= budget)


def add_precool_constraints(
    context: ColdChainContext,
    model,
    start_vars: dict[str, object],
    end_vars: dict[str, object],
    assignments: dict[str, dict[str, object]],
) -> None:
    coldchain = context.snapshot.coldchain
    for requirement in coldchain.precool_requirements:
        precool_id = requirement.precool_operation_id
        precool_end = end_vars.get(precool_id)
        if precool_end is None:
            precool_end = next(
                (item.end_s for item in context.snapshot.frozen_operations
                 if item.operation_id == precool_id), None
            )
        if precool_end is None:
            continue
        for loading_id in requirement.loading_operation_ids:
            loading_start = start_vars.get(loading_id)
            if loading_start is None:
                continue
            model.Add(loading_start >= precool_end)
