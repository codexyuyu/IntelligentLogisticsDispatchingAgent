"""R30-D focused business negatives; no external database, model or solver needed."""
from __future__ import annotations

from copy import deepcopy
from datetime import timedelta

import pytest
from app.adapters.persistence.pg_r27_workflow import demo_snapshot, verified_snapshot
from app.adapters.persistence.pg_routing_preview import BridgeInputError
from app.adapters.warehouse.validator import WarehouseScheduleValidator
from app.api.routes.agent_demo import _plan_summary
from app.contracts.common import SolveMetadata
from app.contracts.entities import ScheduledOperation
from app.contracts.planning import WarehouseHandoff, WarehouseScheduleRequest, WarehouseScheduleResult
from app.domain.cold_chain_rules import validate_cold_chain
from test_r27_workflow import db


def scenario():
    return demo_snapshot().model_dump(mode='python')


def audit(data=None, order_ids=None):
    data = data if data is not None else scenario()
    return validate_cold_chain(data, order_ids or [x['order_id'] for x in data['orders']])


def issue_ids(report):
    return {v['rule_id'] for v in report['violations']}


def test_synthetic_facts_verified_but_precooling_not_claimed():
    report = audit()
    assert not report['violations']
    assert report['status'] == 'partial'
    assert 'coldchain.precooling_and_cleaning_changeover' in report['not_checked_rule_ids']
    assert 'coldchain.time_dependent_room_capacity' in report['not_checked_rule_ids']


def test_multiple_orders_draw_from_same_lot_and_cannot_overallocate():
    data=scenario()
    first, second = data['orders'][:2]
    second['batch_id']=first['batch_id']
    second['warehouse_id']=first['warehouse_id']
    second['temperature_zone']=first['temperature_zone']
    report=audit(data,[first['order_id'], second['order_id']])
    assert 'coldchain.batch_quantity' in issue_ids(report)


def test_batch_missing_wrong_warehouse_and_incompatible_zone_fail():
    data=scenario(); data['orders'][0]['batch_id']='absent_batch'
    assert 'coldchain.batch_exists' in issue_ids(audit(data))
    data=scenario(); data['stock_lots'][0]['warehouse_id']='other'
    assert 'coldchain.batch_warehouse' in issue_ids(audit(data))
    data=scenario(); data['stock_lots'][0]['temperature_zone']='frozen'
    assert 'coldchain.batch_temperature' in issue_ids(audit(data))


def test_expiry_uses_actual_delivery_when_known_not_arbitrary_freshness_deadline():
    data=scenario(); o=data['orders'][0]; lot=data['stock_lots'][0]
    # Stock expires between earliest possible service and latest freshness
    # deadline: pre-solve cannot prove violation. Post-solve can.
    origin = data['origin_at']
    lot['expires_at'] = origin + timedelta(seconds=o['service_window']['start_s']+300)
    first_only=[o['order_id']]
    assert 'coldchain.batch_expiry' not in issue_ids(audit(data,first_only))
    result=validate_cold_chain(data,first_only,{o['order_id']:o['service_window']['start_s']+450})
    assert 'coldchain.batch_expiry' in issue_ids(result)


def test_verified_postgres_unknown_reservations_is_explicitly_partial():
    data=db(); snap,_=verified_snapshot(data,temperature_zone='chilled',
        travel_mode='straight_line_simulation',speed_kmh=30,max_orders=20,budget_ms=5000)
    report=validate_cold_chain(snap.model_dump(mode='python'),[x.order_id for x in snap.orders])
    assert report['status']=='partial' and not report['violations']
    assert 'coldchain.pg_live_reservation_and_quarantine_unknown' in report['not_checked_rule_ids']


def test_verified_postgres_rejects_recorded_stock_shortage():
    data=db();data['r24']['lots'][0]['quantity_units']=4
    with pytest.raises(BridgeInputError,match='r24_stock_lot_oversubscribed'):
        verified_snapshot(data,temperature_zone='chilled',travel_mode='straight_line_simulation',
            speed_kmh=30,max_orders=20,budget_ms=5000)


def test_verified_postgres_rejects_batch_zone_mismatch():
    data=db();data['r24']['lots'][0]['temperature_zone']='frozen'
    with pytest.raises(BridgeInputError,match='r24_lot_dock_warehouse_or_quantity_conflict'):
        verified_snapshot(data,temperature_zone='chilled',travel_mode='straight_line_simulation',
            speed_kmh=30,max_orders=20,budget_ms=5000)


def test_independent_validator_rejects_fabricated_handoff_time():
    snap=demo_snapshot()
    op=snap.operations[0]
    scheduled=ScheduledOperation(operation_id=op.operation_id, resource_id=op.resource_id, start_s=0, end_s=60)
    handoff=WarehouseHandoff(order_id=op.order_ids[0],warehouse_id=op.warehouse_id,
        ready_at_s=0,loading_window={'start_s':0,'end_s':1000})
    result=WarehouseScheduleResult(snapshot_id=snap.snapshot_id,snapshot_version=snap.version,
        metadata=SolveMetadata(status='feasible',raw_status='TEST',engine='stub',engine_version='0',
            has_solution=True,proof_scope='unit test only',solve_ms=0),
        operations=(scheduled,),warehouse_handoffs=(handoff,))
    req=WarehouseScheduleRequest(snapshot=snap,order_ids=(op.order_ids[0],),budget={'remaining_ms':1000})
    report=WarehouseScheduleValidator().validate(req,result)
    assert report.status=='failed'
    assert any(v.rule_id=='warehouse.handoff_operation_ready' for v in report.violations)


def test_ai_warehouse_summary_handles_full_or_legacy_missing_details():
    from test_r30c_deepseek_agent import fake_workflow
    payload=fake_workflow()
    summary=_plan_summary(payload)
    assert summary['warehouse_operations'][0]['operation_id']=='op_001'
    assert summary['vehicle_assignment_details'][0]['vehicle_id']=='veh_2'
    assert summary['cold_chain_audit']['status']=='not_checked'
    assert 'distance_m' in summary['vehicle_assignment_details'][0]
