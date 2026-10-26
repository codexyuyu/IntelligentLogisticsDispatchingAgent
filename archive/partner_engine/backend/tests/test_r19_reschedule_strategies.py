"""R19 strategy-comparison unit tests. No solver runs: pure metric/judgement logic."""
import json
from pathlib import Path
from datetime import datetime, timezone

import pytest

from app.contracts.common import SolveMetadata, Source, TimeWindow, ValidationReport
from app.contracts.entities import Order, PlanningSnapshot, TravelMatrix, Vehicle, Warehouse
from app.contracts.planning import (
    CandidatePlan, RouteStop, RoutingResult, VehicleArrival, VehicleRoute, WarehouseHandoff,
    WarehouseScheduleResult,
)
from tools import r19_reschedule_ablation as r19


def _source() -> Source:
    return Source(source_kind='default', source_ref='r19-test',
                  observed_at=datetime.now(timezone.utc), rule_version='test-1')


def _snapshot(*, window_end: int = 2400, version: int = 1) -> PlanningSnapshot:
    orders = tuple(
        Order(order_id=f'ord_00{i}', version=1, warehouse_id='wh_1', batch_id=f'bat_00{i}',
              delivery_node_id=f'node_c{i}', quantity_units=1, weight_kg=100, volume_l=100,
              temperature_zone='chilled', service_window=TimeWindow(start_s=0, end_s=window_end),
              service_duration_s=60, freshness_deadline_s=10000, required=True, source=_source())
        for i in (1, 2)
    )
    vehicles = tuple(
        Vehicle(vehicle_id=f'veh_{i}', version=1, warehouse_id='wh_1', start_node_id='node_wh',
                end_node_id='node_wh', current_node_id='node_wh', capacity_weight_kg=1000,
                capacity_volume_l=1000, remaining_weight_kg=1000, remaining_volume_l=1000,
                temperature_zone='chilled', shift_window=TimeWindow(start_s=0, end_s=20000),
                available_at_s=0, source=_source())
        for i in (1, 2)
    )
    return PlanningSnapshot(
        snapshot_id='snap_r19', version=version, origin_at=datetime.now(timezone.utc),
        simulation_time_s=0, rule_version='test-1', orders=orders, vehicles=vehicles,
        warehouses=(Warehouse(warehouse_id='wh_1', version=1, node_id='node_wh',
                              temperature_zones=('chilled',)),),
        resources=(), stock_lots=(), operations=(), frozen_operations=(),
        matrix=TravelMatrix(
            matrix_id='mat_1', version=1, node_ids=('node_wh', 'node_c1', 'node_c2'),
            duration_s=((0, 600, 600), (600, 0, 0), (600, 0, 0)),
            distance_m=((0, 1000, 1000), (1000, 0, 0), (1000, 0, 0)), source=_source()),
    )


def _route(vehicle_id: str, node_id: str, order_id: str, *, start: int, orders: int = 1) -> VehicleRoute:
    if not orders:
        return VehicleRoute(
            vehicle_id=vehicle_id,
            stops=(
                RouteStop(node_id='node_wh', order_ids=(), stop_kind='depot_start', arrival_at_s=start,
                          service_start_at_s=start, departure_at_s=start, load_weight_kg=0, load_volume_l=0),
                RouteStop(node_id='node_wh', order_ids=(), stop_kind='depot_end', arrival_at_s=start,
                          service_start_at_s=start, departure_at_s=start, load_weight_kg=0, load_volume_l=0),
            ),
            distance_m=0, duration_s=0)
    return VehicleRoute(
        vehicle_id=vehicle_id,
        stops=(
            RouteStop(node_id='node_wh', order_ids=(), stop_kind='depot_start', arrival_at_s=start,
                      service_start_at_s=start, departure_at_s=start, load_weight_kg=100, load_volume_l=100),
            RouteStop(node_id=node_id, order_ids=(order_id,), stop_kind='delivery', arrival_at_s=start + 600,
                      service_start_at_s=start + 600, departure_at_s=start + 660,
                      load_weight_kg=0, load_volume_l=0),
            RouteStop(node_id='node_wh', order_ids=(), stop_kind='depot_end', arrival_at_s=start + 1260,
                      service_start_at_s=start + 1260, departure_at_s=start + 1260,
                      load_weight_kg=0, load_volume_l=0),
        ),
        distance_m=2000, duration_s=1260)


def _routing(*, version: int = 1) -> RoutingResult:
    return RoutingResult(
        snapshot_id='snap_r19', snapshot_version=version,
        metadata=SolveMetadata(status='feasible', raw_status='TEST', engine='fake',
                               engine_version='1', has_solution=True, proof_scope='test', solve_ms=1),
        routes=(
            _route('veh_1', 'node_c1', 'ord_001', start=1200),
            _route('veh_2', 'node_c2', 'ord_002', start=1200),
        ),
        warehouse_arrivals=(
            VehicleArrival(vehicle_id='veh_1', warehouse_id='wh_1', arrival_at_s=2460,
                           order_ids=('ord_001',)),
            VehicleArrival(vehicle_id='veh_2', warehouse_id='wh_1', arrival_at_s=2460,
                           order_ids=('ord_002',)),
        ),
        unserved_orders=(),
    )


def _warehouse(*, handoffs=('ord_001', 'ord_002')) -> WarehouseScheduleResult:
    return WarehouseScheduleResult(
        snapshot_id='snap_r19', snapshot_version=1,
        metadata=SolveMetadata(status='feasible', raw_status='TEST', engine='fake',
                               engine_version='1', has_solution=True, proof_scope='test', solve_ms=1),
        operations=(),
        warehouse_handoffs=tuple(
            WarehouseHandoff(order_id=oid, warehouse_id='wh_1', ready_at_s=1200,
                             loading_window=TimeWindow(start_s=1200, end_s=2400))
            for oid in handoffs),
    )


def _plan(*, snapshot, routing, warehouse, version: int = 1) -> CandidatePlan:
    return CandidatePlan(
        plan_id='plan_r19_test', snapshot_id=snapshot.snapshot_id,
        snapshot_version=snapshot.version, version=version, plan_hash='a' * 64,
        routing=routing, warehouse=warehouse,
        validation=ValidationReport(status='passed', validator_version='test',
                                    checked_rule_ids=('test',), violations=()))


def test_choose_event_vehicle_prefers_busiest_then_smallest_id():
    snapshot = _snapshot()
    # veh_2 carries the only order, veh_1 none -> the busiest route wins over the smaller id.
    routing = _routing().model_copy(update={'routes': (
        _route('veh_1', 'node_c1', 'ord_001', start=1200, orders=0),
        _route('veh_2', 'node_c2', 'ord_001', start=1200),
    )})
    plan = _plan(snapshot=snapshot, routing=routing, warehouse=_warehouse(handoffs=('ord_001',)))
    vehicle_id, order_count = r19.choose_event_vehicle(plan)
    assert (vehicle_id, order_count) == ('veh_2', 1)


def test_choose_event_vehicle_tie_breaks_on_vehicle_id():
    snapshot = _snapshot()
    plan = _plan(snapshot=snapshot, routing=_routing(), warehouse=_warehouse())
    assert r19.choose_event_vehicle(plan) == ('veh_1', 1)


def test_no_reschedule_shifts_exactly_the_target_route_and_keeps_distance():
    snapshot = _snapshot()
    baseline = _plan(snapshot=snapshot, routing=_routing(), warehouse=_warehouse())
    derived = snapshot.model_copy(update={'version': 2})
    shifted = r19.apply_no_reschedule(baseline_plan=baseline, derived=derived,
                                      vehicle_id='veh_1', delay_s=r19.DELAY_LADDER_S[0])
    before = {r.vehicle_id: r for r in baseline.routing.routes}
    after = {r.vehicle_id: r for r in shifted.routing.routes}
    assert [s.departure_at_s for s in after['veh_1'].stops] == [
        s.departure_at_s + r19.DELAY_LADDER_S[0] for s in before['veh_1'].stops]
    assert after['veh_2'] == before['veh_2']
    assert after['veh_1'].distance_m == before['veh_1'].distance_m
    assert after['veh_1'].duration_s == before['veh_1'].duration_s
    arrivals = {a.vehicle_id: a.arrival_at_s for a in shifted.routing.warehouse_arrivals}
    assert arrivals['veh_1'] == 2460 + r19.DELAY_LADDER_S[0] and arrivals['veh_2'] == 2460
    assert shifted.snapshot_version == 2 and shifted.version == baseline.version + 1
    assert shifted.validation.status == 'not_checked'


def test_plan_metrics_recompute_lateness_and_disturbance():
    snapshot = _snapshot()
    baseline = _plan(snapshot=snapshot, routing=_routing(), warehouse=_warehouse())
    derived = snapshot.model_copy(update={'version': 2})
    on_time = r19.plan_metrics(plan=baseline, snapshot=snapshot, baseline_plan=baseline, wall_ms=1)
    assert (on_time['on_time_count'], on_time['late_order_count'], on_time['max_lateness_s']) == (2, 0, 0)
    assert on_time['changed_order_count'] == 0 and on_time['total_distance_m'] == 4000

    shifted = r19.apply_no_reschedule(baseline_plan=baseline, derived=derived,
                                      vehicle_id='veh_1', delay_s=r19.DELAY_LADDER_S[0])
    late = r19.plan_metrics(plan=shifted, snapshot=derived, baseline_plan=baseline, wall_ms=2)
    assert late['on_time_count'] == 1 and late['late_order_count'] == 1
    assert late['max_lateness_s'] == 1800 + r19.DELAY_LADDER_S[0] - 2400
    assert late['total_lateness_s'] == 1800 + r19.DELAY_LADDER_S[0] - 2400
    assert late['changed_order_count'] == 0  # same vehicle, only later


def test_independent_validation_passes_baseline_and_flags_delayed_windows():
    snapshot = _snapshot()
    baseline = _plan(snapshot=snapshot, routing=_routing(), warehouse=_warehouse())
    clean = r19.independent_validation(plan=baseline, snapshot=snapshot,
                                       order_ids=('ord_001', 'ord_002'))
    assert clean['transport_passed'] and clean['plan_passed']

    derived = snapshot.model_copy(update={'version': 2})
    shifted = r19.apply_no_reschedule(baseline_plan=baseline, derived=derived,
                                      vehicle_id='veh_1', delay_s=r19.DELAY_LADDER_S[0])
    dirty = r19.independent_validation(plan=shifted, snapshot=derived,
                                      order_ids=('ord_001', 'ord_002'))
    assert not dirty['transport_passed']
    assert any(v.startswith('service_window:ord_001') for v in dirty['transport'][0]['violations'])
    # Service windows live in the transport rule set; the cross-domain plan rules do not
    # encode them, so legality must be the conjunction of both rule families.
    record = r19.arm_record(name='no_reschedule', plan=shifted, snapshot=derived,
                            order_ids=('ord_001', 'ord_002'), baseline_plan=baseline, wall_ms=0)
    assert record['legal'] is False
    # The independent metric recomputation catches the lateness even when a rule family misses it.
    assert record['metrics']['late_order_count'] == 1
    assert record['metrics']['max_lateness_s'] == 300


def test_arm_record_marks_partial_when_required_order_unserved():
    snapshot = _snapshot()
    baseline = _plan(snapshot=snapshot, routing=_routing(), warehouse=_warehouse())
    empty_routing = _routing().model_copy(update={'routes': (
        _route('veh_1', 'node_c1', 'ord_001', start=1200),
        _route('veh_2', 'node_c2', 'ord_002', start=1200, orders=0),
    )})
    partial = r19.arm_record(name='full_reschedule',
                             plan=_plan(snapshot=snapshot, routing=empty_routing,
                                        warehouse=_warehouse()),
                             snapshot=snapshot, order_ids=('ord_001', 'ord_002'),
                             baseline_plan=baseline, wall_ms=5)
    assert partial['status'] == 'partial'
    assert partial['metrics']['unserved_order_ids'] == ['ord_002']


def _rung(delay_s: int, statuses: dict, legal: dict) -> dict:
    metrics = {'changed_order_count': 0, 'distance_delta_m': 0, 'total_lateness_s': 0,
               'total_handoff_wait_s': 0, 'wall_ms': 0}
    arms = {arm: {'status': statuses[arm], 'legal': legal.get(arm, False), 'metrics': dict(metrics),
                  'wall_ms': 0, 'independent_validation': {}} for arm in r19.ARMS}
    rung = {'delay_s': delay_s, 'effective_delay_s': delay_s, 'arms': arms}
    rung['judgement'] = r19.judge(rung)
    return rung


def _case(name: str, rungs: list, family: str = 'base') -> dict:
    return {'case': name, 'family': family, 'size': 12, 'seed': 17, 'rungs': rungs}


def test_judge_completes_only_when_every_arm_serves_all_orders():
    good = {arm: 'complete' for arm in r19.ARMS}
    weak = dict(good, no_reschedule='partial')
    assert r19.judge(_rung(900, good, {}))['status'] == 'complete_comparison'
    verdict = r19.judge(_rung(900, weak, {}))
    assert verdict['status'] == 'incomplete' and verdict['reasons']


def test_build_summary_withholds_aggregate_until_every_comparison_completes():
    good = {arm: 'complete' for arm in r19.ARMS}
    solvers_only = {'no_reschedule': False, 'full_reschedule': True, 'local_reschedule': True}
    partial_cases = [_case('s12_seed17', [_rung(900, good, solvers_only)]),
                     _case('s16_seed42', [_rung(900, dict(good, local_reschedule='failed'), solvers_only)])]
    summary = r19.build_summary(partial_cases, budget_ms=1000, simpy_check=None,
                                expected_comparisons=3)
    assert summary['comparison_count'] == 2 and summary['complete_comparisons'] == 1
    assert summary['aggregate_over_complete_comparisons'] is None
    assert summary['no_reschedule_violation_comparisons'] == ['s12_seed17@base@900', 's16_seed42@base@900']
    assert summary['legal_arm_counts']['no_reschedule'] == 0
    assert summary['no_reschedule_first_breaking_effective_delay_s'] == {'s12_seed17@base': 900,
                                                                        's16_seed42@base': 900}

    full_cases = [_case('a', [_rung(900, good, solvers_only), _rung(1800, good, solvers_only)]),
                  _case('b', [_rung(900, good, solvers_only)])]
    published = r19.build_summary(full_cases, budget_ms=1000, simpy_check=None,
                                  expected_comparisons=3)
    assert published['complete_comparisons'] == 3
    assert published['aggregate_over_complete_comparisons'] is not None


def test_execute_refuses_non_empty_output_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(r19, 'load_snapshot', lambda path: (_snapshot(), 'b' * 64))
    target = tmp_path / 'run'
    target.mkdir()
    (target / 'summary.json').write_text('{}', encoding='utf8')
    with pytest.raises(FileExistsError):
        r19.execute(base_file=tmp_path / 'scenario.json', budget_ms=1000, outdir=target,
                    case_count=1, dry_run=False)


def test_dry_run_writes_scenarios_only(tmp_path, monkeypatch):
    snapshot = _snapshot()
    monkeypatch.setattr(r19, 'load_snapshot', lambda path: (snapshot, 'c' * 64))
    calls = {'prepare': 0}

    def fake_prepare(base, *, size, seed):
        calls['prepare'] += 1
        return snapshot
    monkeypatch.setattr(r19, 'prepare_case', fake_prepare)
    target = tmp_path / 'dry'
    result = r19.execute(base_file=tmp_path / 'scenario.json', budget_ms=1000, outdir=target,
                         case_count=1, dry_run=True, simpy_check=False)
    assert result is None and calls['prepare'] == 1
    assert (target / 'manifest.json').is_file()
    assert (target / 'scenarios' / 's12_seed17__base.json').is_file()
    assert (target / 'scenarios' / 's12_seed17__stress.json').is_file()
    assert not list((target / 'raw').iterdir())


def test_effective_delay_is_absorbed_when_planned_departure_is_later():
    """A delay only moves a route when it pushes availability past the planned departure."""
    snapshot = _snapshot()
    baseline = _plan(snapshot=snapshot, routing=_routing(), warehouse=_warehouse())
    event = r19.build_event(case='s12_seed17', snapshot=snapshot, vehicle_id='veh_1', delay_s=900)
    derived = r19._derive_snapshot_for_event(snapshot, event)
    assert r19.planned_departure_s(baseline, 'veh_1') == 1200
    # availability becomes 900 -> the vehicle already departs at 1200, so nothing moves
    assert r19.effective_delay_s(derived=derived, vehicle_id='veh_1', planned_departure=1200) == 0
    # a route that departs at 600 is pushed by exactly the remaining 300 s
    assert r19.effective_delay_s(derived=derived, vehicle_id='veh_1', planned_departure=600) == 300
    absorbed = r19.apply_no_reschedule(baseline_plan=baseline, derived=derived,
                                       vehicle_id='veh_1', delay_s=0)
    assert [s.departure_at_s for s in absorbed.routing.routes[0].stops] == [
        s.departure_at_s for s in baseline.routing.routes[0].stops]
    metrics = r19.plan_metrics(plan=absorbed, snapshot=derived, baseline_plan=baseline, wall_ms=0)
    assert metrics['on_time_count'] == 2 and metrics['max_lateness_s'] == 0


def test_event_id_and_vehicle_selection_are_pre_registered():
    snapshot = _snapshot()
    event = r19.build_event(case='s12_seed17', snapshot=snapshot, vehicle_id='veh_1', delay_s=3600)
    assert event.event_id == 'evt_r19_s12_seed17_3600'
    assert event.event_type == 'departure_delayed'
    assert event.payload.delay_s == 3600 and event.occurred_at_s == r19.OCCURRED_AT_S
    assert event.expected_snapshot_version == snapshot.version
    assert r19.DELAY_LADDER_S == (900, 3600, 14400, 28800)


# --- acceptance freeze: the gate must reject doctored evidence -------------------------

def _fake_run(tmp_path) -> Path:
    """Build a one-comparison run directory whose records match the plans exactly."""
    run = tmp_path / 'run_fake'
    (run / 'scenarios').mkdir(parents=True)
    (run / 'raw').mkdir()
    snapshot = _snapshot()
    scenario_path = run / 'scenarios' / 's12_seed17__base.json'
    scenario_path.write_text(json.dumps(snapshot.model_dump(mode='json'), ensure_ascii=False),
                             encoding='utf8', newline='\n')
    order_ids = ('ord_001', 'ord_002')
    baseline = _plan(snapshot=snapshot, routing=_routing(), warehouse=_warehouse())
    event = r19.build_event(case='s12_seed17', snapshot=snapshot, vehicle_id='veh_1', delay_s=900)
    derived = r19._derive_snapshot_for_event(snapshot, event)
    arms = {}
    for name, plan in (('no_reschedule', baseline), ('full_reschedule', baseline),
                       ('local_reschedule', baseline)):
        arms[name] = r19.arm_record(name=name, plan=plan, snapshot=derived, order_ids=order_ids,
                                    baseline_plan=baseline, wall_ms=1)
    rung = {'delay_s': 900, 'effective_delay_s': 900, 'event': event.model_dump(mode='json'),
            'derived_snapshot_version': derived.version, 'arms': arms}
    rung['judgement'] = r19.judge(rung)
    record = {'case': 's12_seed17', 'family': 'base', 'size': 12, 'seed': 17,
              'scenario_file': 'scenarios/s12_seed17__base.json',
              'scenario_sha256': r19.sha256_file(scenario_path),
              'baseline': {'wall_ms': 1, 'candidate_plan': baseline.model_dump(mode='json'),
                           'metrics': r19.plan_metrics(plan=baseline, snapshot=snapshot,
                                                       baseline_plan=baseline, wall_ms=1),
                           'independent_validation': r19.independent_validation(
                               plan=baseline, snapshot=snapshot, order_ids=order_ids)},
              'rungs': [rung]}
    (run / 'raw' / 's12_seed17__base_arms.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding='utf8', newline='\n')
    summary = r19.build_summary([record], budget_ms=1000, simpy_check=None, expected_comparisons=1)
    summary['families'] = ['base']
    (run / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False), encoding='utf8', newline='\n')
    for name, body in (('summary.csv', 'case\n'), ('summary.md', '# r19\n')):
        (run / name).write_text(body, encoding='utf8', newline='\n')
    (run / 'manifest.json').write_text(json.dumps({
        'protocol': r19.PROTOCOL, 'source_scenario_sha256': 'd' * 64}, ensure_ascii=False),
        encoding='utf8', newline='\n')
    return run


def test_freeze_recomputes_and_accepts_consistent_evidence(tmp_path):
    from tools import r19_acceptance_freeze as freeze

    run = _fake_run(tmp_path)
    accepted = tmp_path / 'accepted'
    assert freeze.main(['--run-dir', str(run), '--accepted-dir', str(accepted)]) == 0
    audit = json.loads((accepted / 'r19_recompute_audit.json').read_text(encoding='utf8'))
    assert audit['comparisons_recomputed'] == 1 and audit['mismatches'] == 0
    manifest = json.loads((accepted / 'r19_accepted_manifest.json').read_text(encoding='utf8'))
    assert manifest['file_count'] == len(manifest['files'])
    assert (accepted / 'README.md').is_file()


def test_freeze_refuses_doctored_metric(tmp_path):
    from tools import r19_acceptance_freeze as freeze

    run = _fake_run(tmp_path)
    raw_path = run / 'raw' / 's12_seed17__base_arms.json'
    raw = json.loads(raw_path.read_text(encoding='utf8'))
    raw['rungs'][0]['arms']['no_reschedule']['metrics']['total_distance_m'] += 1
    raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding='utf8', newline='\n')
    with pytest.raises(ValueError, match='recomputation disagrees'):
        freeze.main(['--run-dir', str(run), '--accepted-dir', str(tmp_path / 'accepted')])


def test_freeze_refuses_doctored_legality_flag(tmp_path):
    from tools import r19_acceptance_freeze as freeze

    run = _fake_run(tmp_path)
    raw_path = run / 'raw' / 's12_seed17__base_arms.json'
    raw = json.loads(raw_path.read_text(encoding='utf8'))
    raw['rungs'][0]['arms']['local_reschedule']['legal'] = False
    raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding='utf8', newline='\n')
    with pytest.raises(ValueError, match='recomputation disagrees'):
        freeze.main(['--run-dir', str(run), '--accepted-dir', str(tmp_path / 'accepted')])


def test_freeze_requires_empty_destination(tmp_path):
    from tools import r19_acceptance_freeze as freeze

    run = _fake_run(tmp_path)
    accepted = tmp_path / 'accepted'
    accepted.mkdir()
    (accepted / 'old.json').write_text('{}', encoding='utf8')
    with pytest.raises(SystemExit):
        freeze.main(['--run-dir', str(run), '--accepted-dir', str(accepted)])
