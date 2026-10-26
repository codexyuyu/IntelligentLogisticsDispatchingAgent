from dataclasses import replace

import pytest

from logistics_domain.metrics import MetricSource
from logistics_evaluation.complete import MetricInput, OrderOutcome, ResourceUse, Span, TaskState, calculate_metrics
from logistics_evaluation.paired import TrialResult, compare_reports, run_paired


def example():
    return MetricInput('test', MetricSource.SIMULATION, 0, 200,
        orders=tuple(OrderOutcome(str(i), end, 100) for i, end in enumerate((60, 80, 100, 140, None))),
        distance_m=1234, transport_cost_cents=456,
        vehicles=(ResourceUse('v1', (Span(0, 60),), (Span(0, 100),)),
                  ResourceUse('v2', (Span(0, 30),), (Span(0, 100),))),
        warehouse_zones=(ResourceUse('z', (Span(0, 10, 100),), (Span(0, 10, 200),)),),
        docks=(), equipment=(ResourceUse('e', (Span(0, 10, 2),), (Span(0, 20, 2),)),),
        solve_ms=(10, 20), detection_ms=(5,), reschedule_ms=(30,),
        base_tasks=tuple(TaskState(str(i), ('a',), 0, 10) for i in range(4)),
        candidate_tasks=tuple(TaskState(str(i), ('b' if i == 0 else 'a',), 0, 10) for i in range(4)))


def test_all_fourteen_hand_calculated_values():
    report = calculate_metrics(example())
    m = {v.code: v for v in report.values}
    assert len(m) == 14
    for name, value in {'delivery_rate': .8, 'on_time_rate': .6, 'average_delay_s': 10,
        'vehicle_utilization': .45, 'warehouse_utilization': .5, 'equipment_utilization': .5,
        'changed_tasks': 1, 'plan_disturbance': .1, 'solve_time_ms': 15}.items():
        assert m[name].value == pytest.approx(value)
    assert m['dock_utilization'].value is None
    assert m['dock_utilization'].reason.value == 'division_by_zero'
    assert report.open_overdue_s == 100


def test_missing_is_not_zero_and_overlaps_are_not_double_counted():
    report = calculate_metrics(MetricInput('x', MetricSource.ACTUAL, 0, 100))
    assert all(m.value is None and m.reason is not None for m in report.values)
    data = replace(example(), vehicles=(ResourceUse('v', (Span(0, 60), Span(20, 80)), (Span(10, 70),)),))
    metric = next(m for m in calculate_metrics(data).values if m.code == 'vehicle_utilization')
    assert metric.value == 1 and metric.numerator == metric.denominator == 60


def test_cancellation_due_fallback_and_completed_fact_protection():
    data = replace(example(), orders=(OrderOutcome('cancel', None, 100, cancelled_at_s=0),
        OrderOutcome('delivered', 120, None, hard_latest_s=100, service_s=20,
                     cancelled_at_s=110, service_started_s=100)))
    report = calculate_metrics(data)
    assert report.cancelled_count == 1 and report.due_fallback_order_ids == ('delivered',)
    assert report.values[0].value == report.values[1].value == 1
    with pytest.raises(ValueError, match='completed facts'):
        calculate_metrics(replace(data, base_tasks=(TaskState('0', ('a',), 0, 10, completed_at_s=10),), event_s=20))


def test_comparison_requires_same_scope_source_window_and_definition():
    with pytest.raises(ValueError, match='INCOMPARABLE'):
        compare_reports(calculate_metrics(example()), calculate_metrics(replace(example(), source=MetricSource.ACTUAL)))


def test_paired_seeds_keep_failure_denominator_and_reproducible_bootstrap():
    def baseline(case, seed, budget):
        return TrialResult('passed', calculate_metrics(example()), ('fixture-evidence',))
    def candidate(case, seed, budget):
        if seed == 0:
            raise RuntimeError('deliberate failed trial')
        return TrialResult('passed', calculate_metrics(replace(example(), distance_m=1200+seed)), ('fixture-evidence',))
    def absent_llm(case, seed, budget):
        return TrialResult('not_checked', None, (), 'provider unavailable')
    strategies = {'rule': baseline, 'solver_only': candidate, 'llm_solver': absent_llm}
    a = run_paired({'synthetic': True}, strategies)
    b = run_paired({'synthetic': True}, strategies)
    assert a['comparisons'] == b['comparisons']
    assert len(a['trials']) == 30
    assert a['summary']['solver_only']['success_rate'] == .9
    assert a['summary']['llm_solver']['success_rate'] == 0
    assert a['comparisons'][0]['metrics']['total_distance_m']['paired_count'] == 9
    assert a['comparisons'][1]['metrics'] == {}
