"""R30-E: regression proof for event-backed order, vehicle and warehouse diffs.

These use archived accepted R19 baseline plus existing R30-B test doubles;
this is not proof of a new OR-Tools solve on Windows.
"""
import copy
import pytest

from app.adapters.persistence.pg_r30e_evidence import build_impact_evidence
from app.adapters.persistence.pg_r30b_reschedule import ExceptionSpec, run_reschedule
from app.api.routes.agent_demo import _exception_summary
from tests.test_r30b_reschedule import (
    one_warehouse_baseline, accepted_baseline, StubWarehouse, StubRoutingAllExplicitlyUnserved,
)


def test_breakdown_forecast_does_not_use_halted_route_geometry(one_warehouse_baseline):
    res = run_reschedule(baseline=one_warehouse_baseline,
        spec=ExceptionSpec(event_type='vehicle_breakdown',object_id='veh_1',occurred_at_s=3500))
    impact=res['impact_evidence']
    assert impact['schema']=='r30e_exception_evidence_v1'
    halted=next(v for v in impact['vehicles'] if v['vehicle_id']=='veh_1')
    assert halted['halted_at_event']
    assert set(halted['previous_order_sequence']) > set(halted['forecast_delivery_order_ids'])
    for row in impact['orders']:
        events=[e for e in res['replay']['events'] if e['kind']=='order_delivered' and e['object_id']==row['order_id']]
        assert len(events)<=1
        assert row['new_delivery_at_s']==(events[0]['time_s'] if events else None)
        if row['status']=='unserved':
            assert row['unserved_reason_code']
    summary=_exception_summary(res)
    assert summary['impact_counts']['affected_orders']>=2
    assert 'affected_order_details' in summary
    assert 'vehicle_delivery_forecasts' in summary
    assert summary['database_mutated'] is False


def test_delay_has_actual_positive_eta_deltas(one_warehouse_baseline):
    res=run_reschedule(baseline=one_warehouse_baseline,
        spec=ExceptionSpec(event_type='delivery_delay',object_id='veh_1',occurred_at_s=3500,delay_s=600))
    impact=res['impact_evidence']
    assert impact['counts']['delivery_time_changed_orders']>0
    row=next(o for o in impact['orders'] if o['order_id']=='ord_002')
    assert row['delivery_delta_s']>0 and row['time_changed'] and row['affected']
    locked=next(o for o in impact['orders'] if o['order_id']=='ord_003')
    assert locked['delivery_delta_s']==0 and locked['status']=='completed_before_event'


def test_resource_failure_reports_interrupted_operations(one_warehouse_baseline):
    res=run_reschedule(baseline=one_warehouse_baseline,
        spec=ExceptionSpec(event_type='warehouse_resource_failure',object_id='res_dock1',occurred_at_s=80),
        warehouse_solver=StubWarehouse(one_warehouse_baseline),routing_solver=StubRoutingAllExplicitlyUnserved())
    assert res['impact_evidence']['counts']['interrupted_operations']>=1
    affected=res['impact_evidence']['warehouse_operation_changes']
    assert any(w['status']=='interrupted_at_event' and w['previous_resource_id']=='res_dock1' for w in affected)
    assert all(w['new_resource_id']!='res_dock1' for w in affected if w['new_resource_id'])


def test_quarantine_reports_no_invented_replacement(one_warehouse_baseline):
    res=run_reschedule(baseline=one_warehouse_baseline,
        spec=ExceptionSpec(event_type='inventory_quarantine',object_id='batch_001',occurred_at_s=100),
        warehouse_solver=StubWarehouse(one_warehouse_baseline),routing_solver=StubRoutingAllExplicitlyUnserved())
    assert any(o['order_id']=='ord_001' and o['status']=='unserved' and 'quarantined' in o['unserved_reason_code']
               for o in res['impact_evidence']['orders'])
    assert res['verification']['suffix_accounting']=='passed'


def test_evidence_fails_if_delivery_eta_is_fabricated(one_warehouse_baseline):
    res=run_reschedule(baseline=one_warehouse_baseline,
        spec=ExceptionSpec(event_type='vehicle_breakdown',object_id='veh_1',occurred_at_s=3500))
    forged=copy.deepcopy(res['comparison']['order_changes'])
    row=next(x for x in forged if x['new_delivery_at_s'] is not None)
    row['new_delivery_at_s']+=42
    with pytest.raises(RuntimeError,match='r30e_order_eta_not_equal_to_replay_event'):
        build_impact_evidence(baseline=one_warehouse_baseline,
            replay_events=res['replay']['events'],next_operations={},
            interrupted_operation_ids=set(),order_changes=forged,
            event_t=3500,halted_vehicles={})


def test_delay_parameter_affects_preview_identity(one_warehouse_baseline):
    a=run_reschedule(baseline=one_warehouse_baseline,
        spec=ExceptionSpec(event_type='delivery_delay',object_id='veh_1',occurred_at_s=3500,delay_s=300))
    b=run_reschedule(baseline=one_warehouse_baseline,
        spec=ExceptionSpec(event_type='delivery_delay',object_id='veh_1',occurred_at_s=3500,delay_s=600))
    assert a['new_plan_id']!=b['new_plan_id']
    assert a['impact_evidence']['counts']['replay_predicted_delivery_orders']==a['comparison']['forecast_delivered_total']
