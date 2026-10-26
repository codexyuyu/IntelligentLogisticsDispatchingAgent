"""Convert data/preparation/competition-2026 bundle.json into R30 PlanningSnapshot scenarios.

Output: data/scenarios/prep_<scenario>.json (one per T1/A8/B20) plus a loss report.
Each snapshot is validated by constructing the shared contract model; any record
the contract cannot express is either rejected (raise) or listed in the report.

Unit conversion is conservative: demand rounds up, capacity rounds down, so a
conversion can never make an overloaded plan look feasible.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from app.contracts.entities import PlanningSnapshot  # noqa: E402

BUNDLE = ROOT / 'data' / 'preparation' / 'competition-2026' / 'generated' / 'bundle.json'
OUT_DIR = ROOT / 'data' / 'scenarios'
RULE_VERSION = 'prep-v1'

PREFIX = {
    'Node': 'node', 'Warehouse': 'wh', 'WarehouseZone': 'zone', 'StorageLocation': 'loc',
    'Dock': 'res', 'Worker': 'res', 'Equipment': 'res', 'Driver': 'drv', 'Vehicle': 'veh',
    'Order': 'ord', 'Cargo': 'batch', 'InitialStock': 'stk', 'TransportTask': 'tt',
    'ExternalArrival': 'arr', 'WarehouseTask': 'op',
}
RESOURCE_KIND = {'Dock': 'dock', 'Worker': 'worker'}


def zone_of(min_decic: int, max_decic: int) -> str:
    if 0 <= min_decic and max_decic <= 80:
        return 'chilled'
    if max_decic <= -180:
        return 'frozen'
    raise ValueError(f'temperature range {min_decic}..{max_decic} decic maps to no contract zone')


def setpoint_zone(decic: int) -> str:
    if 0 <= decic <= 80:
        return 'chilled'
    if decic <= -180:
        return 'frozen'
    raise ValueError(f'setpoint {decic} decic maps to no contract zone')


def up(value: int, div: int) -> int:
    return max(1, math.ceil(value / div))


def down(value: int, div: int) -> int:
    result = value // div
    if result <= 0:
        raise ValueError(f'capacity {value} rounds down to 0 at /{div}')
    return result


def window(pair) -> dict:
    return {'start_s': int(pair[0]), 'end_s': int(pair[1])}


def convert(bundle: dict, scenario: str) -> tuple[dict, list[str]]:
    ents = [e for e in bundle['entities'] if e['scenario'] == scenario]
    by_kind: dict[str, list[dict]] = defaultdict(list)
    for e in ents:
        by_kind[e['kind']].append(e)
    ids: dict[str, str] = {}
    for e in ents:
        ids[e['id']] = f"{PREFIX[e['kind']]}_{scenario}_{e['code']}"
    losses: list[str] = []
    epoch = bundle['epoch_utc'].replace('Z', '+00:00')
    source = {'source_kind': 'simulation', 'source_ref': f'preparation-v1:{scenario}:seed{bundle["seed"]}',
              'observed_at': epoch, 'rule_version': RULE_VERSION}

    cargo = {c['id']: c for c in by_kind['Cargo']}
    matrix = next(m for m in bundle['matrices'] if m['scenario'] == scenario)
    for row in matrix['connected']:
        if not all(row):
            raise ValueError(f'{scenario}: disconnected matrix arcs are not expressible as contract nulls here')

    warehouses = []
    for w in by_kind['Warehouse']:
        zones = sorted({setpoint_zone(z['setpoint_decic']) for z in by_kind['WarehouseZone']
                        if z['warehouse_id'] == w['id']})
        warehouses.append({'warehouse_id': ids[w['id']], 'version': 1,
                           'node_id': ids[w['node_id']], 'temperature_zones': zones})

    resources = []
    for kind in ('Dock', 'Worker', 'Equipment'):
        for r in by_kind[kind]:
            cap = r.get('capacity', r.get('quantity_capacity', 1))
            resources.append({
                'resource_id': ids[r['id']], 'warehouse_id': ids[r['warehouse_id']], 'version': 1,
                'resource_kind': RESOURCE_KIND.get(kind, r.get('preparation_kind', 'equipment')),
                'capacity_units': int(cap),
                'available_windows': [window(iv) for iv in r['calendar']['intervals']],
                'unavailable_windows': [],
            })
            if kind == 'Dock' and r.get('setup_duration_s'):
                losses.append(f'{ids[r["id"]]}: dock setup_duration_s={r["setup_duration_s"]} not expressible')
    if by_kind['StorageLocation']:
        losses.append(f'{len(by_kind["StorageLocation"])} StorageLocation capacities dropped: contract has no '
                      'time-varying storage occupancy')

    orders, stock_lots = [], []
    warehouse_of_cargo = {}
    for s in by_kind['InitialStock']:
        loc = next(l for l in by_kind['StorageLocation'] if l['id'] == s['location_id'])
        zone = next(z for z in by_kind['WarehouseZone'] if z['id'] == loc['zone_id'])
        warehouse_of_cargo[s['cargo_id']] = zone['warehouse_id']
    for a in by_kind['ExternalArrival']:
        warehouse_of_cargo.setdefault(a['cargo_id'], a['warehouse_id'])

    for o in by_kind['Order']:
        if len(o['cargo_ids']) != 1:
            raise ValueError(f'{o["code"]}: contract Order carries exactly one batch')
        c = cargo[o['cargo_ids'][0]]
        wh = warehouse_of_cargo[c['id']]
        zone = zone_of(c['min_temp_decic'], c['max_temp_decic'])
        orders.append({
            'order_id': ids[o['id']], 'version': 1, 'warehouse_id': ids[wh],
            'batch_id': ids[c['id']], 'delivery_node_id': ids[o['delivery_node_id']],
            'quantity_units': int(c['quantity_units']),
            'weight_kg': up(c['weight_g'], 1000), 'volume_l': up(c['volume_cm3'], 1000),
            'temperature_zone': zone, 'service_window': window(o['delivery_window']),
            'service_duration_s': int(o['service_s']),
            'freshness_deadline_s': int(o['delivery_window'][1]),
            'required': bool(o['must_serve']), 'source': source,
        })
        if o.get('soft_due_at_s') is not None:
            losses.append(f'{ids[o["id"]]}: soft_due_at_s={o["soft_due_at_s"]} dropped (no soft target field)')
        losses.append(f'{ids[o["id"]]}: max_exposure_s={c["max_exposure_s"]} dropped (no exposure field)')
        on_hand = sum(s['quantity_units'] for s in by_kind['InitialStock'] if s['cargo_id'] == c['id'])
        on_hand += sum(a['quantity_units'] for a in by_kind['ExternalArrival'] if a['cargo_id'] == c['id'])
        stock_lots.append({
            'batch_id': ids[c['id']], 'warehouse_id': ids[wh], 'version': 1, 'temperature_zone': zone,
            'on_hand_units': on_hand, 'reserved_units': 0, 'quarantined_units': 0,
            'expires_at': bundle['epoch_utc'].replace('Z', '+00:00').replace('T00:00:00', 'T23:59:59'),
        })
    losses.append('StockLot.expires_at set to end of epoch day: bundle carries no batch expiry')
    arrivals = [a for a in by_kind['ExternalArrival']]
    if arrivals:
        losses.append(f'{len(arrivals)} ExternalArrival arrival_s folded into on_hand_units; '
                      'arrival timing is carried only by op release_at_s')

    vehicles = []
    for v in by_kind['Vehicle']:
        home = next(w for w in by_kind['Warehouse'] if w['node_id'] == v['start_node_id'])
        cap_w, cap_v = down(v['capacity_weight_g'], 1000), down(v['capacity_volume_cm3'], 1000)
        shift = v['calendar']['intervals']
        if len(shift) != 1:
            raise ValueError(f'{v["code"]}: contract shift_window is a single interval')
        vehicles.append({
            'vehicle_id': ids[v['id']], 'version': 1, 'warehouse_id': ids[home['id']],
            'start_node_id': ids[v['start_node_id']], 'end_node_id': ids[v['end_node_id']],
            'current_node_id': ids[v['start_node_id']],
            'capacity_weight_kg': cap_w, 'capacity_volume_l': cap_v,
            'remaining_weight_kg': cap_w, 'remaining_volume_l': cap_v,
            'temperature_zone': setpoint_zone(v['setpoint_decic']),
            'shift_window': window(shift[0]), 'available_at_s': int(shift[0][0]), 'source': source,
        })
        losses.append(f'{ids[v["id"]]}: fixed_cost_cents/rate_cents_per_km dropped (no cost fields)')

    operations = []
    arrival_at = {a['cargo_id']: a['arrival_s'] for a in arrivals}
    for t in by_kind['WarehouseTask']:
        reqs = t['requirements']
        primary = reqs[0]['resource_ids'][0]
        if len(reqs) > 1:
            losses.append(f'{ids[t["id"]]}: {len(reqs)} simultaneous resource requirements reduced to 1 '
                          '(contract Operation occupies one resource)')
        operations.append({
            'operation_id': ids[t['id']], 'order_ids': [ids[t['order_id']]],
            'warehouse_id': ids[t['warehouse_id']], 'resource_id': ids[primary],
            'operation_kind': t['preparation_operation'], 'duration_s': int(t['duration_s']),
            'release_at_s': max(int(t['window'][0]), int(arrival_at.get(t['cargo_id'], 0))),
            'deadline_at_s': int(t['window'][1]),
            'predecessor_ids': [ids[p] for p in t['predecessor_ids']], 'status': 'pending',
        })
        if t.get('setup_class'):
            losses.append(f'{ids[t["id"]]}: setup_class={t["setup_class"]} dropped (no sequence setup)')

    snapshot = {
        'snapshot_id': f'snap_prep_{scenario}', 'version': 1, 'origin_at': epoch,
        'simulation_time_s': 0, 'rule_version': RULE_VERSION,
        'orders': orders, 'vehicles': vehicles, 'warehouses': warehouses, 'resources': resources,
        'stock_lots': stock_lots, 'operations': operations, 'frozen_operations': [],
        'matrix': {
            'matrix_id': f'mtx_prep_{scenario}', 'version': 1,
            'node_ids': [ids[n] for n in matrix['node_ids']],
            'duration_s': matrix['travel_s'], 'distance_m': matrix['distance_m'],
            'source': {**source, 'source_ref': f'preparation-v1:{scenario}:{matrix["model"]}'},
        },
    }
    PlanningSnapshot.model_validate(snapshot)
    return snapshot, losses


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='fail if outputs differ from disk')
    args = parser.parse_args()
    bundle = json.loads(BUNDLE.read_text(encoding='utf-8'))
    report = {}
    drift = []
    for scenario in ('T1', 'A8', 'B20'):
        snapshot, losses = convert(bundle, scenario)
        text = json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n'
        path = OUT_DIR / f'prep_{scenario}.json'
        if args.check:
            if not path.exists() or path.read_text(encoding='utf-8') != text:
                drift.append(path.name)
        else:
            path.write_text(text, encoding='utf-8')
        report[scenario] = {'orders': len(snapshot['orders']), 'vehicles': len(snapshot['vehicles']),
                            'operations': len(snapshot['operations']), 'resources': len(snapshot['resources']),
                            'losses': losses}
    if args.check:
        if drift:
            print('drift:', ', '.join(drift))
            return 1
        print('prep scenarios match bundle')
        return 0
    (OUT_DIR / 'prep_import_report.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for s, r in report.items():
        print(f"{s}: {r['orders']} orders, {r['vehicles']} vehicles, {r['operations']} ops, "
              f"{r['resources']} resources, {len(r['losses'])} recorded losses")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
