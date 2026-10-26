"""R26 safe single-depot scenario and guarded PostgreSQL consolidation."""
from __future__ import annotations

from pathlib import Path
import json

import pytest

from app.contracts.entities import PlanningSnapshot
from tools.pg_r26_single_warehouse import inspect

ROOT=Path(__file__).resolve().parents[2]


def test_new_scenario_is_a_single_depot_without_losing_orders():
    old=json.loads((ROOT/'data/scenarios/two_warehouses_20_orders.json').read_text(encoding='utf-8'))
    new=json.loads((ROOT/'data/scenarios/single_warehouse_20_orders.json').read_text(encoding='utf-8'))
    parsed=PlanningSnapshot.model_validate(new)
    assert len(parsed.warehouses)==1
    assert parsed.warehouses[0].warehouse_id=='wh_1'
    assert len(parsed.orders)==20 and len(parsed.vehicles)==4
    assert {order.order_id for order in parsed.orders}=={x['order_id'] for x in old['orders']}
    for name in ('orders','vehicles','stock_lots','resources','operations'):
        assert all(x['warehouse_id']=='wh_1' for x in new[name])
    assert all(vehicle.start_node_id=='node_wh1' and vehicle.end_node_id=='node_wh1' for vehicle in parsed.vehicles)
    assert 'node_wh2' not in parsed.matrix.node_ids
    assert len(parsed.matrix.node_ids)==21
    assert all(len(row)==21 for row in parsed.matrix.duration_s)
    # All non-depot customer distances, capacities and time windows are unchanged.
    index_old={key:i for i,key in enumerate(old['matrix']['node_ids'])}
    for i,a in enumerate(parsed.matrix.node_ids):
        for j,b in enumerate(parsed.matrix.node_ids):
            assert parsed.matrix.duration_s[i][j]==old['matrix']['duration_s'][index_old[a]][index_old[b]]
            assert parsed.matrix.distance_m[i][j]==old['matrix']['distance_m'][index_old[a]][index_old[b]]
    assert len({r.resource_id for r in parsed.resources})==len(parsed.resources)
    assert set(v.warehouse_id for v in parsed.vehicles)=={'wh_1'}


def test_frontend_and_backend_default_snapshot_identical():
    paths=[ROOT/'frontend/public/scenarios/single_warehouse_20_orders.json',ROOT/'data/scenarios/single_warehouse_20_orders.json']
    assert json.loads(paths[0].read_text(encoding='utf-8'))==json.loads(paths[1].read_text(encoding='utf-8'))


class FakeConn:
    def __init__(self, *, count=0):
        self.count=count;self.calls=[]
    def execute(self,sql,params=None):
        self.calls.append((str(sql),params))
        if 'FROM public.warehouses ORDER BY' in str(sql):return FakeRows([{'id':1,'code':'WH001','name':'main'},{'id':2,'code':'WH002','name':'historic'}])
        if 'FROM public.vehicles v JOIN' in str(sql):return FakeRows([{'vehicle_code':'V001','warehouse_code':'WH001'},{'vehicle_code':'V002','warehouse_code':'WH002'}])
        if 'pg_constraint con' in str(sql):return FakeRows([{'schema_name':'public','table_name':'vehicles','column_name':'home_warehouse_id','key_columns':1},
                                                           {'schema_name':'public','table_name':'routes','column_name':'start_warehouse_id','key_columns':1}])
        if 'count(*) AS n' in str(sql):
            return FakeRows([{'n':self.count if 'routes' in str(sql) else 1}])
        raise AssertionError(f'unexpected query: {sql}')


class FakeRows:
    def __init__(self,rows):self.rows=rows
    def fetchall(self):return self.rows
    def fetchone(self):return self.rows[0]


def test_migration_preflight_is_readonly_and_blocks_historical_routes():
    conn=FakeConn(count=3)
    outcome=inspect(conn)
    assert outcome['can_apply'] is False
    assert any(dep['blocking'] for dep in outcome['dependent_rows'])
    assert all(str(query).lower().strip().startswith('select') for query,_ in conn.calls)


def test_migration_preflight_allows_only_known_unreferenced_wh2():
    conn=FakeConn(count=0)
    outcome=inspect(conn)
    assert outcome['can_apply'] is True
    assert len(outcome['vehicles'])==2
    assert all(not dep['blocking'] for dep in outcome['dependent_rows'])
