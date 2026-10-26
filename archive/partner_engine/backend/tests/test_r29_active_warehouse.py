"""R29: historical FK preservation and one active warehouse, no live DB required."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from tools.pg_r29_active_warehouse import assess, preflight, apply
from app.adapters.persistence.pg_routing_preview import load_view_data, BridgeInputError, _distance_lookup
from app.main import app


def report(*, routes=4, vehicles=2, extra=0, warehouse_codes=None):
    return {'target': 'WH001', 'source': 'WH002',
            'warehouse_codes': warehouse_codes or ['WH001', 'WH002'],
            'target_exists': True, 'source_exists': True,
            'vehicles': [{'vehicle_code': f'V{i:03}', 'warehouse_code': 'WH001' if i <= 2 else 'WH002'}
                         for i in range(1,5)],
            'dependent_rows': [
                {'relation': 'public.vehicles', 'column': 'home_warehouse_id',
                 'count': vehicles, 'blocking': False},
                {'relation': 'public.routes', 'column': 'start_warehouse_id',
                 'count': routes, 'blocking': routes > 0},
                {'relation': 'public.pg_r24_stock_lots', 'column': 'warehouse_id',
                 'count': extra, 'blocking': extra > 0}]}


def test_known_historical_routes_do_not_block_logical_retirement():
    value = assess(report())
    assert value['can_apply_logical']
    assert value['historical_route_count'] == 4
    assert value['active_warehouse_codes_after'] == ['WH001']
    assert value['physical_warehouse_rows_after'] == 2


@pytest.mark.parametrize('kwargs', [
    {'routes': 3}, {'routes': 5}, {'vehicles': 3}, {'extra': 1},
    {'warehouse_codes': ['WH001', 'WH002', 'WH003']},
])
def test_drift_or_new_business_dependencies_refused(kwargs):
    assert not assess(report(**kwargs))['can_apply_logical']


def test_unknown_nonempty_fk_refused_even_when_the_original_four_routes_match():
    actual = report()
    actual['dependent_rows'].append({'relation': 'public.other_sensitive_table',
                                     'column': 'warehouse_id', 'count': 1, 'blocking': True})
    assert not assess(actual)['can_apply_logical']
    actual['dependent_rows'][-1]['count'] = None
    assert not assess(actual)['can_apply_logical']


class FakeReadConn:
    def __init__(self, marker: bool, *, malformed=False):
        self.marker = marker
        self.malformed = malformed
        self.calls = []
        self.data = []
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def execute(self, query, params=None):
        self.calls.append(str(query).strip())
        if 'FROM v_dispatch_orders' in query:
            self.data = [{'order_code': 'ORD001', 'customer_code':'C001'}]
        elif 'FROM v_dispatch_vehicles' in query:
            self.data = [{'vehicle_code': f'V{i:03}', 'warehouse_code':'WH001'} for i in range(1,5)]
        elif 'FROM v_dispatch_nodes' in query:
            self.data = [{'node_key': key} for key in ('WH:WH001', 'WH:WH002', 'C:C001')]
        elif 'FROM v_dispatch_distance_matrix' in query:
            nodes = ('WH:WH001', 'WH:WH002', 'C:C001')
            self.data = [{'from_node': a, 'to_node': b, 'distance_m': Decimal(0 if a == b else 1000)}
                         for a in nodes for b in nodes]
        elif 'FROM pg_catalog.pg_tables' in query:
            self.data = [(1,)] if self.marker else []
        elif 'FROM public.pg_r29_retired_warehouses r' in query:
            self.data = [{'retired_code': 'WH002', 'active_code': 'WH003' if self.malformed else 'WH001'}]
        else:
            self.data = []
        return self
    def fetchall(self): return self.data
    def fetchone(self): return self.data[0] if self.data else None


def test_read_adapter_keeps_unmigrated_database_unchanged():
    data = load_view_data(lambda: FakeReadConn(marker=False))
    assert len(data['nodes']) == 3 and len(data['distance_matrix']) == 9
    assert 'r29_active_depot' not in data


def test_read_adapter_only_excludes_retired_warehouse_and_its_matrix_pairs():
    conn = FakeReadConn(marker=True)
    data = load_view_data(lambda: conn)
    assert {n['node_key'] for n in data['nodes']} == {'WH:WH001','C:C001'}
    assert len(data['distance_matrix']) == 4
    assert data['r29_active_depot']['retired_historical_fk_warehouse'] == 'WH002'
    assert _distance_lookup(data)['WH:WH001','C:C001'] == 1000
    assert all(x.strip().upper().startswith(('SELECT', 'SET')) for x in conn.calls)


def test_inconsistent_marker_must_fail_closed():
    with pytest.raises(BridgeInputError, match='marker_inconsistent'):
        load_view_data(lambda: FakeReadConn(marker=True, malformed=True))


def test_preflight_reports_historical_only_marker_without_mutating_database():
    class Conn:
        def execute(self, query, *_):
            assert 'SELECT' in query
            return self
        def fetchone(self): return None
    with patch('tools.pg_r29_active_warehouse.inspect', return_value=report()):
        value = preflight(Conn())
    assert value['can_apply_logical'] and not value['database_mutated']


def test_apply_fails_closed_before_creating_any_tables_if_unknown_fks():
    class Conn:
        def __init__(self): self.queries = []
        def execute(self, query, *_):
            self.queries.append(query)
            return self
        def fetchall(self): return [{'id':1,'code':'WH001'}, {'id':2,'code':'WH002'}]
        def fetchone(self): return None
    conn=Conn()
    with patch('tools.pg_r29_active_warehouse.inspect', return_value=report(extra=1)):
        with pytest.raises(RuntimeError, match='unsafe_preflight_refused'):
            apply(conn)
    assert not any('CREATE TABLE' in q for q in conn.queries)
    assert not any('UPDATE public.vehicles' in q for q in conn.queries)
    assert not any('DELETE' in q.upper() for q in conn.queries)


def test_endpoint_summary_exposes_explicit_historical_fk_caveat(monkeypatch):
    monkeypatch.setenv('PG_DEMO_ENABLED','1')
    sample={'orders': [{} for _ in range(20)],
            'vehicles':[{'warehouse_code':'WH001'} for _ in range(4)],
            'nodes':[{'node_key':'WH:WH001'}]+[{'node_key':f'C:C{i:03}'} for i in range(20)],
            'distance_matrix':[{} for _ in range(441)],
            'r29_active_depot':{'active_warehouses':['WH001'],
                'retired_historical_fk_warehouse':'WH002',
                'physical_historical_warehouse_retained':True}}
    with patch('app.api.routes.postgres_demo.load_view_data', return_value=sample):
        response=TestClient(app).get('/local-pg/pg-preview/summary')
    assert response.status_code == 200
    val=response.json()
    assert val['r26_single_warehouse_ready']
    assert val['r29_active_warehouse']['physical_historical_warehouse_retained']
    assert (val['orders'],val['vehicles'],val['nodes'],val['distance_pairs']) == (20,4,21,441)


def test_apply_success_path_updates_only_vehicle_fks_and_preserves_routes():
    before=report()
    after=report(vehicles=0)
    for vehicle in after['vehicles']:
        vehicle['warehouse_code'] = 'WH001'
    after['dependent_rows'].append({
        'relation': 'public.pg_r29_retired_warehouses', 'column': 'warehouse_id',
        'count':1,'blocking':True})
    class FakeResult:
        def __init__(self, rows=None, rowcount=0):
            self.rows=rows or []
            self.rowcount=rowcount
        def fetchall(self): return self.rows
        def fetchone(self): return self.rows[0] if self.rows else None
    class Conn:
        def __init__(self): self.sql=[]
        def execute(self, query, params=None):
            self.sql.append(str(query))
            if 'FOR UPDATE' in query:
                return FakeResult([{'id':1,'code':'WH001'}, {'id':2,'code':'WH002'}])
            if 'SELECT to_jsonb(w) AS data' in query:
                return FakeResult([{'data':{'id':2,'code':'WH002','name':'historic'}}])
            if 'FROM public.vehicles v WHERE v.home_warehouse_id' in query:
                return FakeResult([{'data':[{'id':3,'code':'V003'}, {'id':4,'code':'V004'}]}])
            if 'FROM public.routes r WHERE r.start_warehouse_id' in query:
                return FakeResult([{'data':[{'id':i} for i in range(1,5)]}])
            if 'UPDATE public.vehicles SET home_warehouse_id' in query:
                return FakeResult(rowcount=2)
            if 'SELECT 1 FROM pg_catalog.pg_tables' in query:
                return FakeResult([{'?column?':1}])
            return FakeResult()
    conn=Conn()
    with patch('tools.pg_r29_active_warehouse.inspect', side_effect=[before,after]), \
         patch('tools.pg_r29_active_warehouse._retirement', side_effect=[None, {'active_code':'WH001', 'retired_at':datetime.now(timezone.utc)}]):
        status=apply(conn)
    assert status['vehicles_moved']==2
    assert status['historical_routes_preserved']==4
    assert status['physical_warehouse_rows']==2
    assert any('INSERT INTO public.pg_r29_active_warehouse_audit' in x for x in conn.sql)
    assert any('pg_r29_guard_retired_warehouse' in x for x in conn.sql)
    assert not any('UPDATE public.routes' in x or 'DELETE FROM public.routes' in x or
                   'DELETE FROM public.warehouses' in x for x in conn.sql)
