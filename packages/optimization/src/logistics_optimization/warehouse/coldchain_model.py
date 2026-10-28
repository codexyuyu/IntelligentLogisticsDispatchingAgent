"""CP-SAT constraints. Independent validation never calls this module."""
from collections import defaultdict
from itertools import pairwise

from logistics_domain.coldchain import ExposureScope


def phased_capacity(model, intervals, demands, horizon, boundaries, capacity_at, name):
    """Convert a piecewise capacity into cumulative fixed blocking intervals."""
    points = sorted({0, horizon} | {p for p in boundaries if 0 < p < horizon})
    segments = [(a, b, capacity_at(a)) for a, b in pairwise(points)]
    ceiling = max((c for _, _, c in segments), default=0)
    blocked, amounts = list(intervals), list(demands)
    for index, (a, b, capacity) in enumerate(segments):
        if capacity < ceiling:
            blocked.append(model.NewIntervalVar(a, b-a, b, f'{name}_closed_{index}'))
            amounts.append(ceiling-capacity)
    model.AddCumulative(blocked, amounts, ceiling)


def union_duration(model, spans, horizon, name):
    """Exact interval-union measure, including nested and coincident intervals."""
    contributions = []
    for i, (start, end) in enumerate(spans):
        earlier_ends = [start]
        for j, (other_start, other_end) in enumerate(spans):
            if i == j:
                continue
            before = model.NewBoolVar(f'{name}_{j}_before_{i}')
            # Stable tie break ensures coincident spans are counted once.
            model.Add(other_start <= start - (j > i)).OnlyEnforceIf(before)
            model.Add(other_start > start - (j > i)).OnlyEnforceIf(before.Not())
            value = model.NewIntVar(0, horizon, f'{name}_previous_{i}_{j}')
            model.Add(value == other_end).OnlyEnforceIf(before)
            model.Add(value == 0).OnlyEnforceIf(before.Not())
            earlier_ends.append(value)
        covered = model.NewIntVar(0, horizon, f'{name}_covered_{i}')
        model.AddMaxEquality(covered, earlier_ends)
        amount = model.NewIntVar(0, horizon, f'{name}_contribution_{i}')
        model.AddMaxEquality(amount, [0, end-covered])
        contributions.append(amount)
    return sum(contributions)


def add_coldchain(model, problem, starts, ends, use):
    cold = problem.snapshot.coldchain
    if cold is None:
        return {}
    horizon = problem.snapshot.scope.horizon_s
    if cold.horizon_s != horizon:
        raise ValueError('coldchain horizon differs from planning scope')
    locations = {x.location_id: x for x in cold.storage_locations}
    zones = {x.zone_id: x for x in cold.zones}
    batches = {x.batch_id: x for x in cold.batch_compatibility}
    spans, by_location, by_zone = {}, defaultdict(list), defaultdict(list)
    exposure = defaultdict(list)
    reuse = {rule.location_id: rule for rule in cold.reuse_rules}
    for item in cold.occupancies:
        if item.location_id not in locations:
            raise ValueError('unknown coldchain storage location')
        location = locations[item.location_id]
        if location.zone_id not in zones:
            raise ValueError('unknown coldchain zone')
        zone = zones[location.zone_id]
        if location.warehouse_id != zone.warehouse_id:
            raise ValueError('storage/zone warehouse mismatch')
        batch = batches.get(item.batch_id)
        if batch is None:
            raise ValueError('batch compatibility evidence missing')
        if batch.warehouse_id != location.warehouse_id or not (
                batch.min_temperature_decic <= zone.setpoint_decic <= batch.max_temperature_decic):
            model.Add(False)
        try:
            start = ends[item.inbound_operation_id] if item.inbound_operation_id else (item.declared_start_s or 0)
            if item.outbound_operation_id:
                end = starts[item.outbound_operation_id]
            else:
                end = horizon
                rule = reuse.get(item.location_id)
                if rule is not None:
                    capped = model.NewIntVar(0, horizon, f'storage_reuse_end_{item.occupancy_id}')
                    model.AddMinEquality(capped, [horizon, start + rule.max_batch_age_s])
                    end = capped
        except KeyError as exc:
            raise ValueError('occupancy operation outside problem') from exc
        size = model.NewIntVar(0, horizon, f'storage_duration_{item.occupancy_id}')
        model.Add(size == end-start)
        interval = model.NewIntervalVar(start, size, end, f'storage_{item.occupancy_id}')
        spans[item.occupancy_id] = (start, end)
        by_location[item.location_id].append((item, interval))
        by_zone[zone.zone_id].append((item, interval))
        exposure[(item.batch_id, ExposureScope.IN_WAREHOUSE)].append((start, end))
    for location_id, entries in by_location.items():
        location = locations[location_id]
        bounds = [p for x in location.capacity_periods for p in (x.start_s, x.end_s)]
        bounds += [p for x in location.available_windows for p in (x.earliest_s, x.latest_s)]
        units = {u.unit for item, _ in entries for u in item.capacity_use}
        for unit in units:
            def capacity_at(t, unit=unit, location=location):
                if location.available_windows and not any(w.earliest_s <= t < w.latest_s for w in location.available_windows):
                    return 0
                capacities = location.capacities
                if location.capacity_periods:
                    period = next((p for p in location.capacity_periods if p.start_s <= t < p.end_s), None)
                    capacities = period.capacities if period else ()
                return next((u.amount for u in capacities if u.unit == unit), 0)
            phased_capacity(model, [iv for _, iv in entries],
                            [sum(u.amount for u in item.capacity_use if u.unit == unit) for item, _ in entries],
                            horizon, bounds, capacity_at, f'{location_id}_{unit}')
    for zone_id, entries in by_zone.items():
        zone = zones[zone_id]
        for unit in {u.unit for item, _ in entries for u in item.capacity_use}:
            cap = next((u.amount for u in zone.capacities if u.unit == unit), 0)
            model.AddCumulative([iv for _, iv in entries],
                [sum(u.amount for u in item.capacity_use if u.unit == unit) for item, _ in entries], cap)
        if cold.compatibility_policy:
            banned = {frozenset(pair) for pair in cold.compatibility_policy.incompatible_class_pairs}
            for i, (left, _) in enumerate(entries):
                for right, _ in entries[i+1:]:
                    if frozenset((batches[left.batch_id].compatibility_class,
                                  batches[right.batch_id].compatibility_class)) not in banned:
                        continue
                    a, b = spans[left.occupancy_id], spans[right.occupancy_id]
                    order = model.NewBoolVar(f'compatible_{left.occupancy_id}_{right.occupancy_id}')
                    model.Add(a[1] <= b[0]).OnlyEnforceIf(order)
                    model.Add(b[1] <= a[0]).OnlyEnforceIf(order.Not())
    task_by_id = {t.id: t for t in problem.tasks}
    for req in cold.precool_requirements:
        if req.precool_operation_id not in starts or any(t not in starts for t in req.loading_operation_ids):
            raise ValueError('precool or loading operation outside problem')
        task = task_by_id[req.precool_operation_id]
        model.Add(task.duration_s >= req.min_duration_s)
        eligible_flags = [flag for (tid, _, resource), flag in use.items()
                          if tid == task.id and resource in req.eligible_resource_ids]
        model.Add(sum(eligible_flags) >= 1)
        for loading in req.loading_operation_ids:
            model.Add(starts[loading] >= ends[task.id])
            exposure[(req.batch_id, ExposureScope.WAITING)].append((ends[task.id], starts[loading]))
            exposure[(req.batch_id, ExposureScope.LOADING)].append((starts[loading], ends[loading]))
    for limit in cold.exposure_limits:
        intervals = [span for scope in limit.scopes for span in exposure[(limit.batch_id, scope)]]
        if intervals:
            model.Add(union_duration(model, intervals, horizon, f'exposure_{limit.limit_id}') <= limit.max_exposure_s)
    # Export the exact modeled endpoints; callers may read them only after a feasible solve.
    return spans
