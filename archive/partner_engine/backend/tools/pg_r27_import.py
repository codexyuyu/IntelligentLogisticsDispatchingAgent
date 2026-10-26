"""CSV -> R27 explicitly recorded warehouse operation standards.

Dry run by default, transactionally INSERT ONLY on explicit approval. Does not
update legacy business records or existing warehouse work/dispatch plans.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime
from pathlib import Path
import re

COLUMNS = ('operation_code','order_code','warehouse_code','resource_code',
           'operation_kind','duration_s','release_at','deadline_at','predecessor_code','observed_at')
CODE = re.compile(r'^[A-Za-z0-9_-]{1,55}$')


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError('r27_csv_header_mismatch')
        rows = []
        seen = set()
        for lineno, row in enumerate(reader, 2):
            for key in ('operation_code','order_code','warehouse_code','resource_code'):
                if not row.get(key) or not CODE.fullmatch(row[key]):
                    raise ValueError(f'line_{lineno}:invalid_{key}')
            if row['operation_code'] in seen:
                raise ValueError(f'line_{lineno}:duplicate_operation_code')
            seen.add(row['operation_code'])
            if row['warehouse_code'] != 'WH001':
                raise ValueError(f'line_{lineno}:only_WH001_supported')
            if row['operation_kind'] not in ('pick','stage','load'):
                raise ValueError(f'line_{lineno}:invalid_operation_kind')
            if not row['duration_s'] or not row['duration_s'].isdecimal() or int(row['duration_s']) <= 0:
                raise ValueError(f'line_{lineno}:invalid_duration_s')
            for key in ('release_at','deadline_at','observed_at'):
                try: dt = datetime.fromisoformat(row[key])
                except (TypeError, ValueError): raise ValueError(f'line_{lineno}:invalid_{key}') from None
                if dt.tzinfo is None or dt.utcoffset() is None:
                    raise ValueError(f'line_{lineno}:timezone_required_{key}')
            if datetime.fromisoformat(row['deadline_at']) <= datetime.fromisoformat(row['release_at']):
                raise ValueError(f'line_{lineno}:release_after_deadline')
            parent = row.get('predecessor_code') or None
            if parent is not None and (not CODE.fullmatch(parent) or parent == row['operation_code']):
                raise ValueError(f'line_{lineno}:invalid_predecessor')
            row['predecessor_code'] = parent
            rows.append(row)
    if not rows:
        raise ValueError('r27_csv_has_no_operations')
    # Cyclic or unknown predecessors must fail before any database writes.
    by_code = {row['operation_code']: row for row in rows}
    for row in rows:
        parent = row['predecessor_code']
        if parent and (parent not in by_code or by_code[parent]['order_code'] != row['order_code']):
            raise ValueError('predecessor_missing_or_cross_order:' + row['operation_code'])
        chain = {row['operation_code']}
        while parent:
            if parent in chain:
                raise ValueError('predecessor_cycle:' + row['operation_code'])
            chain.add(parent)
            parent = by_code[parent]['predecessor_code']
    return rows


def main():
    parser = argparse.ArgumentParser(description='R27 warehouse work CSV import: dry-run by default')
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup-verified', action='store_true')
    parser.add_argument('--confirm', default='')
    args = parser.parse_args()
    rows = read_csv(args.csv)
    print(f'R27 CSV checked: {len(rows)} operations, {len({r["order_code"] for r in rows})} orders; warehouse WH001')
    if not args.apply:
        print('DRY RUN: database was NOT accessed or modified.')
        return
    if not args.backup_verified or args.confirm != 'WH001':
        parser.error('For database writes require --apply --backup-verified --confirm WH001')
    from app.adapters.persistence.pg_simulation_archive import _connection
    with _connection() as conn:
        with conn.transaction():
            for row in rows:
                result = conn.execute('''INSERT INTO public.pg_r27_work_operations(
                  operation_code,order_id,warehouse_id,resource_code,operation_kind,
                  duration_s,release_at,deadline_at,predecessor_code,observed_at)
                SELECT %s,o.id,w.id,%s,%s,%s,%s,%s,%s,%s
                FROM public.delivery_orders o CROSS JOIN public.warehouses w
                WHERE o.code=%s AND w.code=%s RETURNING operation_code''',
                (row['operation_code'], row['resource_code'], row['operation_kind'],
                 int(row['duration_s']), row['release_at'],row['deadline_at'],
                 row['predecessor_code'],row['observed_at'],row['order_code'],row['warehouse_code'])).fetchone()
                if not result:
                    raise ValueError('unknown_order_or_warehouse:' + row['operation_code'])
    print('R27 operations inserted transactionally; no business dispatch plans were written.')


if __name__ == '__main__':
    main()
