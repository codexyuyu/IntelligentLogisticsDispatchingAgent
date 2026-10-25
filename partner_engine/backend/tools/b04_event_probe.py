"""Real-solver probe for the B-04 event types (not a unit test).

Run from the backend directory:
    python -m tools.b04_event_probe [--budget-ms 60000]

Builds one baseline plan, then replays a dock outage and a cargo quarantine through
handle_event with the real OR-Tools solver and prints what each event changed.
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.application.coordinator import coordinate
from app.application.handle_event import handle_event
from app.application.runtime import runtime
from app.contracts.common import Source
from app.contracts.events import DispatchEvent, EventPayload
from tools.r17_joint_ablation import load_snapshot

SNAPSHOT_FILE = Path('../data/scenarios/two_warehouses_20_orders.json')


def source(ref):
    return Source(source_kind='simulation', source_ref=ref, observed_at=datetime.now(timezone.utc),
                  rule_version='r20-1.0')


def describe(plan):
    rows = []
    for route in plan.routing.routes:
        deliveries = [s for s in route.stops if s.stop_kind == 'delivery']
        if deliveries:
            rows.append((route.vehicle_id, route.stops[0].departure_at_s,
                         tuple(o for s in deliveries for o in s.order_ids)))
    return sorted(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Replay the B-04 event types with the real solver')
    parser.add_argument('--scenario', type=Path, default=SNAPSHOT_FILE)
    parser.add_argument('--budget-ms', type=int, default=60000)
    args = parser.parse_args(argv)
    snapshot, fingerprint = load_snapshot(args.scenario)
    order_ids = tuple(sorted(o.order_id for o in snapshot.orders))
    runtime.put_snapshot(snapshot)
    baseline = coordinate(snapshot=snapshot, order_ids=order_ids, budget_ms=args.budget_ms,
                          max_coordination_rounds=1, coordination_mode='sequential')
    runtime.put_plan(baseline)
    print('scenario sha256', fingerprint[:16], 'orders', len(order_ids))
    print('baseline departures', describe(baseline))

    for label, event in (
        ('dock_unavailable wh_1 until 3600s',
         DispatchEvent(event_id='evt_e2e_dock', event_type='dock_unavailable',
                       snapshot_id=snapshot.snapshot_id, expected_snapshot_version=snapshot.version,
                       object_id='wh_1', occurred_at_s=0, received_at=datetime.now(timezone.utc),
                       source=source('e2e:dock'), payload=EventPayload(unavailable_until_s=3600))),
        ('cargo_quarantined ord_001+ord_002',
         DispatchEvent(event_id='evt_e2e_quar', event_type='cargo_quarantined',
                       snapshot_id=snapshot.snapshot_id, expected_snapshot_version=snapshot.version,
                       object_id='bat_001', occurred_at_s=0, received_at=datetime.now(timezone.utc),
                       source=source('e2e:quarantine'),
                       payload=EventPayload(affected_order_ids=('ord_001', 'ord_002')))),
    ):
        runtime.put_snapshot(snapshot)
        try:
            result = handle_event(event=event, previous_plan=baseline, budget_ms=args.budget_ms)
        except Exception as exc:  # noqa: BLE001 - report failures verbatim
            print(f'--- {label}: FAILED {type(exc).__name__}: {exc}')
            continue
        plan = result.replanned_plan
        unserved = {u.order_id: u.reason_code for u in plan.routing.unserved_orders}
        served = {oid for route in plan.routing.routes
                  for s in route.stops if s.stop_kind == 'delivery' for oid in s.order_ids}
        print(f'--- {label}: OK')
        print(f'    affected={len(result.impact.affected_order_ids)} '
              f'locked={len(result.impact.locked_order_ids)} served={len(served)} unserved={unserved}')
        print(f'    departures {describe(plan)}')
        print(f'    validation={result.validation.status} rules={len(result.validation.checked_rule_ids)}')
        if label.startswith('dock'):
            wh1_handoffs = [h for h in plan.warehouse.warehouse_handoffs
                            if h.order_id in set(result.impact.affected_order_ids)]
            print(f'    affected loading windows start at '
                  f'{sorted({h.loading_window.start_s for h in wh1_handoffs})} '
                  f'(ready_at kept: {sorted({h.ready_at_s for h in wh1_handoffs})})')


if __name__ == '__main__':
    main()
