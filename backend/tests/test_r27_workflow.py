"""R27 strict PG readiness, recorded work mapping, replay order and API guards."""
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.adapters.persistence.pg_r27_workflow import (
    demo_snapshot, readiness, verified_snapshot, build_events, execute,
)
from app.adapters.persistence.pg_routing_preview import BridgeInputError
from app.main import app
from test_pg_routing_preview import ORIGIN, sample
from test_pg_r24 import metadata
from tools.pg_r27_import import read_csv


def db():
    data=sample()
    data['vehicles'] = data['vehicles'][:1]
    data['nodes'] = [n for n in data['nodes'] if n['node_key'] != 'WH:WH002']
    data['distance_matrix'] = [d for d in data['distance_matrix']
        if d['from_node'] != 'WH:WH002' and d['to_node'] != 'WH:WH002']
    data['r24']=metadata()
    data['r24']['vehicles'] = data['r24']['vehicles'][:1]
    for resource in data['r24']['resources']:
        resource.update(version=1, capacity_units=1)
    data['r24']['resources'].append({
        'warehouse_code':'WH001','resource_code':'COLD1', 'resource_kind':'cold_room',
        'temperature_zone':'chilled','capacity_units':10,'version':1,
        'available_from':ORIGIN-timedelta(hours=3), 'available_until':ORIGIN+timedelta(days=1),
    })
    data['r27']={'installed':True,'operations':[]}
    for index, code in enumerate(('ORD001','ORD002'),1):
        pick=f'PICK{index:03}'
        data['r27']['operations'].extend([
            {'operation_code':pick,'order_code':code,'warehouse_code':'WH001','resource_code':'COLD1',
             'operation_kind':'pick','duration_s':120,'release_at':ORIGIN-timedelta(minutes=30),
             'deadline_at':ORIGIN+timedelta(hours=2),'predecessor_code':None,'version':1},
            {'operation_code':f'LOAD{index:03}','order_code':code,'warehouse_code':'WH001',
             'resource_code':'DOCK1','operation_kind':'load','duration_s':180,
             'release_at':ORIGIN-timedelta(minutes=30),'deadline_at':ORIGIN+timedelta(hours=3),
             'predecessor_code':pick,'version':1},
        ])
    return data


def test_demo_snapshot_is_one_warehouse_with_operations():
    snap=demo_snapshot()
    assert len(snap.warehouses)==1
    assert len(snap.vehicles)==4
    assert len(snap.operations)>0


def test_r27_presence_check_does_not_seed_missing_pg_data():
    data=db()
    assert readiness(data)['complete_presence']
    data['r27']['operations']=[]
    status=readiness(data)
    assert not status['complete_presence']
    assert status['missing']['work_operations']==2
    with pytest.raises(BridgeInputError, match='incomplete'):
        verified_snapshot(data,temperature_zone='chilled',travel_mode='straight_line_simulation',speed_kmh=30,max_orders=20,budget_ms=5000)


def test_verified_pg_preserves_exact_work_facts_and_source_provenance():
    data=db()
    snapshot, meta=verified_snapshot(data,temperature_zone='chilled',travel_mode='straight_line_simulation',speed_kmh=30,max_orders=20,budget_ms=5000)
    assert snapshot.origin_at == ORIGIN-timedelta(days=1)
    assert len(snapshot.operations)==4 and len(snapshot.resources)==2
    assert snapshot.orders[0].source.source_kind=='database'
    assert snapshot.orders[0].volume_l==30
    assert all(x.warehouse_id=='wh_WH001' for x in snapshot.operations)
    assert any(x.operation_kind=='load' and x.resource_id=='res_DOCK1' for x in snapshot.operations)
    assert snapshot.orders[0].service_window.start_s==24*3600
    assert snapshot.rule_version=='pg-r27-verified'
    assert len(snapshot.stock_lots)==1
    assert snapshot.stock_lots[0].batch_id=='bat_L001'
    assert snapshot.stock_lots[0].on_hand_units==100


def test_wrong_resource_kind_and_precedence_fail_closed():
    data=db()
    data['r27']['operations'][1]['resource_code']='COLD1'
    with pytest.raises(BridgeInputError, match='resource_kind_mismatch'):
        verified_snapshot(data,temperature_zone='chilled',travel_mode='straight_line_simulation',speed_kmh=30,max_orders=20,budget_ms=5000)
    data=db();data['r27']['operations'][1]['predecessor_code']=None
    with pytest.raises(BridgeInputError, match='loading_must_follow'):
        verified_snapshot(data,temperature_zone='chilled',travel_mode='straight_line_simulation',speed_kmh=30,max_orders=20,budget_ms=5000)


def test_cross_order_dependency_rejected():
    data=db()
    data['r27']['operations'][1]['predecessor_code']='PICK002'
    with pytest.raises(BridgeInputError, match='cross_order'):
        verified_snapshot(data,temperature_zone='chilled',travel_mode='straight_line_simulation',speed_kmh=30,max_orders=20,budget_ms=5000)


def test_migration_and_csv_are_explicit_and_non_destructive(tmp_path):
    path=tmp_path/'operations.csv'
    from tools.pg_r27_import import COLUMNS
    path.write_text(','.join(COLUMNS)+'\n', encoding='utf8')
    with pytest.raises(ValueError,match='no_operations'):
        read_csv(path)
    path.write_text(','.join(COLUMNS)+'\nOP1,ORD001,WH001,COLD1,pick,180,2026-10-18T06:00:00+00:00,2026-10-18T09:00:00+00:00,,2026-10-17T12:00:00+00:00\n',encoding='utf8')
    assert len(read_csv(path))==1
    with patch.dict('os.environ', {'PG_DEMO_ENABLED':'1'}):
        client=TestClient(app)
        bad=client.post('/local-pg/pg-preview/r27/workflow',json={'source':'single_warehouse_demo'})
        assert bad.status_code==422
        with patch('app.api.routes.postgres_demo.load_view_data', return_value=db()):
            state=client.get('/local-pg/pg-preview/r27/readiness')
            assert state.status_code==200
            assert state.json()['single_warehouse'] is True


def test_events_are_chronological_and_link_handoff_to_departure():
    snap=demo_snapshot()
    a=snap.orders[0]
    from app.contracts.planning import WarehouseHandoff, RouteStop, VehicleRoute
    from app.contracts.entities import ScheduledOperation
    from app.contracts.common import ValidationReport
    work=SimpleNamespace(operation_id=snap.operations[0].operation_id,resource_id=snap.resources[0].resource_id,start_s=100,end_s=180)
    h=SimpleNamespace(order_id=a.order_id,warehouse_id=a.warehouse_id,ready_at_s=180)
    stop0=SimpleNamespace(stop_kind='depot_start',departure_at_s=200,arrival_at_s=200,order_ids=())
    stop1=SimpleNamespace(stop_kind='delivery',departure_at_s=320,arrival_at_s=300,order_ids=(a.order_id,))
    stop2=SimpleNamespace(stop_kind='depot_end',arrival_at_s=400,departure_at_s=400,order_ids=())
    route=SimpleNamespace(vehicle_id=snap.vehicles[0].vehicle_id,stops=(stop0,stop1,stop2))
    plan=SimpleNamespace(validation=SimpleNamespace(status='passed'),warehouse=SimpleNamespace(operations=[work],warehouse_handoffs=[h]),routing=SimpleNamespace(routes=[route]))
    events=build_events(snap,plan)
    assert [e['time_s'] for e in events] == sorted(e['time_s'] for e in events)
    assert {e['kind'] for e in events} == {'warehouse_work_start','warehouse_work_finished','loading_ready','vehicle_departure','order_delivered','vehicle_return'}
    assert events.index(next(e for e in events if e['kind']=='loading_ready')) < events.index(next(e for e in events if e['kind']=='vehicle_departure'))


def test_independent_validator_rejects_r27_illegal_resource_swap():
    from app.adapters.warehouse.validator import WarehouseScheduleValidator
    from app.contracts.planning import WarehouseScheduleRequest, WarehouseScheduleResult
    from app.contracts.entities import ScheduledOperation
    from app.contracts.common import SolveMetadata
    snap,_=verified_snapshot(db(),temperature_zone='chilled',travel_mode='straight_line_simulation',speed_kmh=30,max_orders=20,budget_ms=5000)
    work=snap.operations[0]
    swapped=next(r for r in snap.resources if r.resource_id != work.resource_id)
    item=ScheduledOperation(operation_id=work.operation_id,resource_id=swapped.resource_id,
                            start_s=work.release_at_s,end_s=work.release_at_s+work.duration_s)
    result=WarehouseScheduleResult(snapshot_id=snap.snapshot_id,snapshot_version=snap.version,
        metadata=SolveMetadata(status='feasible',raw_status='MOCK',engine='test',engine_version='0',
            has_solution=True,proof_scope='unit test only',solve_ms=0),
        operations=(item,),warehouse_handoffs=())
    req=WarehouseScheduleRequest(snapshot=snap,order_ids=tuple(o.order_id for o in snap.orders),
        budget={'remaining_ms':5000})
    check=WarehouseScheduleValidator().validate(req,result)
    assert check.status=='failed'
    assert any(v.rule_id=='warehouse.verified_resource_binding' for v in check.violations)
