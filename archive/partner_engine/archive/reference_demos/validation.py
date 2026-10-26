"""Checks plain results without importing either solver or simulation library."""
from collections import Counter


def warehouse_errors(tasks, plan, downtime=(), frozen=(), now=0):
    errors = []
    rows = plan.get('tasks', [])
    if plan.get('status') not in ('OPTIMAL', 'FEASIBLE'):
        return ['no_feasible_plan']
    if Counter(r['id'] for r in rows) != Counter(t['id'] for t in tasks):
        return ['task_coverage']
    by_id = {r['id']: r for r in rows}
    fixed = {r['id']: r for r in frozen}
    for task in tasks:
        row = by_id[task['id']]
        if row['resource'] != task['resource']:
            errors.append('resource:' + task['id'])
        if row['end'] - row['start'] != task['duration']:
            errors.append('duration:' + task['id'])
        if row['start'] < task['release'] or row['end'] > task['deadline']:
            errors.append('window:' + task['id'])
        if task['id'] in fixed:
            if row != fixed[task['id']]:
                errors.append('frozen:' + task['id'])
        elif row['start'] < now:
            errors.append('past:' + task['id'])
        for predecessor in task['after']:
            if row['start'] < by_id[predecessor]['end']:
                errors.append('precedence:' + task['id'])
    for i, left in enumerate(rows):
        for right in rows[i + 1:] + list(downtime):
            if left['resource'] == right['resource'] and max(left['start'], right['start']) < min(left['end'], right['end']):
                errors.append('overlap:' + left['id'])
    return errors


def transport_errors(data, plan):
    if plan.get('status') != 'FEASIBLE':
        return ['no_feasible_plan']
    errors, served = [], []
    routes = plan['routes']
    if Counter(r['vehicle'] for r in routes) != Counter(range(len(data['vehicles']))):
        return ['vehicle_coverage']
    for route in routes:
        vehicle = data['vehicles'][route['vehicle']]
        stops = route['stops']
        if not stops or stops[0]['node'] != 0 or stops[-1]['node'] != 0:
            errors.append('depot')
            continue
        nodes = [s['node'] for s in stops[1:-1]]
        served.extend(nodes)
        if any(n <= 0 or n >= len(data['matrix']) for n in nodes):
            errors.append('unknown_node')
            continue
        if sum(data['demands'][n] for n in nodes) > vehicle['capacity']:
            errors.append('capacity')
        if any(data['temperatures'][n] != vehicle['temperature'] for n in nodes):
            errors.append('temperature')
        for stop in stops:
            lo, hi = data['windows'][stop['node']]
            if not lo <= stop['time'] <= hi:
                errors.append('window')
        for prev, curr in zip(stops, stops[1:]):
            needed = data['matrix'][prev['node']][curr['node']] + data['service'][prev['node']]
            if curr['time'] < prev['time'] + needed:
                errors.append('travel_time')
    if Counter(served) != Counter(range(1, len(data['matrix']))):
        errors.append('order_coverage')
    return errors
