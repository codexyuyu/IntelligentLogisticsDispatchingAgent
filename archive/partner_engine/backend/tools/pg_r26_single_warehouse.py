"""R26 explicit WH002 -> WH001 consolidation for the legacy demo PostgreSQL DB.

Default is read-only inspection. Never run on unbacked-up production data.
Refuses migration if WH002 has dependent historical/business rows other than
vehicle home assignment; a deliberate safeguard against modifying route history
or silently reassigning stock, orders, or loading operations.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def _connection():
    from app.adapters.persistence.pg_simulation_archive import _connection as get_conn
    return get_conn()


def inspect(conn) -> dict:
    """Read-only FK inventory; no assumption that secondary warehouse is unused."""
    warehouses = conn.execute('SELECT id,code,name FROM public.warehouses ORDER BY code').fetchall()
    by_code = {row['code']: row for row in warehouses}
    vehicles = conn.execute('''SELECT v.code AS vehicle_code,w.code AS warehouse_code
        FROM public.vehicles v JOIN public.warehouses w ON w.id=v.home_warehouse_id
        ORDER BY v.code''').fetchall()
    secondary = by_code.get('WH002')
    dependent = []
    if secondary:
        fks = conn.execute('''SELECT ns.nspname AS schema_name, cls.relname AS table_name,
             a.attname AS column_name, cardinality(con.conkey) AS key_columns
          FROM pg_constraint con
          JOIN pg_class cls ON cls.oid=con.conrelid
          JOIN pg_namespace ns ON ns.oid=cls.relnamespace
          LEFT JOIN pg_attribute a ON a.attrelid=con.conrelid AND a.attnum=con.conkey[1]
          WHERE con.contype='f' AND con.confrelid='public.warehouses'::regclass''').fetchall()
        for fk in fks:
            if fk['key_columns'] != 1:
                dependent.append({'relation':f"{fk['schema_name']}.{fk['table_name']}",
                                  'column':'composite_key','count':None,'blocking':True})
                continue
            # Names are catalog-derived, double-quote escaped, never user-provided SQL.
            def q(name):
                return '"' + str(name).replace('"','""') + '"'
            query = f"SELECT count(*) AS n FROM {q(fk['schema_name'])}.{q(fk['table_name'])} WHERE {q(fk['column_name'])}=%s"
            count = conn.execute(query, (secondary['id'],)).fetchone()['n']
            is_vehicle = fk['schema_name']=='public' and fk['table_name']=='vehicles' and fk['column_name']=='home_warehouse_id'
            dependent.append({'relation':f"{fk['schema_name']}.{fk['table_name']}",
                              'column':fk['column_name'],'count':int(count),
                              'blocking':bool(count) and not is_vehicle})
    return {'target':'WH001','source':'WH002',
      'warehouse_codes':sorted(by_code), 'vehicles':vehicles,
      'source_exists': bool(secondary), 'target_exists':'WH001' in by_code,
      'dependent_rows':dependent,
      'can_apply': bool(secondary) and 'WH001' in by_code and len(by_code)==2
                   and not any(x['blocking'] for x in dependent)}


def consolidate(conn) -> dict:
    """Atomic guarded reassignment; never rewrites old saved plans or R24 rows."""
    conn.execute("SET LOCAL lock_timeout='5s'")
    conn.execute('LOCK TABLE public.warehouses, public.vehicles IN SHARE ROW EXCLUSIVE MODE')
    report=inspect(conn)
    if not report['can_apply']:
        raise RuntimeError('migration_refused_review_dependent_rows_and_wh_codes')
    current=conn.execute("SELECT id FROM public.warehouses WHERE code='WH001'").fetchone()['id']
    retired=conn.execute("SELECT id FROM public.warehouses WHERE code='WH002'").fetchone()['id']
    conn.execute('''CREATE TABLE IF NOT EXISTS public.pg_r26_single_warehouse_audit (
      migrated_at timestamptz NOT NULL DEFAULT now(),
      retired_code text NOT NULL, active_code text NOT NULL,
      retired_record jsonb NOT NULL, vehicles_before jsonb NOT NULL
    )''')
    conn.execute('''INSERT INTO public.pg_r26_single_warehouse_audit
       (retired_code,active_code,retired_record,vehicles_before)
       SELECT 'WH002','WH001',
          jsonb_build_object('id',w.id,'code',w.code,'name',w.name,
             'address',w.address,'location_wkt',ST_AsText(w.location)),
          (SELECT coalesce(jsonb_agg(jsonb_build_object('id',v.id,'code',v.code,
              'home_warehouse_id',v.home_warehouse_id)),'[]'::jsonb)
           FROM public.vehicles v WHERE v.home_warehouse_id=w.id)
       FROM public.warehouses w WHERE w.id=%s''', (retired,))
    moved=conn.execute('UPDATE public.vehicles SET home_warehouse_id=%s WHERE home_warehouse_id=%s',
                       (current,retired)).rowcount
    deleted=conn.execute('DELETE FROM public.warehouses WHERE id=%s',(retired,)).rowcount
    if deleted!=1: raise RuntimeError('warehouse_delete_count_unexpected')
    return {'warehouse_codes_after':['WH001'],'vehicles_moved':moved,'retired_rows_deleted':deleted,
            'audit_table':'public.pg_r26_single_warehouse_audit',
            'warning':'warehouse address/location and original vehicle FK saved in audit; restore from pg_dump for rollback'}


def main():
    parser=argparse.ArgumentParser(description='R26 单仓 PostgreSQL 预检（默认只读）')
    parser.add_argument('--apply',action='store_true',help='经用户确认后执行受保护的事务迁移')
    parser.add_argument('--confirm',default='',help='必须为 WH001')
    parser.add_argument('--backup-verified',action='store_true',help='确认已通过 pg_dump/pgAdmin 备份并验证')
    args=parser.parse_args()
    if args.apply and (args.confirm!='WH001' or not args.backup_verified):
        parser.error('必须同时指定 --confirm WH001 --backup-verified；先做完整数据库备份')
    conn=_connection()
    try:
        if not args.apply:
            conn.execute('SET TRANSACTION READ ONLY')
            print(json.dumps(inspect(conn),ensure_ascii=False,indent=2,default=str))
            conn.rollback()
            return
        result=consolidate(conn)
        conn.commit()
        print(json.dumps({'database_mutated':True,'timestamp_utc':datetime.now(timezone.utc).isoformat(),**result},ensure_ascii=False,indent=2))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__=='__main__':main()
