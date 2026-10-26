"""R28 fail-closed reconciliation and read-only fact intake tests.

These are contract-independent component tests; live CP-SAT/OR-Tools integration
remains a Windows acceptance task whenever those optional packages are absent.
"""
from types import SimpleNamespace as Obj

import pytest

from app.adapters.persistence.pg_r28_reconciliation import ReconciliationError, reconcile
from app.adapters.persistence.pg_r28_diagnostics import diagnostics
from tools.pg_r28_prepare import operator_worklists, export_worklists
from test_r27_workflow import db


def sample_plan():
    snapshot = Obj(
        orders=[Obj(order_id='ord_1'), Obj(order_id='ord_2')],
        operations=[Obj(operation_id='op_1', order_ids=('ord_1',)), Obj(operation_id='op_2', order_ids=('ord_2',))],
    )
    warehouse = Obj(
        operations=[Obj(operation_id='op_1', end_s=90), Obj(operation_id='op_2', end_s=140)],
        warehouse_handoffs=[Obj(order_id='ord_1', ready_at_s=100), Obj(order_id='ord_2', ready_at_s=150)],
    )
    routes = [Obj(vehicle_id='veh_1', stops=[
        Obj(stop_kind='depot_start', departure_at_s=200, order_ids=()),
        Obj(stop_kind='delivery', departure_at_s=340, order_ids=('ord_1',)),
        Obj(stop_kind='delivery', departure_at_s=510, order_ids=('ord_2',)),
        Obj(stop_kind='depot_end', departure_at_s=600, order_ids=()),
    ])]
    plan = Obj(warehouse=warehouse,routing=Obj(routes=routes,unserved_orders=[]))
    events = [{'kind':'loading_ready','object_id':'ord_1'}, {'kind':'loading_ready','object_id':'ord_2'},
              {'kind':'vehicle_departure','object_id':'veh_1'},
              {'kind':'order_delivered','object_id':'ord_1'}, {'kind':'order_delivered','object_id':'ord_2'},
              {'kind':'vehicle_return','object_id':'veh_1'}]
    return snapshot, plan, events


def test_full_plan_and_playback_are_distinct_counts():
    snap, plan, events = sample_plan()
    summary = reconcile(snap,plan,events)
    assert summary['scope_order_count']==2
    assert summary['planned_delivery_order_count']==2
    assert summary['unserved_order_count']==0
    assert [x['planned_delivery_at_s'] for x in summary['order_statuses']]==[340,510]
    assert [x['planned_vehicle_id'] for x in summary['order_statuses']]==['veh_1','veh_1']
    # At clock 400, only one of the two planned deliveries has occurred.
    assert sum(x['planned_delivery_at_s']<=400 for x in summary['order_statuses'])==1




def test_reconciliation_rejects_missing_undisclosed_order():
    snap,plan,events=sample_plan()
    plan.routing.routes[0].stops.pop(2)
    events=[x for x in events if x['object_id']!='ord_2' or x['kind']=='loading_ready']
    with pytest.raises(ReconciliationError,match='unaccounted_orders'):
        reconcile(snap,plan,events)


def test_reconciliation_rejects_duplicate_or_phantom_delivery():
    snap,plan,events=sample_plan()
    plan.routing.routes[0].stops[1].order_ids=('ord_1','ord_1')
    with pytest.raises(ReconciliationError,match='duplicate_route_deliveries'):
        reconcile(snap,plan,events)
    snap,plan,events=sample_plan()
    events.append({'kind':'order_delivered','object_id':'ord_999'})
    with pytest.raises(ReconciliationError,match='event_delivery_mismatch'):
        reconcile(snap,plan,events)


def test_reconciliation_rejects_departure_before_all_loads_ready():
    snap,plan,events=sample_plan()
    plan.routing.routes[0].stops[0].departure_at_s=149
    with pytest.raises(ReconciliationError,match='departure_before_loading_ready'):
        reconcile(snap,plan,events)


def test_reconciliation_rejects_missing_or_repeated_handoff_and_events():
    snap,plan,events=sample_plan()
    plan.warehouse.warehouse_handoffs.pop()
    with pytest.raises(ReconciliationError,match='unknown_or_duplicate_handoffs'):
        reconcile(snap,plan,events)
    snap,plan,events=sample_plan()
    events=[x for x in events if x['kind']!='vehicle_return']
    with pytest.raises(ReconciliationError,match='vehicle_return_event_mismatch'):
        reconcile(snap,plan,events)


def test_database_readiness_and_fk_blockers_are_visible():
    data=db()
    status=diagnostics(data,{'warehouse_codes':['WH001','WH002'],'can_apply':False,'dependent_rows':[
        {'relation':'public.routes','column':'warehouse_id','count':2,'blocking':True}]})
    assert status['database_mutated'] is False
    assert status['ready_to_try_verified_solver']
    assert status['warehouse']['dependent_rows'][0]['blocking']
    data['r24']['orders']=[]
    assert not diagnostics(data, status['warehouse'])['ready_to_try_verified_solver']


def test_csv_operator_worklists_use_only_real_ids_no_fake_business_values(tmp_path):
    data=db()
    data['r24']['orders'] = data['r24']['orders'][:1]
    data['r24']['vehicles']=[]
    data['r27']['operations']=[]
    lists=operator_worklists(data)
    assert lists['orders'][1][0]['order_code']=='ORD002'
    assert lists['orders'][1][0]['volume_l']==''
    assert lists['vehicles'][1][0]['vehicle_code']=='V001'
    assert lists['vehicles'][1][0]['capacity_volume_l']==''
    assert len(lists['work_operations'][1])==2
    assert lists['work_operations'][1][0]['duration_s']==''
    assert lists['zones'][1]==[]
    counts=export_worklists(data,tmp_path/'empty')
    assert counts['orders']==1
    from tools.r24_import_csv import read_rows
    with pytest.raises(ValueError,match='empty_field'):
        read_rows('orders', tmp_path/'empty/orders.csv')
    with pytest.raises(ValueError,match='r28_output_directory_must_be_empty'):
        export_worklists(data,tmp_path/'empty')


def test_r28_diagnostics_http_returns_readonly_blockers_without_pg_writes():
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from app.main import app

    class ReadonlyConnection:
        def __init__(self):
            self.queries=[]
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def execute(self, query, *args):
            self.queries.append(str(query))
        def rollback(self): pass

    conn=ReadonlyConnection()
    warehouse={'warehouse_codes':['WH001','WH002'], 'can_apply':False, 'dependent_rows':[
        {'relation':'public.route_stops','column':'warehouse_id','count':7,'blocking':True}]}
    with patch.dict('os.environ', {'PG_DEMO_ENABLED':'1'}), \
         patch('app.api.routes.postgres_demo.load_view_data', return_value=db()), \
         patch('app.adapters.persistence.pg_simulation_archive._connection', return_value=conn), \
         patch('tools.pg_r26_single_warehouse.inspect', return_value=warehouse):
        response=TestClient(app).get('/local-pg/pg-preview/r28/diagnostics')
    assert response.status_code==200
    body=response.json()
    assert body['database_mutated'] is False
    assert body['business']['complete_presence']
    assert body['warehouse']['dependent_rows'][0]['count']==7
    assert conn.queries==['SET TRANSACTION READ ONLY']


def test_r28_no_approval_means_no_postgres_access():
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from app.main import app
    with patch.dict('os.environ', {'PG_DEMO_ENABLED':'0'}), \
         patch('app.api.routes.postgres_demo.load_view_data', side_effect=AssertionError('should_not_reach_db')):
        response=TestClient(app).get('/local-pg/pg-preview/r28/diagnostics')
        assert response.status_code==503


def test_reconciliation_checks_warehouse_tasks_and_ready_timestamps():
    snap,plan,events=sample_plan()
    plan.warehouse.operations.pop()
    with pytest.raises(ReconciliationError,match='scheduled_warehouse_operations_mismatch'):
        reconcile(snap,plan,events)
    snap,plan,events=sample_plan()
    plan.warehouse.warehouse_handoffs[1].ready_at_s=130
    with pytest.raises(ReconciliationError,match='handoff_before_warehouse_operations_finished'):
        reconcile(snap,plan,events)
