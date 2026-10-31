import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import DefenseImpactPanel from './DefenseImpactPanel';
import type { Comparison } from './ProposalComparison';
const mk = (hold: number, candidate: number, coverage = true): Comparison => ({
  scope: 'affected_vehicle_full_route', source: 'checked_run_simulation', method: 'matrix_arc_fraction_and_delivery_events',
  soft_due_configured: true, objective_note: 'matrix', coverage_preserved: coverage, route_changed: false,
  baseline: { distance_m: 12000, driving_cents: 2000, fixed_vehicle_cents: 0, late_penalty_cents: 0, objective_cents: 2000, late_orders: 1, total_late_s: 30, deliveries: [], return_s: 500 },
  simple_hold: { distance_m: 14000, driving_cents: hold, fixed_vehicle_cents: 0, late_penalty_cents: 0, objective_cents: hold, late_orders: 2, total_late_s: 80, deliveries: [], return_s: 600 },
  candidate: { distance_m: 13000, driving_cents: candidate, fixed_vehicle_cents: 0, late_penalty_cents: 0, objective_cents: candidate, late_orders: 1, total_late_s: 40, deliveries: [], return_s: 580 },
  delta_vs_hold: { distance_saved_m: 1000, late_orders_reduced: 1, lateness_reduced_s: 40,
    objective_saved_cents: hold - candidate, improves_objective: coverage && candidate < hold },
});
describe('答辩方案对比不伪造收益', () => {
  it('节省金额来自后端返回的三方指标', () => {
    const markup = renderToStaticMarkup(<DefenseImpactPanel comparison={mk(19000, 16000)} validated />);
    expect(markup).toContain('本次候选有费用改善');
    expect(markup).toContain('−¥30.00');
    expect(markup).toContain('原计划 v0');
    expect(markup).toContain('异常后简单顺延');
  });
  it('相同费用不得宣称改善', () => {
    const markup = renderToStaticMarkup(<DefenseImpactPanel comparison={mk(18000, 18000)} validated />);
    expect(markup).toContain('未证明费用改善');
    expect(markup).toContain('持平');
  });
  it('交付范围不同不可比较，即使费用下降', () => {
    const markup = renderToStaticMarkup(<DefenseImpactPanel comparison={mk(19000, 16000, false)} validated />);
    expect(markup).toContain('数据不足 · 不可判定');
    expect(markup).toContain('不具可比性');
  });
  it('候选校验不通过不得宣称改善', () => {
    const markup = renderToStaticMarkup(<DefenseImpactPanel comparison={mk(19000, 16000)} validated={false} />);
    expect(markup).toContain('候选未通过校验');
    expect(markup).not.toContain('本次候选有费用改善');
  });
});
