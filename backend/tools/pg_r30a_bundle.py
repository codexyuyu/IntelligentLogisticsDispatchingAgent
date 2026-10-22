"""R30-A: prepare and explicitly import a PostgreSQL-backed *synthetic demonstration*.

Read the installed base PostgreSQL rows, preserving all original identifiers and
numeric warehouse/order/vehicle facts. Only R24/R27 extension records are generated.
No row is inserted until --apply, --backup-verified, and --confirm DEMO_WH001.
A durable provenance marker prevents a synthetic bundle from being called real data.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from app.adapters.persistence.pg_routing_preview import (
    BridgeInputError, _datetime, _pos_int, _temp_zone, load_view_data,
)
from tools.r24_import_csv import FIELDS, QUERIES, read_rows, params
from tools.pg_r27_import import COLUMNS, read_csv

KINDS = (*FIELDS, 'work_operations')
PROVENANCE_SQL = '''CREATE TABLE IF NOT EXISTS public.pg_r30a_data_provenance (
 singleton integer PRIMARY KEY CHECK(singleton=1),
 source_kind text NOT NULL CHECK(source_kind='explicit_synthetic_demo'),
 warehouse_code text NOT NULL CHECK(warehouse_code='WH001'),
 base_digest_sha256 text NOT NULL CHECK(length(base_digest_sha256)=64),
 bundle_digest_sha256 text NOT NULL CHECK(length(bundle_digest_sha256)=64),
 created_at timestamptz NOT NULL DEFAULT now(),
 description text NOT NULL
)'''


def base_fingerprint(data: dict) -> str:
    """Bind the CSV bundle to the actual, exact business base records."""
    source = {key: data[key] for key in ('orders','vehicles','nodes','distance_matrix')}
    text = json.dumps(source, ensure_ascii=False, sort_keys=True, default=str, separators=(',',':'))
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def assemble(data: dict) -> dict[str, list[dict]]:
    """Deliberately synthetic, deterministic parameters; no claim of measurement."""
    warehouse_keys = {n['node_key'] for n in data['nodes'] if n['node_key'].startswith('WH:')}
    if warehouse_keys != {'WH:WH001'} or any(v['warehouse_code'] != 'WH001' for v in data['vehicles']):
        raise BridgeInputError('r30a_requires_R29_single_active_WH001')
    orders = sorted(data['orders'], key=lambda r: r['order_code'])
    vehicles = sorted(data['vehicles'], key=lambda r: r['vehicle_code'])
    if not orders or not vehicles:
        raise BridgeInputError('r30a_orders_and_vehicles_required')
    codes = [o['order_code'] for o in orders]
    if len(codes) != len(set(codes)) or len({v['vehicle_code'] for v in vehicles}) != len(vehicles):
        raise BridgeInputError('r30a_duplicate_base_codes')
    zones = {zone: [] for zone in ('chilled', 'frozen')}
    for order in orders:
        zones[_temp_zone(order, item='order:' + order['order_code'])].append(order)
    result: dict[str, list[dict]] = {kind: [] for kind in KINDS}
    for zone, grouped in zones.items():
        if not grouped:
            continue
        compatible = [v for v in vehicles if all(
            Decimal(str(v['min_temp_c'])) <= Decimal(str(o['min_temp_c']))
            and Decimal(str(v['max_temp_c'])) >= Decimal(str(o['max_temp_c'])) for o in grouped)]
        if not compatible:
            raise BridgeInputError('r30a_no_original_vehicle_covers_zone:' + zone)
        earliest = min(_datetime(o['window_start'], 'window_start') for o in grouped)
        latest = max(_datetime(o['window_end'], 'window_end') for o in grouped)
        work_begin = earliest - timedelta(hours=3)
        operations_end = earliest - timedelta(minutes=10)
        resource_begin = earliest - timedelta(hours=4)
        resource_end = latest + timedelta(hours=8)
        observed = earliest - timedelta(days=2)
        iso = lambda d: d.isoformat()
        label = zone.upper()
        cold_code = 'R30_COLD_' + label
        dock_code = 'R30_DOCK_' + label
        total_l = sum(_pos_int(o['weight_kg'], 'weight_kg') * 2 for o in grouped)
        result['zones'].append({'warehouse_code':'WH001','temperature_zone':zone,
                                'capacity_volume_l':max(total_l * 3, 10000)})
        for code, kind in ((cold_code, 'cold_room'), (dock_code, 'loading_dock')):
            result['resources'].append({'warehouse_code':'WH001','resource_code':code,
                'resource_kind':kind,'temperature_zone':zone, 'capacity_units':1,
                'available_from':iso(resource_begin), 'available_until':iso(resource_end)})
        for order in grouped:
            order_code = str(order['order_code'])
            _pos_int(order['service_minutes'], 'service_minutes')
            # Preserve real base weight and time windows; the remaining quantities are
            # openly SYNTHETIC. Separate lots avoid invented real inventory pooling.
            lot = 'R30DEMO_' + order_code
            detail_volume = _pos_int(order['weight_kg'], 'weight_kg') * 2
            result['lots'].append({'lot_code':lot,'warehouse_code':'WH001','temperature_zone':zone,
                'quantity_units':2,'best_before_at':iso(latest + timedelta(days=3)),
                'observed_at':iso(observed)})
            result['orders'].append({'order_code':order_code,'warehouse_code':'WH001',
                'lot_code':lot,'quantity_units':1,'volume_l':detail_volume,
                'freshness_deadline':iso(latest + timedelta(hours=6)),
                'temperature_zone':zone,'observed_at':iso(observed)})
            result['handoffs'].append({'order_code':order_code,'warehouse_code':'WH001',
                'ready_at':iso(work_begin),'loading_window_end':iso(latest + timedelta(hours=5)),
                'operation_status':'planned','resource_code':dock_code,
                'observed_at':iso(observed)})
            p = 'R30P_' + order_code
            l = 'R30L_' + order_code
            for op_code, kind, resource, parent in ((p,'pick',cold_code,''), (l,'load',dock_code,p)):
                result['work_operations'].append({'operation_code':op_code,
                    'order_code':order_code,'warehouse_code':'WH001','resource_code':resource,
                    'operation_kind':kind,'duration_s':30,
                    'release_at':iso(work_begin), 'deadline_at':iso(operations_end),
                    'predecessor_code':parent or None, 'observed_at':iso(observed)})
    for vehicle in vehicles:
        code = vehicle['vehicle_code']
        # Restrict to its original hardware temperature band; do not invent new capabilities.
        compatible_zones = [z for z, grouped in zones.items() if grouped and all(
            Decimal(str(vehicle['min_temp_c'])) <= Decimal(str(o['min_temp_c']))
            and Decimal(str(vehicle['max_temp_c'])) >= Decimal(str(o['max_temp_c'])) for o in grouped)]
        if not compatible_zones:
            raise BridgeInputError('r30a_base_vehicle_cannot_serve_any_zone:' + code)
        if len(compatible_zones) > 1:
            raise BridgeInputError('r30a_vehicle_ambiguous_multi_zone_choose_manually:' + code)
        zone = compatible_zones[0]
        earliest = min(_datetime(o['window_start'], 'window_start') for o in zones[zone])
        latest = max(_datetime(o['window_end'], 'window_end') for o in zones[zone])
        capacity = _pos_int(vehicle['capacity_kg'], 'capacity_kg')
        result['vehicles'].append({'vehicle_code':code,'capacity_volume_l':capacity*3,
            'remaining_weight_kg':capacity,'remaining_volume_l':capacity*3,
            'temperature_zone':zone,'shift_start':(earliest-timedelta(hours=2)).isoformat(),
            'shift_end':(latest+timedelta(hours=6)).isoformat(),
            'available_at':(earliest-timedelta(hours=2)).isoformat(),
            'current_node_key':'WH:WH001',
            'observed_at':(earliest-timedelta(days=2)).isoformat()})
    return result


def preview_generated(data: dict, rows: dict) -> list[dict]:
    """Run the actual R27 PG-to-snapshot adapter on generated candidate rows.

    No solver is invoked here: it is an offline schema/constraint preflight, not a
    guarantee of feasibility. The Windows workflow later uses real CP-SAT/OR-Tools.
    """
    from app.adapters.persistence.pg_r27_workflow import verified_snapshot
    from app.adapters.persistence.pg_r30a_provenance import load_provenance  # noqa: F401
    projected = dict(data)
    projected['r24'] = {
        kind: [{**row, **({'version': 1} if kind in ('lots', 'orders', 'vehicles', 'resources', 'handoffs') else {})}
               for row in rows[kind]] for kind in FIELDS
    }
    projected['r27'] = {'installed': True, 'operations': [
        {**op, 'version': 1} for op in rows['work_operations'] ]}
    projected['r30a'] = {'installed': True, 'source_kind': 'explicit_synthetic_demo'}
    result = []
    for zone in ('chilled', 'frozen'):
        expected = [x for x in rows['orders'] if x['temperature_zone'] == zone]
        if not expected:
            continue
        snapshot, meta = verified_snapshot(projected, temperature_zone=zone,
            travel_mode='straight_line_simulation', speed_kmh=30,
            max_orders=20, budget_ms=5000)
        if len(snapshot.orders) != len(expected) or len(snapshot.operations) != len(expected) * 2:
            raise BridgeInputError('r30a_generated_snapshot_scope_mismatch:' + zone)
        if any(x.source.source_kind != 'simulation' for x in snapshot.orders):
            raise BridgeInputError('r30a_synthetic_provenance_lost')
        result.append({'zone': zone, 'orders': len(snapshot.orders),
            'vehicles': len(snapshot.vehicles), 'warehouse_operations': len(snapshot.operations),
            'distance_type': meta['distance_type'], 'validated_structure': True})
    return result


def bundle_digest(directory: Path) -> str:
    h=hashlib.sha256()
    for kind in KINDS:
        h.update(kind.encode('ascii') + b'\0')
        h.update((directory / (kind + '.csv')).read_bytes())
    return h.hexdigest()


def export(data: dict, directory: Path) -> dict:
    if directory.exists() and any(directory.iterdir()):
        raise ValueError('r30a_bundle_directory_must_be_empty')
    rows = assemble(data)
    previews = preview_generated(data, rows)
    directory.mkdir(parents=True, exist_ok=True)
    for kind in KINDS:
        headers = COLUMNS if kind == 'work_operations' else FIELDS[kind]
        with (directory / (kind + '.csv')).open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows[kind])
    manifest = {'format':'r30a_explicit_synthetic_demo_v1',
        'warehouse':'WH001', 'source_kind':'explicit_synthetic_demo',
        'base_sha256':base_fingerprint(data), 'bundle_sha256':bundle_digest(directory),
        'counts':{kind:len(rows[kind]) for kind in KINDS},
        'snapshot_adapters_validated': previews,
        'strict_warning':'SYNTHETIC VOLUME, LOTS, SHIFTS, RESOURCES, READY-AT AND DURATIONS. NOT OBSERVED BUSINESS FACTS.',
        'base_fact_fields':'order and vehicle codes, original weight/time windows/temperature limits, geographic matrix'}
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (directory / 'IMPORTANT_READ_ME.txt').write_text(
        'R30-A 明确标记的【合成演示业务数据】。数量、体积、库存批次、工时、班次、月台不是现场实测！\n'
        '仅用于验证 PostgreSQL → CP-SAT → OR-Tools 的本地非执行调度链路。\n'
        '请勿提交为生产事实或用于真实发车、库存扣减；备份并确认后才能运行 -Apply。\n'
        '本目录含订单等本地数据库标识，请勿向公共网站上传。\n', encoding='utf-8-sig')
    return manifest


def validate_bundle(directory: Path, data: dict) -> tuple[dict, dict]:
    manifest=json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('format') != 'r30a_explicit_synthetic_demo_v1' or manifest.get('warehouse') != 'WH001':
        raise ValueError('r30a_unrecognized_bundle')
    if manifest['base_sha256'] != base_fingerprint(data):
        raise ValueError('r30a_base_data_changed_since_export_refuse_write')
    if manifest['bundle_sha256'] != bundle_digest(directory):
        raise ValueError('r30a_csv_tampered_or_modified_refuse_write')
    rows = {kind: (read_csv(directory / (kind + '.csv')) if kind == 'work_operations'
                   else read_rows(kind, directory / (kind + '.csv'))) for kind in KINDS}
    if {kind:len(rows[kind]) for kind in KINDS} != manifest['counts']:
        raise ValueError('r30a_bundle_row_count_mismatch')
    def normalize(value):
        return {kind: [ {k: '' if v is None else str(v) for k,v in row.items()} for row in items ]
                for kind,items in value.items()}
    if normalize(rows) != normalize(assemble(data)):
        raise ValueError('r30a_generated_business_facts_changed')
    if preview_generated(data, rows) != manifest.get('snapshot_adapters_validated'):
        raise ValueError('r30a_pg_snapshot_adapter_validation_changed')
    return manifest, rows


def apply_bundle(directory: Path, data: dict) -> dict:
    """Atomic opt-in extension-only import; refuses partial existing data."""
    manifest, rows = validate_bundle(directory, data)
    if data.get('r24') is None or not data.get('r27', {}).get('installed'):
        raise ValueError('r30a_R24_R27_tables_must_be_explicitly_installed_first')
    if any(data['r24'][key] for key in FIELDS) or data['r27']['operations']:
        raise ValueError('r30a_existing_R24_R27_data_refuse_to_overwrite_or_mix')
    if data.get('r30a', {}).get('installed'):
        raise ValueError('r30a_provenance_already_exists_refuse_duplicate_seed')
    from app.adapters.persistence.pg_simulation_archive import _connection
    with _connection() as conn:
        with conn.transaction():
            # Recheck inside the write transaction, including all extension tables.
            for table in ('pg_r24_warehouse_zones','pg_r24_stock_lots','pg_r24_order_details',
                          'pg_r24_vehicle_details','pg_r24_resources','pg_r24_dock_operations',
                          'pg_r27_work_operations'):
                result=conn.execute(f'SELECT COUNT(*) AS n FROM public.{table}').fetchone()
                if result['n']:
                    raise ValueError('r30a_existing_extension_rows_refuse_write:' + table)
            conn.execute(PROVENANCE_SQL)
            if conn.execute('SELECT COUNT(*) AS n FROM public.pg_r30a_data_provenance').fetchone()['n']:
                raise ValueError('r30a_provenance_exists_refuse_reseed')
            for kind in FIELDS:
                for row in rows[kind]:
                    inserted=conn.execute(QUERIES[kind], params(kind,row)).fetchone()
                    if inserted is None:
                        raise ValueError('r30a_base_identifier_not_found:' + kind)
            for row in rows['work_operations']:
                inserted=conn.execute('''INSERT INTO public.pg_r27_work_operations(
                  operation_code,order_id,warehouse_id,resource_code,operation_kind,
                  duration_s,release_at,deadline_at,predecessor_code,observed_at)
                SELECT %s,o.id,w.id,%s,%s,%s,%s,%s,%s,%s
                FROM public.delivery_orders o CROSS JOIN public.warehouses w
                WHERE o.code=%s AND w.code=%s RETURNING operation_code''',
                (row['operation_code'],row['resource_code'],row['operation_kind'],
                 int(row['duration_s']),row['release_at'],row['deadline_at'],
                 row['predecessor_code'] or None,row['observed_at'],row['order_code'],
                 row['warehouse_code'])).fetchone()
                if inserted is None:
                    raise ValueError('r30a_work_base_identifier_not_found')
            conn.execute('''INSERT INTO public.pg_r30a_data_provenance(
                singleton,source_kind,warehouse_code,base_digest_sha256,bundle_digest_sha256,description)
                VALUES (1,'explicit_synthetic_demo','WH001',%s,%s,%s)''',
                (manifest['base_sha256'], manifest['bundle_sha256'],
                 'Synthetic volume, lots, shifts, resources, durations and handoffs; non-operational planning only'))
    return {'database_mutated':True,'base_tables_mutated':False,
            'source_kind':'explicit_synthetic_demo','counts':manifest['counts'],
            'warning':'NOT REAL BUSINESS FACTS; only R24/R27 extensions and R30A provenance inserted'}


def main() -> None:
    parser = argparse.ArgumentParser(description='R30A 单仓数据准备。默认只读；明确 -Apply 才追加演示数据。')
    parser.add_argument('--output', type=Path, help='生成合成演示 CSV；目标目录必须为空')
    parser.add_argument('--bundle', type=Path, help='仅验证或显式导入既有 R30A 演示数据包')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup-verified', action='store_true')
    parser.add_argument('--confirm', default='')
    args=parser.parse_args()
    if bool(args.output) == bool(args.bundle):
        parser.error('必须二选一：--output 或 --bundle')
    if args.apply and (not args.bundle or not args.backup_verified or args.confirm != 'DEMO_WH001'):
        parser.error('--apply 需要 --bundle --backup-verified --confirm DEMO_WH001')
    data=load_view_data(include_r27=True)
    if args.output:
        result=export(data,args.output)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        print('ONLY CSV FILES WRITTEN. No database changes. Values are SYNTHETIC DEMO.')
        return
    if args.apply:
        status=apply_bundle(args.bundle,data)
        print(json.dumps(status,ensure_ascii=False,indent=2))
        return
    manifest,_=validate_bundle(args.bundle,data)
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
    print('CSV verified; DATABASE NOT MODIFIED. Run --apply only after pg_dump backup.')


if __name__ == '__main__':
    main()
