"""Real-solver probe for the B-05 event stream (not a unit test).

Run from the backend directory:
    python -m tools.b05_event_stream_probe [--budget-ms 20000]

Replays one deterministic simulation containing all three B-04 event types in time
order, twice, and reports what each run emitted plus whether the two runs agree.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from app.adapters.simulation.simpy_simulator import SimPySimulator
from app.contracts.common import Source
from app.application.runtime import runtime
from app.contracts.events import DispatchEvent, EventPayload, SimulationRequest
from tools.r17_joint_ablation import load_snapshot

SNAPSHOT_FILE = Path('../data/scenarios/two_warehouses_20_orders.json')
HORIZON_S = 7200


def source(ref: str) -> Source:
    return Source(source_kind='simulation', source_ref=ref,
                  observed_at=datetime.now(timezone.utc), rule_version='r20-1.0')


def build_stream(snapshot) -> tuple[DispatchEvent, ...]:
    common = {'snapshot_id': snapshot.snapshot_id, 'expected_snapshot_version': snapshot.version,
              'received_at': datetime.now(timezone.utc)}
    return (
        DispatchEvent(event_id='evt_s1_delay', event_type='departure_delayed', object_id='veh_1',
                      occurred_at_s=0, source=source('stream:delay'),
                      payload=EventPayload(delay_s=900), **common),
        DispatchEvent(event_id='evt_s2_dock', event_type='dock_unavailable', object_id='wh_1',
                      occurred_at_s=1200, source=source('stream:dock'),
                      payload=EventPayload(unavailable_until_s=3600), **common),
        DispatchEvent(event_id='evt_s3_quarantine', event_type='cargo_quarantined',
                      object_id='bat_001', occurred_at_s=3600, source=source('stream:quarantine'),
                      payload=EventPayload(affected_order_ids=('ord_001', 'ord_002')), **common),
    )


def departures(plan) -> list:
    rows = []
    for route in plan.routing.routes:
        stops = [s for s in route.stops if s.stop_kind == 'delivery']
        if stops:
            rows.append((route.vehicle_id, route.stops[0].departure_at_s,
                         tuple(o for s in stops for o in s.order_ids)))
    return sorted(rows)


def run_once(snapshot, budget_ms: int) -> dict:
    simulator = SimPySimulator()
    simulator.BASELINE_BUDGET_MS = budget_ms
    simulator.REPLAN_BUDGET_MS = budget_ms
    request = SimulationRequest(snapshot=snapshot, events=build_stream(snapshot),
                                horizon_s=HORIZON_S, random_seed=17)
    result = simulator.simulate(request)
    normalized = result.final_snapshot.model_dump(mode='json')
    normalized.pop('snapshot_id', None)
    normalized.pop('simulation_time_s', None)
    # The HTTP layer finds the final plan the same way: newest plan of the final snapshot.
    final_plans = [p for p in runtime.plans.values()
                   if p.snapshot_id == result.final_snapshot.snapshot_id]
    final_plan = max(final_plans, key=lambda p: (p.snapshot_version, p.version)) if final_plans else None
    return {
        'emitted': [(e.event_id, e.event_type, e.occurred_at_s) for e in result.emitted_events],
        'final_version': result.final_snapshot.version,
        'digest': hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest(),
        'final_plan': final_plan,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='Replay the B-05 event stream with the real solver')
    parser.add_argument('--scenario', type=Path, default=SNAPSHOT_FILE)
    parser.add_argument('--budget-ms', type=int, default=20000)
    args = parser.parse_args(argv)
    snapshot, fingerprint = load_snapshot(args.scenario)
    print('scenario sha256', fingerprint[:16], 'horizon', HORIZON_S, 'budget', args.budget_ms)

    runs = [run_once(snapshot, args.budget_ms) for _ in range(2)]
    for index, run in enumerate(runs, start=1):
        print(f'--- run {index}: final version {run["final_version"]} digest {run["digest"][:16]}')
        for event_id, event_type, at_s in run['emitted']:
            print(f'    {at_s:>6}s  {event_type:<18} {event_id}')
    plan = runs[0]['final_plan']
    if plan is not None:
        served = {oid for route in plan.routing.routes for stop in route.stops
                  if stop.stop_kind == 'delivery' for oid in stop.order_ids}
        unserved = {u.order_id: u.reason_code for u in plan.routing.unserved_orders}
        print(f'final plan v{plan.version}: served {len(served)} unserved {unserved}')
        for vehicle_id, start, order_ids in departures(plan):
            print(f'    {vehicle_id} departs {start:>6}s  {order_ids}')
    same = runs[0]['digest'] == runs[1]['digest'] and runs[0]['emitted'] == runs[1]['emitted']
    print('determinism:', 'identical' if same else 'DIVERGENT')
    return 0 if same else 1


if __name__ == '__main__':
    raise SystemExit(main())
