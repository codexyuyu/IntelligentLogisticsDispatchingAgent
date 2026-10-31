import type { Comparison } from './ProposalComparison';
import './defense-evidence.css';

const yen = (cents: number) => `¥${(cents / 100).toFixed(2)}`;
const km = (metres: number) => `${(metres / 1000).toFixed(2)} km`;
const integer = (n: number) => `${n.toLocaleString('zh-CN')}`;
const signed = (n: number, fmt: (n: number) => string) => n === 0 ? '持平' : `${n > 0 ? '+' : '−'}${fmt(Math.abs(n))}`;
const comparable = (comparison: Comparison) => comparison.coverage_preserved &&
  [comparison.simple_hold.objective_cents, comparison.candidate.objective_cents,
    comparison.simple_hold.distance_m, comparison.candidate.distance_m,
    comparison.simple_hold.total_late_s, comparison.candidate.total_late_s].every(Number.isFinite);

/** All values are computed from the same persisted simulation comparison, never demo constants. */
export default function DefenseImpactPanel({ comparison, validated, compact = false }: {
  comparison: Comparison; validated?: boolean; compact?: boolean;
}) {
  const { baseline, simple_hold: hold, candidate } = comparison;
  const valid = comparable(comparison);
  const saving = hold.objective_cents - candidate.objective_cents;
  const benefit = valid && validated !== false && comparison.delta_vs_hold.improves_objective === true && saving > 0;
  const verdict = !valid ? '数据不足 · 不可判定' : validated === false ? '候选未通过校验'
    : benefit ? '本次候选有费用改善' : saving < 0 ? '本次候选费用更高' : '未证明费用改善';
  const cols = [
    { label: '原计划 v0', value: baseline, note: '未发生本次延误的基准' },
    { label: '异常后简单顺延', value: hold, note: '本次收益评估的公平对照' },
    { label: 'OR-Tools 候选', value: candidate, note: validated === false ? '约束校验未通过' : '等待或已完成人工审批' },
  ];
  return <section className={`defense-impact ${compact ? 'defense-impact-compact' : ''}`} aria-label="调度效果对比">
    <div className="defense-heading"><div><span className="defense-eyebrow">调度决策 · 真实模拟指标</span><h3>调度前后效果对比</h3></div>
      <span className={`defense-verdict ${benefit ? 'positive' : valid && saving < 0 ? 'negative' : ''}`} role="status">{verdict}</span></div>
    <div className="defense-impact-grid">{cols.map((item, i) => <div className={`defense-score ${i === 2 ? 'candidate' : ''}`} key={item.label}>
      <div className="defense-score-title"><strong>{item.label}</strong><small>{item.note}</small></div>
      <div className="defense-main-number">{yen(item.value.objective_cents)}<small>估算综合费用</small></div>
      <dl><div><dt>路线里程</dt><dd>{km(item.value.distance_m)}</dd></div>
        <div><dt>迟到订单</dt><dd>{integer(item.value.late_orders)} 单</dd></div>
        <div><dt>累计迟到</dt><dd>{integer(item.value.total_late_s)} 秒</dd></div>
        <div><dt>预计配送</dt><dd>{integer(item.value.deliveries.length)} 单</dd></div></dl>
    </div>)}</div>
    <div className="defense-delta-grid">
      <div><small>候选相较简单顺延 · 综合费用</small><strong>{valid ? signed(candidate.objective_cents - hold.objective_cents, yen) : '—'}</strong></div>
      <div><small>候选相较简单顺延 · 行驶距离</small><strong>{valid ? signed(candidate.distance_m - hold.distance_m, km) : '—'}</strong></div>
      <div><small>候选相较简单顺延 · 迟到订单</small><strong>{valid && comparison.soft_due_configured ? signed(candidate.late_orders - hold.late_orders, integer) : '—'}</strong></div>
    </div>
    <p className="defense-disclaimer">判断口径：只用<strong>简单顺延</strong>与<strong>候选方案</strong>衡量异常后的重调度收益；v0 仅用于解释异常前计划，不作为费用改善基准。
      {comparison.distance_approximate ? ' 距离属于场景道路矩阵估算。' : ''}
      {!comparison.soft_due_configured ? ' 当前场景无可评价的软时效截止，迟到改善不作结论。' : ''}
      {!comparison.coverage_preserved ? ' 两方案交付范围不同，收益暂不具可比性。' : ''}
      {' '}统计范围仅为本次异常影响车辆的完整模拟路线，不代表全车队收益。本表不是 GPS 实际里程或真实运输账单。</p>
  </section>;
}
