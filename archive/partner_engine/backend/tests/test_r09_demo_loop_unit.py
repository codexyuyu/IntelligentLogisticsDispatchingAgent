"""R09 final round: demo-loop enrichment, scoped cold-chain evidence, reporting.

One end-to-end pass (real CP-SAT + OR-Tools) plus unit-level guards for the three
things this round fixed: unknown waits are not zero, out-of-scope occupancies are
not modelled, and the transcript is demo-ready.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend' / 'tools'))

from r09_demo_loop import enrich_coldchain  # noqa: E402

from app.application.contract_net import format_transcript  # noqa: E402
from app.application.coordinator import coordinate  # noqa: E402
from app.application.negotiation_link import negotiate_plan, tasks_from_plan  # noqa: E402
from app.application.plan_observations import observe_plan  # noqa: E402
from app.contracts.entities import PlanningSnapshot  # noqa: E402

SOURCE = {
    'source_kind': 'simulation', 'source_ref': 'tests/test_r09_demo_loop_unit.py',
    'observed_at': '2026-10-24T00:00:00Z', 'rule_version': 'r09-demo-test',
}


def _scenario() -> dict:
    """Two-order synthetic scenario in the same shape as data/scenarios/*.json."""
    return {
        'snapshot_id': 'snap_demo', 'version': 1,
        'origin_at': '2026-10-24T00:00:00Z', 'simulation_time_s': 0,
        'rule_version': 'r09-demo-test',
        'orders': [
            {'order_id': f'ord_{index:03d}', 'version': 1, 'warehouse_id': 'wh_1',
             'batch_id': f'batch_{index:03d}', 'delivery_node_id': f'node_c{index}',
             'quantity_units': 2, 'weight_kg': 100, 'volume_l': 200,
             'temperature_zone': 'chilled',
             'service_window': {'start_s': 0, 'end_s': 3600},
             'service_duration_s': 60, 'freshness_deadline_s': 3600,
             'required': True, 'source': SOURCE}
            for index in (1, 2)
        ],
        'vehicles': [{
            'vehicle_id': 'veh_1', 'version': 1, 'warehouse_id': 'wh_1',
            'start_node_id': 'node_depot', 'end_node_id': 'node_depot',
            'current_node_id': 'node_depot', 'capacity_weight_kg': 1000,
            'capacity_volume_l': 2000, 'remaining_weight_kg': 1000,
            'remaining_volume_l': 2000, 'temperature_zone': 'chilled',
            'shift_window': {'start_s': 0, 'end_s': 3600},
            'available_at_s': 0, 'source': SOURCE,
        }],
        'warehouses': [{'warehouse_id': 'wh_1', 'version': 1, 'node_id': 'node_depot',
                        'temperature_zones': ['chilled']}],
        'resources': [{'resource_id': 'res_dock1', 'warehouse_id': 'wh_1', 'version': 1,
                       'resource_kind': 'dock', 'capacity_units': 1,
                       'available_windows': [{'start_s': 0, 'end_s': 3600}],
                       'unavailable_windows': []}],
        'stock_lots': [],
        'operations': [
            {'operation_id': f'op_load{index:03d}', 'order_ids': [f'ord_{index:03d}'],
             'warehouse_id': 'wh_1', 'resource_id': 'res_dock1',
             'operation_kind': 'loading', 'duration_s': 60, 'release_at_s': 0,
             'deadline_at_s': 3600, 'predecessor_ids': [], 'status': 'pending'}
            for index in (1, 2)
        ],
        'frozen_operations': [],
        'matrix': {'matrix_id': 'matrix_demo', 'version': 1,
                   'node_ids': ['node_depot', 'node_c1', 'node_c2'],
                   'duration_s': [[0, 120, 180], [120, 0, 60], [180, 60, 0]],
                   'distance_m': [[0, 1000, 1500], [1000, 0, 500], [1500, 500, 0]],
                   'source': SOURCE},
    }


def test_enrichment_is_deterministic_and_complete():
    first = enrich_coldchain(_scenario())
    second = enrich_coldchain(_scenario())

    assert first == second
    coldchain = first['coldchain']
    assert coldchain['rule_version'] == 'r05-demo-1.0'
    assert len(coldchain['storage_locations']) == 1
    assert len(coldchain['occupancies']) == 2
    assert len(coldchain['precool_requirements']) == 2
    # precool operations were added and wired as predecessors of the loading task
    precool_ids = {op['operation_id'] for op in first['operations'] if 'precool' in op['operation_kind']}
    assert precool_ids == {'pre_op_load001', 'pre_op_load002'}
    loading = next(op for op in first['operations'] if op['operation_id'] == 'op_load001')
    assert 'pre_op_load001' in loading['predecessor_ids']
    assert loading['primary_requirement_id'] == 'req_op_load001'
    # the enriched payload is still a valid contract snapshot
    PlanningSnapshot.model_validate(first)


def test_enriched_snapshot_solves_with_coldchain_evidence():
    snapshot = PlanningSnapshot.model_validate(enrich_coldchain(_scenario()))
    order_ids = tuple(order.order_id for order in snapshot.orders)

    plan = coordinate(snapshot=snapshot, order_ids=order_ids, budget_ms=9000,
                      max_coordination_rounds=1, coordination_mode='sequential')
    observations = observe_plan(plan, order_ids)

    assert plan.validation.status == 'passed'
    assert observations.coldchain_evidence is True
    assert observations.served_count == 2
    assert observations.capacity_peaks                      # R05 evidence is real
    assert observations.exposure_totals
    assert [wait for _, wait in observations.handoff_wait_s] == [w for _, w in observations.handoff_wait_s]
    assert all(wait is not None for _, wait in observations.handoff_wait_s)


def test_unknown_wait_is_reported_as_none_not_zero():
    snapshot = PlanningSnapshot.model_validate(enrich_coldchain(_scenario()))
    order_ids = tuple(order.order_id for order in snapshot.orders)
    plan = coordinate(snapshot=snapshot, order_ids=order_ids, budget_ms=9000,
                      max_coordination_rounds=1, coordination_mode='sequential')

    # Drop the only route: the orders still have handoffs, but no departure.
    starved = plan.model_copy(update={
        'routing': plan.routing.model_copy(update={'routes': ()}),
    })
    observations = observe_plan(starved, order_ids)

    assert all(wait is None for _, wait in observations.handoff_wait_s)
    assert observations.measured_handoff_wait_s == ()
    assert len(observations.unmeasured_handoff_orders) == 2


def test_negotiation_runs_on_the_solved_plan_and_formats_for_demo():
    snapshot = PlanningSnapshot.model_validate(enrich_coldchain(_scenario()))
    order_ids = tuple(order.order_id for order in snapshot.orders)
    plan = coordinate(snapshot=snapshot, order_ids=order_ids, budget_ms=9000,
                      max_coordination_rounds=1, coordination_mode='sequential')

    tasks = tasks_from_plan(plan, snapshot)
    assert {task.task_id for task in tasks} == {'op_load001', 'op_load002'}

    outcomes = negotiate_plan(plan, snapshot, now_s=0)
    assert len(outcomes) == 2
    for outcome in outcomes:
        assert outcome.result.status == 'confirmed'
        assert outcome.awarded_role in ('warehouse', 'transport')
        # the roles really were bound to the solved plan: operation + vehicle ids
        assert outcome.operation_id.startswith('op_load')
        assert outcome.vehicle_id == 'veh_1'
        lines = outcome.transcript_lines()
        assert lines[0].split()[3].strip() == 'cfp'
        assert lines[-1].startswith('status=confirmed')


def test_format_transcript_is_stable_and_ordered():
    snapshot = PlanningSnapshot.model_validate(enrich_coldchain(_scenario()))
    order_ids = tuple(order.order_id for order in snapshot.orders)
    plan = coordinate(snapshot=snapshot, order_ids=order_ids, budget_ms=9000,
                      max_coordination_rounds=1, coordination_mode='sequential')
    outcome = negotiate_plan(plan, snapshot, now_s=0)[0]

    first = format_transcript(outcome.result)
    second = format_transcript(outcome.result)
    assert first == second
    assert [int(line.split()[0]) for line in first[:-1]] == list(range(1, len(first)))


