"""A known-duration dock outage at a job boundary; no running task is interrupted."""
from copy import deepcopy
import simpy
from warehouse import scenario, solve
from validation import warehouse_errors


def run():
    tasks = scenario()
    before = solve(tasks)
    if warehouse_errors(tasks, before):
        raise RuntimeError('Baseline failed independent validation')
    env, events = simpy.Environment(), []
    result = dict(before=before, events=events)

    def fault():
        yield env.timeout(4)
        # At time 4 the completed unloading is retained; work starting at 4 is pending.
        frozen = [deepcopy(t) for t in before['tasks'] if t['end'] <= env.now]
        downtime = [dict(resource='dock', start=env.now, end=10)]
        events.append(dict(time=env.now, type='dock_unavailable', until=10))
        after = solve(tasks, downtime=downtime, frozen=frozen, now=env.now)
        errors = warehouse_errors(tasks, after, downtime, frozen, env.now)
        forged = deepcopy(after)
        for row in forged['tasks']:
            if row['id'] == 'load-A':
                row.update(start=5, end=9)
        result.update(after=after, frozen=frozen, downtime=downtime, validation_errors=errors,
                      rejected_candidate_errors=warehouse_errors(tasks, forged, downtime, frozen, env.now),
                      evidence=dict(source='synthetic:outage-001', time_unit='minute', repair_duration_known=True))

    env.process(fault())
    env.run()
    return result
