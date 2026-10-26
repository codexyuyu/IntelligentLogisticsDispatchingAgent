"""Explicit CSV data entry for R24 cold-chain tables, with full transaction rollback.

No synthetic defaults, no modification to base seven business tables. Run once per
file; duplicates abort rather than silently overwriting validated input.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
from decimal import Decimal


# Headings are part of the operator-facing schema; intentionally no implicit values.
FIELDS = {
    'zones': ('warehouse_code', 'temperature_zone', 'capacity_volume_l'),
    'lots': ('lot_code', 'warehouse_code', 'temperature_zone', 'quantity_units',
             'best_before_at', 'observed_at'),
    'orders': ('order_code', 'warehouse_code', 'lot_code', 'quantity_units', 'volume_l',
               'freshness_deadline', 'temperature_zone', 'observed_at'),
    'vehicles': ('vehicle_code', 'capacity_volume_l', 'remaining_weight_kg', 'remaining_volume_l',
                 'temperature_zone', 'shift_start', 'shift_end', 'available_at', 'current_node_key', 'observed_at'),
    'resources': ('warehouse_code','resource_code','resource_kind','temperature_zone',
                  'capacity_units','available_from','available_until'),
    'handoffs': ('order_code', 'warehouse_code', 'ready_at', 'loading_window_end',
                 'operation_status', 'resource_code', 'observed_at'),
}
QUERIES = {
    'zones': '''INSERT INTO public.pg_r24_warehouse_zones(warehouse_id, temperature_zone, capacity_volume_l)
      SELECT w.id,%s,%s FROM public.warehouses w WHERE w.code=%s RETURNING warehouse_id''',
    'lots': '''INSERT INTO public.pg_r24_stock_lots(lot_code, warehouse_id, temperature_zone,
       quantity_units, best_before_at, observed_at)
      SELECT %s,w.id,%s,%s,%s,%s FROM public.warehouses w WHERE w.code=%s RETURNING lot_code''',
    'orders': '''INSERT INTO public.pg_r24_order_details(order_id,warehouse_id,lot_code,
       quantity_units,volume_l,freshness_deadline,temperature_zone,observed_at)
      SELECT d.id,w.id,%s,%s,%s,%s,%s,%s FROM public.delivery_orders d CROSS JOIN public.warehouses w
      WHERE d.code=%s AND w.code=%s RETURNING order_id''',
    'vehicles': '''INSERT INTO public.pg_r24_vehicle_details(vehicle_id,capacity_volume_l,
       remaining_weight_kg,remaining_volume_l,temperature_zone,shift_start,shift_end,
       available_at,current_node_key,observed_at)
      SELECT v.id,%s,%s,%s,%s,%s,%s,%s,%s,%s FROM public.vehicles v
      WHERE v.code=%s RETURNING vehicle_id''',
    'resources': '''INSERT INTO public.pg_r24_resources(warehouse_id,resource_code,resource_kind,
      temperature_zone,capacity_units,available_from,available_until)
      SELECT w.id,%s,%s,%s,%s,%s,%s FROM public.warehouses w WHERE w.code=%s
      RETURNING resource_code''',
    'handoffs': '''INSERT INTO public.pg_r24_dock_operations(order_id,warehouse_id,
       ready_at,loading_window_end,operation_status,resource_code,observed_at)
      SELECT d.id,w.id,%s,%s,%s,%s,%s FROM public.delivery_orders d CROSS JOIN public.warehouses w
      WHERE d.code=%s AND w.code=%s RETURNING order_id''',
}


def read_rows(kind: str, path: Path) -> list[dict]:
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != FIELDS[kind]:
            raise ValueError(f'{kind}:columns_must_exactly_match_template')
        records = []
        for i, row in enumerate(reader, start=2):
            if any(v is None or not str(v).strip() for v in row.values()):
                raise ValueError(f'{kind}:empty_field_line_{i}')
            for key, value in row.items():
                if key.endswith('_at') or key in ('freshness_deadline','shift_start','shift_end',
                                                   'available_at','ready_at','loading_window_end'):
                    dt = datetime.fromisoformat(value)
                    if dt.tzinfo is None or dt.utcoffset() is None:
                        raise ValueError(f'{kind}:timezone_required_line_{i}')
                if key in ('quantity_units','volume_l','capacity_volume_l','capacity_units','remaining_weight_kg',
                           'remaining_volume_l'):
                    number = Decimal(value)
                    if number != number.to_integral_value() or number < 0 or (number == 0 and key.startswith(('capacity','quantity','volume'))):
                        raise ValueError(f'{kind}:invalid_integer_line_{i}')
                if key == 'resource_kind' and value not in ('cold_room','loading_dock','pre_cooler'):
                    raise ValueError(f'{kind}:invalid_resource_kind_line_{i}')
                if key == 'temperature_zone' and value not in ('chilled','frozen'):
                    raise ValueError(f'{kind}:invalid_zone_line_{i}')
            records.append(row)
    return records


def params(kind: str, row: dict) -> tuple:
    if kind == 'zones':
        return row['temperature_zone'], row['capacity_volume_l'], row['warehouse_code']
    if kind == 'lots':
        return (row['lot_code'], row['temperature_zone'], row['quantity_units'],
                row['best_before_at'], row['observed_at'], row['warehouse_code'])
    if kind == 'orders':
        return (row['lot_code'],row['quantity_units'],row['volume_l'],row['freshness_deadline'],
                row['temperature_zone'],row['observed_at'],row['order_code'],row['warehouse_code'])
    if kind == 'resources':
        return tuple(row[k] for k in FIELDS['resources'] if k != 'warehouse_code') + (row['warehouse_code'],)
    if kind == 'vehicles':
        return tuple(row[k] for k in FIELDS['vehicles'] if k != 'vehicle_code') + (row['vehicle_code'],)
    return (row['ready_at'],row['loading_window_end'],row['operation_status'],
            row['resource_code'],row['observed_at'],row['order_code'],row['warehouse_code'])


def main():
    parser = argparse.ArgumentParser(description='R24 CSV 补录；默认校验，不写入数据库')
    for key in FIELDS:
        parser.add_argument('--' + key, type=Path)
    parser.add_argument('--apply', action='store_true', help='明确执行全事务插入（已有重复记录会报错并回滚）')
    args = parser.parse_args()
    loaded = {kind: read_rows(kind, getattr(args, kind)) for kind in FIELDS if getattr(args, kind) is not None}
    if not loaded:
        parser.error('请指定至少一个 --zones/--lots/--orders/--vehicles/--resources/--handoffs CSV 路径')
    for kind, records in loaded.items():
        print(f'{kind}: {len(records)} rows; headers and basic types checked')
    if not args.apply:
        print('DRY RUN；未连接或写入数据库。使用 --apply 并确认备份后才写入。')
        return
    from app.adapters.persistence.pg_simulation_archive import _connection
    with _connection() as conn:
        with conn.transaction():
            for kind in FIELDS:
                for row in loaded.get(kind, []):
                    record = conn.execute(QUERIES[kind], params(kind, row)).fetchone()
                    if not record:
                        raise ValueError(f'{kind}:related_base_code_missing; transaction_rolled_back')
    print('补录事务成功；仅新增 R24 扩展表记录，不修改原有业务表。')


if __name__ == '__main__':
    main()
