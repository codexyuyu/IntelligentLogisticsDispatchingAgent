"""R30-B: verify durable event boundaries without requiring a live Windows PG.

The historical R19 candidate is REAL accepted solver evidence (no new claim of
solving in this environment). Fake solvers exercise orchestration/wiring; the
actual CP-SAT/OR-Tools suffix still requires dependency-backed Windows checks.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.adapters.persistence.pg_r27_workflow import build_events
from app.adapters.persistence.pg_r30b_reschedule import (
    ExceptionSpec, RescheduleInputError, _location_at, run_reschedule,
)
from app.contracts.entities import PlanningSnapshot
from app.contracts.planning import (
    CandidatePlan, RoutingResult, RouteStop, VehicleArrival, VehicleRoute,
    WarehouseScheduleResult, UnservedOrder,
)

BASE = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def accepted_baseline():
    snap = PlanningSnapshot.model_validate(json.loads((BASE / 'benchmarks/b04/r19_accepted_v2/scenarios/s12_seed17__base.json').read_text()))
    raw = json.loads((BASE / 'benchmarks/b04/r19_accepted_v2/raw/s12_seed17__base_arms.json').read_text())
    plan = CandidatePlan.model_validate(raw['baseline']['candidate_plan'])
    return {'snapshot':snap.model_dump(mode='json'),'plan':plan.model_dump(mode='json'),
            'events':build_events(snap,plan),'source':'scenario_demo','meta':{'business_facts':'all_synthetic'}}


def test_vehicle_breakdown_does_not_teleport_or_redeliver(one_warehouse_baseline):
    result=run_reschedule(baseline=one_warehouse_baseline,
        spec=ExceptionSpec(event_type='vehicle_breakdown',object_id='veh_1',occurred_at_s=3500))
    assert result['verification']['status']=='passed'
    assert result['database_mutated'] is False
    assert result['new_plan_version']==result['previous_plan_version']+1
    assert result['comparison']['delivered_before_event']>=1
    assert {'ord_001','ord_002'} <= {o['order_id'] for o in result['comparison']['unserved_orders']}
    assert 'ord_003' in result['state']['completed_order_ids']
    assert result['state']['halted_vehicle_positions']['veh_1']['state']=='in_transit_between_nodes'
    assert all(not (x['object_id']=='ord_003' and x['time_s']>3500)
               for x in result['replay']['events'] if x['kind']=='order_delivered')
    assert result['replay']['halted_vehicles']['veh_1']['from_s']==3500
    assert [x for x in one_warehouse_baseline['events'] if x['time_s']<=3500] == [
        x for x in result['replay']['events'] if x['time_s']<=3500 and x['kind']!='exception_occurred']


def test_delivery_delay_changes_actual_delivery_predictions(one_warehouse_baseline):
    result=run_reschedule(baseline=one_warehouse_baseline,
        spec=ExceptionSpec(event_type='delivery_delay',object_id='veh_1',occurred_at_s=3500,delay_s=600))
    assert result['verification']['status']=='passed'
    assert result['comparison']['unserved_total']==0
    changes={x['order_id']:x for x in result['comparison']['order_changes']}
    assert changes['ord_003']['status']=='completed_before_event'
    assert changes['ord_003']['new_delivery_at_s']==changes['ord_003']['previous_delivery_at_s']
    assert changes['ord_002']['new_delivery_at_s'] > changes['ord_002']['previous_delivery_at_s']


def test_invalid_ids_and_times_rejected(one_warehouse_baseline):
    for event in (ExceptionSpec(event_type='vehicle_breakdown',object_id='veh_missing',occurred_at_s=900),
                  ExceptionSpec(event_type='inventory_quarantine',object_id='batch_missing',occurred_at_s=100),
                  ExceptionSpec(event_type='delivery_delay',object_id='veh_1',occurred_at_s=100,delay_s=0),
                  ExceptionSpec(event_type='vehicle_breakdown',object_id='veh_1',occurred_at_s=999999)):
        with pytest.raises(RescheduleInputError):
            run_reschedule(baseline=one_warehouse_baseline,spec=event)


def test_original_plan_fails_closed_if_tampered(one_warehouse_baseline):
    dirty={**one_warehouse_baseline,'events':one_warehouse_baseline['events'][:-1]}
    with pytest.raises(Exception):
        run_reschedule(baseline=dirty,
            spec=ExceptionSpec(event_type='vehicle_breakdown',object_id='veh_1',occurred_at_s=3500))




@pytest.fixture(scope='module')
def one_warehouse_baseline(accepted_baseline):
    # R19 was a historical two-warehouse acceptance case. Scope a self-consistent
    # WH1-only validated subset to test today's single-depot R30-B suffix.
    src=PlanningSnapshot.model_validate(accepted_baseline['snapshot'])
    plan=CandidatePlan.model_validate(accepted_baseline['plan'])
    wh='wh_1'
    orders=tuple(o for o in src.orders if o.warehouse_id==wh)
    ids={o.order_id for o in orders}
    works=tuple(o for o in src.operations if o.warehouse_id==wh)
    snap=src.model_copy(update={
        'orders':orders,'vehicles':tuple(v for v in src.vehicles if v.warehouse_id==wh),
        'warehouses':tuple(w for w in src.warehouses if w.warehouse_id==wh),
        'resources':tuple(r for r in src.resources if r.warehouse_id==wh),
        'stock_lots':tuple(l for l in src.stock_lots if l.warehouse_id==wh),
        'operations':works,
    })
    whop_ids={o.operation_id for o in works}
    warehouse=plan.warehouse.model_copy(update={
        'operations':tuple(o for o in plan.warehouse.operations if o.operation_id in whop_ids),
        'warehouse_handoffs':tuple(h for h in plan.warehouse.warehouse_handoffs if h.order_id in ids),
    })
    vehicle_ids={v.vehicle_id for v in snap.vehicles}
    routing=plan.routing.model_copy(update={
        'routes':tuple(r for r in plan.routing.routes if r.vehicle_id in vehicle_ids),
        'warehouse_arrivals':tuple(r for r in plan.routing.warehouse_arrivals if r.vehicle_id in vehicle_ids),
        'unserved_orders':tuple(u for u in plan.routing.unserved_orders if u.order_id in ids),
    })
    next_plan=plan.model_copy(update={'warehouse':warehouse,'routing':routing})
    return {'snapshot':snap.model_dump(mode='json'),'plan':next_plan.model_dump(mode='json'),
            'events':build_events(snap,next_plan),'source':'scenario_demo'}


class StubWarehouse:
    def __init__(self, baseline):
        self.plan=CandidatePlan.model_validate(baseline['plan'])
    def schedule(self, request):
        ids=set(request.order_ids)
        operations={op.operation_id for op in request.snapshot.operations}
        operations=tuple(x for x in self.plan.warehouse.operations if x.operation_id in operations)
        handoffs=tuple(x for x in self.plan.warehouse.warehouse_handoffs if x.order_id in ids)
        return WarehouseScheduleResult(snapshot_id=request.snapshot.snapshot_id,
             snapshot_version=request.snapshot.version,metadata=self.plan.warehouse.metadata,
             operations=operations,warehouse_handoffs=handoffs)


class StubRoutingAllExplicitlyUnserved:
    """Valid transport format with no deliveries; no success claimed for a route."""
    def solve(self, request):
        routes=[]
        arrivals=[]
        wh_nodes={w.warehouse_id:w.node_id for w in request.snapshot.warehouses}
        for vehicle in request.snapshot.vehicles:
            node=wh_nodes[vehicle.warehouse_id]
            at=vehicle.available_at_s
            start=RouteStop(node_id=node,order_ids=(),stop_kind='depot_start',arrival_at_s=at,
                service_start_at_s=at,departure_at_s=at,load_weight_kg=0,load_volume_l=0)
            end=RouteStop(node_id=node,order_ids=(),stop_kind='depot_end',arrival_at_s=at,
                service_start_at_s=at,departure_at_s=at,load_weight_kg=0,load_volume_l=0)
            routes.append(VehicleRoute(vehicle_id=vehicle.vehicle_id,stops=(start,end),distance_m=0,duration_s=0))
            arrivals.append(VehicleArrival(vehicle_id=vehicle.vehicle_id,
                warehouse_id=vehicle.warehouse_id,arrival_at_s=at,order_ids=()))
        return RoutingResult(snapshot_id=request.snapshot.snapshot_id,snapshot_version=request.snapshot.version,
            metadata={'status':'feasible','raw_status':'TEST_STUB_EXPLICITLY_UNSERVED',
                      'has_solution':True,'engine':'stub','engine_version':'test',
                      'proof_scope':'test-double-only','solve_ms':1},
            routes=tuple(routes),warehouse_arrivals=tuple(arrivals),
            unserved_orders=tuple(UnservedOrder(order_id=o,reason_code='no_transport_capacity') for o in request.order_ids))


def test_warehouse_fault_removes_future_resource_tasks_and_calls_suffix_scheduler(one_warehouse_baseline):
    res=run_reschedule(baseline=one_warehouse_baseline,
        spec=ExceptionSpec(event_type='warehouse_resource_failure',object_id='res_dock1',occurred_at_s=80),
        warehouse_solver=StubWarehouse(one_warehouse_baseline),routing_solver=StubRoutingAllExplicitlyUnserved())
    assert res['verification']['status']=='passed'
    assert res['state']['interrupted_operation_ids']
    assert res['comparison']['unserved_total']>0
    assert res['solver']['warehouse_status'] not in ('no_pending_warehouse_work',)
    assert res['database_mutated'] is False
    assert all(x['resource_id']!='res_dock1' for x in res['comparison']['changed_warehouse_operations'])


def test_quarantine_blocks_unpicked_stock_and_keeps_history(one_warehouse_baseline):
    res=run_reschedule(baseline=one_warehouse_baseline,
        spec=ExceptionSpec(event_type='inventory_quarantine',object_id='batch_001',occurred_at_s=80),
        warehouse_solver=StubWarehouse(one_warehouse_baseline),routing_solver=StubRoutingAllExplicitlyUnserved())
    assert any(x['order_id']=='ord_001' and 'quarantined' in x['reason_code']
               for x in res['comparison']['unserved_orders'])
    assert res['comparison']['forecast_delivered_total']+res['comparison']['unserved_total']==6
    assert res['verification']['status']=='passed'



def test_quarantined_batch_interrupts_active_warehouse_operation(one_warehouse_baseline):
    out = run_reschedule(baseline=one_warehouse_baseline,
        spec=ExceptionSpec(event_type='inventory_quarantine',object_id='batch_001',occurred_at_s=100),
        warehouse_solver=StubWarehouse(one_warehouse_baseline),
        routing_solver=StubRoutingAllExplicitlyUnserved())
    assert out['verification']['status']=='passed'
    assert 'op_load001' in out['state']['interrupted_operation_ids']
    assert any(e['object_id']=='op_load001' and e['kind']=='warehouse_work_start' and e['time_s']==60
               for e in out['replay']['events'])
    assert not any(e['object_id']=='op_load001' and e['kind']=='warehouse_work_finished' and e['time_s']>100
               for e in out['replay']['events'])
    assert 'ord_001' in {o['order_id'] for o in out['comparison']['unserved_orders']}


def test_endpoint_is_local_and_opt_in(monkeypatch):
    client=TestClient(app)
    monkeypatch.delenv('PG_DEMO_ENABLED',raising=False)
    payload={'source':'single_warehouse_demo','temperature_zone':'chilled','travel_mode':'straight_line_simulation',
        'speed_kmh':30,'max_orders':20,'budget_ms':60000,'acknowledge_dry_run_only':True,
        'event_type':'vehicle_breakdown','object_id':'veh_1','occurred_at_s':200,'delay_s':0}
    response=client.post('/local-pg/pg-preview/r30b/reschedule',json=payload)
    assert response.status_code==503
    assert 'disabled' in str(response.json())
