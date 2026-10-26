"""Small dock scheduling probe. Minutes are relative to a synthetic day start."""
from ortools.sat.python import cp_model


def scenario():
    return [
        dict(id="unload-A", resource="dock", duration=4, release=0, deadline=30, after=[]),
        dict(id="sort-A", resource="sorter", duration=3, release=0, deadline=30, after=["unload-A"]),
        dict(id="load-A", resource="dock", duration=4, release=0, deadline=30, after=["sort-A"]),
        dict(id="unload-B", resource="dock", duration=3, release=12, deadline=30, after=[]),
    ]


def solve(tasks, downtime=(), frozen=(), now=0):
    if not tasks or len({t['id'] for t in tasks}) != len(tasks):
        raise ValueError("Tasks must be nonempty with unique IDs")
    model = cp_model.CpModel()
    variables, resources = {}, {}
    fixed = {x['id']: x for x in frozen}
    horizon = max(t['deadline'] for t in tasks)
    for task in tasks:
        key = task['id']
        start = model.new_int_var(0, horizon, key + ':start')
        end = model.new_int_var(0, horizon, key + ':end')
        interval = model.new_interval_var(start, task['duration'], end, key)
        model.add(start >= task['release'])
        model.add(end <= task['deadline'])
        if key in fixed:
            model.add(start == fixed[key]['start'])
            model.add(end == fixed[key]['end'])
        else:
            model.add(start >= now)
        variables[key] = (start, end)
        resources.setdefault(task['resource'], []).append(interval)
    for task in tasks:
        for predecessor in task['after']:
            model.add(variables[task['id']][0] >= variables[predecessor][1])
    for index, outage in enumerate(downtime):
        interval = model.new_fixed_size_interval_var(outage['start'], outage['end'] - outage['start'], f'outage:{index}')
        resources.setdefault(outage['resource'], []).append(interval)
    for intervals in resources.values():
        model.add_no_overlap(intervals)
    # This probe minimizes completion times, not the full project's economic cost.
    model.minimize(sum(end for _, end in variables.values()))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 2
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 17
    status = solver.solve(model)
    result = dict(status=solver.status_name(status), tasks=[])
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        result['tasks'] = [dict(id=t['id'], resource=t['resource'], start=solver.value(variables[t['id']][0]), end=solver.value(variables[t['id']][1])) for t in tasks]
    return result
