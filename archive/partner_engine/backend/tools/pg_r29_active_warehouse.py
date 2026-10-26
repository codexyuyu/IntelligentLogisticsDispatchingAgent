"""R29 guarded logical retirement: one *active* PostgreSQL warehouse, history intact.

WH002 remains as a historical FK anchor for four legacy routes.  Never rewrite
routes, route_stops, dispatch_plans or historic simulation archives.  The R29
marker is read by the preview adapter to omit historical WH002 nodes/matrix
pairs.  All writes require an operator-verified backup and explicit approval.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from tools.pg_r26_single_warehouse import _connection, inspect

MARKER_TABLE = 'public.pg_r29_retired_warehouses'
AUDIT_TABLE = 'public.pg_r29_active_warehouse_audit'
EXPECTED_DEPS = {('public.vehicles', 'home_warehouse_id'),
                 ('public.routes', 'start_warehouse_id')}


def assess(report: dict, *, expected_historical_routes: int = 4) -> dict:
    """Pure conservative gate built from dynamic FK introspection, not assumptions."""
    by_key = {(r['relation'], r['column']): r for r in report['dependent_rows']}
    surprises = [r for r in report['dependent_rows']
                 if r['count'] is None or (r['count'] and
                 (r['relation'], r['column']) not in EXPECTED_DEPS)]
    routes = by_key.get(('public.routes', 'start_warehouse_id'))
    vehicles = by_key.get(('public.vehicles', 'home_warehouse_id'))
    n_routes = routes['count'] if routes is not None else None
    n_vehicles = vehicles['count'] if vehicles is not None else None
    codes = report['warehouse_codes']
    vehicle_rows = report['vehicles']
    valid = (codes == ['WH001', 'WH002'] and report['target_exists'] and
             report['source_exists'] and not surprises and routes is not None and
             vehicles is not None and n_routes == expected_historical_routes and
             n_vehicles == 2 and len(vehicle_rows) == 4 and
             {r['vehicle_code'] for r in vehicle_rows} ==
             {'V001', 'V002', 'V003', 'V004'} and
             {r['vehicle_code'] for r in vehicle_rows if r['warehouse_code'] == 'WH002'} ==
             {'V003', 'V004'} and
             all(r['warehouse_code'] == 'WH001' for r in vehicle_rows
                 if r['vehicle_code'] in ('V001', 'V002')))
    return {
        'strategy': 'retire_WH002_keep_historical_FK_rows',
        'expected_historical_routes': expected_historical_routes,
        'historical_route_count': n_routes,
        'vehicles_to_move': n_vehicles,
        'unexpected_nonempty_dependencies': surprises,
        'can_apply_logical': bool(valid),
        'physical_warehouse_rows_after': 2,
        'active_warehouse_codes_after': ['WH001'] if valid else None,
        'note': '历史路线保留原仓库外键；WH002 实体继续留库，仅从新调度读取中排除',
    }


def _marker_exists(conn) -> bool:
    return bool(conn.execute("""SELECT 1 FROM pg_catalog.pg_tables
      WHERE schemaname='public' AND tablename='pg_r29_retired_warehouses'""").fetchone())


def _retirement(conn):
    if not _marker_exists(conn):
        return None
    return conn.execute("""SELECT w.code AS retired_code, active.code AS active_code,
            r.retired_at FROM public.pg_r29_retired_warehouses r
         JOIN public.warehouses w ON w.id=r.warehouse_id
         JOIN public.warehouses active ON active.id=r.active_warehouse_id
         WHERE w.code='WH002'""").fetchone()


def preflight(conn, *, expected_historical_routes=4) -> dict:
    report = inspect(conn)
    retirement = _retirement(conn)
    if retirement:
        # Historical routes stay linked to WH002; the lifecycle FK also stays.
        expected = {('public.routes', 'start_warehouse_id'),
                    ('public.pg_r29_retired_warehouses', 'warehouse_id')}
        blocked = [row for row in report['dependent_rows']
                   if row['count'] is None or
                   (row['count'] and (row['relation'], row['column']) not in expected)]
        route_counts = [row['count'] for row in report['dependent_rows']
                        if (row['relation'], row['column']) == ('public.routes', 'start_warehouse_id')]
        marker_counts = [row['count'] for row in report['dependent_rows']
                         if (row['relation'], row['column']) ==
                         ('public.pg_r29_retired_warehouses', 'warehouse_id')]
        active_ok = (retirement['active_code'] == 'WH001' and
                     report['warehouse_codes'] == ['WH001', 'WH002'] and
                     len(report['vehicles']) == 4 and
                     {v['vehicle_code'] for v in report['vehicles']} == {'V001', 'V002', 'V003', 'V004'} and
                     all(v['warehouse_code'] == 'WH001' for v in report['vehicles']) and
                     route_counts == [expected_historical_routes] and
                     marker_counts == [1] and not blocked)
        return {'mode': 'r29_single_active_warehouse_preflight',
                'database_mutated': False, 'already_applied': True,
                'retired_at': retirement['retired_at'],
                'historical_route_count': route_counts[0] if route_counts else None,
                'unexpected_nonempty_dependencies': blocked,
                'state_valid': active_ok, 'warehouse': report,
                'active_warehouse_codes': ['WH001'] if active_ok else None,
                'explanation': 'WH002 仅作历史路线外键锚点，不属于现役业务仓库'}
    assessment = assess(report, expected_historical_routes=expected_historical_routes)
    return {'mode': 'r29_single_active_warehouse_preflight',
            'database_mutated': False, 'already_applied': False,
            'warehouse': report, **assessment}


def _install_write_guards(conn):
    """Prevent future operational inserts/updates using retired WH002.

    Existing route rows are preserved. Column-specific UPDATE triggers only fire
    when the warehouse FK is explicitly assigned.
    """
    conn.execute("""CREATE OR REPLACE FUNCTION public.pg_r29_guard_retired_warehouse()
      RETURNS trigger LANGUAGE plpgsql AS $guard$
      DECLARE depot_id bigint;
      BEGIN
        depot_id := (to_jsonb(NEW)->>TG_ARGV[0])::bigint;
        IF depot_id IS NOT NULL AND EXISTS
           (SELECT 1 FROM public.pg_r29_retired_warehouses
            WHERE warehouse_id=depot_id) THEN
          RAISE EXCEPTION 'r29_retired_warehouse_for_new_business:%', depot_id;
        END IF;
        RETURN NEW;
      END;
      $guard$""")
    tables = [('vehicles', 'home_warehouse_id'),
              ('routes', 'start_warehouse_id'),
              ('pg_r24_warehouse_zones', 'warehouse_id'),
              ('pg_r24_stock_lots', 'warehouse_id'),
              ('pg_r24_order_details', 'warehouse_id'),
              ('pg_r24_resources', 'warehouse_id'),
              ('pg_r24_dock_operations', 'warehouse_id'),
              ('pg_r27_work_operations', 'warehouse_id')]
    for table, column in tables:
        exists = conn.execute("""SELECT 1 FROM pg_catalog.pg_tables
            WHERE schemaname='public' AND tablename=%s""", (table,)).fetchone()
        if not exists:
            if table in ('vehicles', 'routes'):
                raise RuntimeError('r29_missing_required_table:' + table)
            continue
        # Identifiers are closed literals from this module; never from user input.
        trigger = 'pg_r29_guard_' + table
        conn.execute(f'DROP TRIGGER IF EXISTS "{trigger}" ON public."{table}"')
        conn.execute(f'''CREATE TRIGGER "{trigger}"
            BEFORE INSERT OR UPDATE OF "{column}" ON public."{table}"
            FOR EACH ROW EXECUTE FUNCTION
            public.pg_r29_guard_retired_warehouse('{column}')''')


def apply(conn, *, expected_historical_routes=4) -> dict:
    """One atomic transaction. Caller owns commit/rollback."""
    conn.execute("SET LOCAL lock_timeout='5s'")
    conn.execute("SET LOCAL statement_timeout='30s'")
    conn.execute('LOCK TABLE public.warehouses, public.vehicles, public.routes IN SHARE ROW EXCLUSIVE MODE')
    # Row locks also prevent new FK references to WH002 during preflight/apply.
    locked = conn.execute("""SELECT id,code FROM public.warehouses
                   WHERE code IN ('WH001','WH002') ORDER BY code FOR UPDATE""").fetchall()
    if len(locked) != 2:
        raise RuntimeError('r29_expected_exactly_two_warehouse_records')
    if _retirement(conn):
        raise RuntimeError('r29_already_applied_use_preflight_to_verify')
    report = inspect(conn)
    gate = assess(report, expected_historical_routes=expected_historical_routes)
    if not gate['can_apply_logical']:
        raise RuntimeError('r29_unsafe_preflight_refused:' + json.dumps(gate, ensure_ascii=False, default=str))
    ids = {r['code']: r['id'] for r in locked}
    current, retired = ids['WH001'], ids['WH002']
    conn.execute("""CREATE TABLE IF NOT EXISTS public.pg_r29_retired_warehouses (
       warehouse_id bigint PRIMARY KEY REFERENCES public.warehouses(id) ON DELETE RESTRICT,
       active_warehouse_id bigint NOT NULL REFERENCES public.warehouses(id) ON DELETE RESTRICT,
       retired_at timestamptz NOT NULL DEFAULT now(),
       reason text NOT NULL,
       CHECK (warehouse_id <> active_warehouse_id)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS public.pg_r29_active_warehouse_audit (
       audit_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
       applied_at timestamptz NOT NULL DEFAULT now(),
       historical_warehouse jsonb NOT NULL,
       previous_vehicles jsonb NOT NULL,
       untouched_historical_routes jsonb NOT NULL,
       expected_historical_routes integer NOT NULL,
       moved_vehicle_count integer NOT NULL
    )""")
    historical = conn.execute("""SELECT to_jsonb(w) AS data
        FROM public.warehouses w WHERE id=%s""", (retired,)).fetchone()['data']
    vehicles = conn.execute("""SELECT coalesce(jsonb_agg(to_jsonb(v) ORDER BY v.code),'[]'::jsonb) AS data
        FROM public.vehicles v WHERE v.home_warehouse_id=%s""", (retired,)).fetchone()['data']
    routes = conn.execute("""SELECT coalesce(jsonb_agg(to_jsonb(r) ORDER BY to_jsonb(r)::text),'[]'::jsonb) AS data
        FROM public.routes r WHERE r.start_warehouse_id=%s""", (retired,)).fetchone()['data']
    if len(vehicles) != 2 or len(routes) != expected_historical_routes:
        raise RuntimeError('r29_concurrent_or_changed_source_rows')
    moved = conn.execute('UPDATE public.vehicles SET home_warehouse_id=%s WHERE home_warehouse_id=%s',
                         (current, retired)).rowcount
    if moved != 2:
        raise RuntimeError('r29_unexpected_vehicle_update_count')
    conn.execute("""INSERT INTO public.pg_r29_retired_warehouses
        (warehouse_id,active_warehouse_id,reason)
        VALUES (%s,%s,'R29: historical routes retained; excluded from new scheduling')""",
        (retired, current))
    _install_write_guards(conn)
    conn.execute("""INSERT INTO public.pg_r29_active_warehouse_audit
      (historical_warehouse,previous_vehicles,untouched_historical_routes,
       expected_historical_routes,moved_vehicle_count)
      VALUES (%s::jsonb,%s::jsonb,%s::jsonb,%s,%s)""",
      (json.dumps(historical, default=str), json.dumps(vehicles, default=str),
       json.dumps(routes, default=str), expected_historical_routes, moved))
    result = preflight(conn, expected_historical_routes=expected_historical_routes)
    if not result.get('already_applied') or not result.get('state_valid'):
        raise RuntimeError('r29_post_migration_invariant_failed')
    route_after = next((row['count'] for row in result['warehouse']['dependent_rows']
                        if row['relation']=='public.routes' and row['column']=='start_warehouse_id'), None)
    if route_after != expected_historical_routes:
        raise RuntimeError('r29_historical_routes_changed_abort')
    return {'database_mutated': True, 'status': 'single_active_warehouse',
            'vehicles_moved': moved, 'historical_routes_preserved': route_after,
            'active_warehouse_codes': ['WH001'],
            'physical_warehouse_rows': 2,
            'retired_warehouse': 'WH002',
            'history_mode': 'original_rows_unchanged_historical_FKs_retained',
            'audit_table': AUDIT_TABLE,
            'historical_fk_anchor_not_deleted': True}


def main():
    parser = argparse.ArgumentParser(description='R29 单现役仓库：默认只读，安全保留历史路线')
    parser.add_argument('--apply', action='store_true', help='明确执行现役仓库统一事务')
    parser.add_argument('--confirm', default='', help='必须写 WH001')
    parser.add_argument('--backup-verified', action='store_true', help='已备份并核验可还原')
    parser.add_argument('--expect-routes', type=int, default=4,
                        help='预计 WH002 历史路线条数，默认采用已验收的4条')
    args = parser.parse_args()
    if args.expect_routes < 0:
        parser.error('--expect-routes must be nonnegative')
    if args.apply and (args.confirm != 'WH001' or not args.backup_verified):
        parser.error('必须同时指定 --confirm WH001 --backup-verified；请先核验完整备份')
    conn = _connection()
    try:
        if not args.apply:
            conn.execute('SET TRANSACTION READ ONLY')
            outcome = preflight(conn, expected_historical_routes=args.expect_routes)
            conn.rollback()
        else:
            outcome = apply(conn, expected_historical_routes=args.expect_routes)
            conn.commit()
        print(json.dumps({'checked_at_utc': datetime.now(timezone.utc).isoformat(), **outcome},
                         ensure_ascii=False, indent=2, default=str))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
