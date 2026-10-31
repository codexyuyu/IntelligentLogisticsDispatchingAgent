import DefenseImpactPanel from './DefenseImpactPanel';
import type { SimIncident } from './api';
import './proposal-comparison.css';

type Delivery = { order_id: string; order_ref: string; node_id?: string | null;
  arrival_s: number; delivered_s: number; soft_due_s: number | null; late_s: number };
type Score = { distance_m: number; driving_cents: number; fixed_vehicle_cents: number;
  late_penalty_cents: number; objective_cents: number; late_orders: number;
  total_late_s: number; deliveries: Delivery[]; return_s: number | null };
export type Comparison = { scope: string; source: string; method: string;
  distance_approximate?: boolean; late_definition?: string; soft_due_configured: boolean;
  objective_note: string; baseline: Score; simple_hold: Score; candidate: Score;
  route_changed: boolean; coverage_preserved: boolean;
  delta_vs_hold: { distance_saved_m: number; late_orders_reduced: number;
    lateness_reduced_s: number; objective_saved_cents: number; improves_objective: boolean } };
const money = (cents: number) => `¥${(cents / 100).toFixed(2)}`;
const clock = (seconds?: number | null) => seconds == null ? '—' : `${Math.floor(seconds / 60)}分${String(seconds % 60).padStart(2, '0')}秒`;
const distance = (metres: number) => `${(metres / 1000).toFixed(2)} km`;
function RouteTable({ title, value }: { title: string; value: Score }) {
  return <div className="proposal-route-card"><div className="proposal-route-heading"><strong>{title}</strong><span>停靠 {value.deliveries.length} 单</span></div>
    <ol className="proposal-route-stops">{value.deliveries.map(stop => <li key={stop.order_id}>
      <div><strong>{stop.order_ref}</strong><small>交付 {clock(stop.delivered_s)}</small></div>
      <span className={stop.late_s ? 'proposal-late' : ''}>{stop.soft_due_s == null ? '无软时效要求' : stop.late_s ? `超时 ${stop.late_s}s` : `截止 ${clock(stop.soft_due_s)}`}</span>
    </li>)}</ol>
  </div>;
}
export default function ProposalComparison({ incident, comparison }: { incident: SimIncident; comparison: Comparison }) {
  const { simple_hold: hold, candidate, delta_vs_hold: delta } = comparison;
  const noReroute = !comparison.route_changed;
  return <section className="proposal-comparison" aria-label="候选方案评估">
    <div className="proposal-title"><div><span className="proposal-overline">方案评估</span><h4>候选方案与原定路线对比</h4></div>
      <span className={`pill ${incident.proposal_valid ? 'pill-success' : 'pill-warning'}`}>{incident.proposal_valid ? '约束校验通过' : '未通过校验'}</span></div>
    <p className="proposal-intro">{incident.strategy === 'simulated_local_reroute' ? '已计算途中接续路线；以下是实际生成的候选方案与延误后保持原路线的比较。'
      : incident.strategy === 'simulated_local_retimed' ? '已重新计算接续时序，停靠顺序保持不变。'
      : '当前候选为等待后保持原路线，未产生新的停靠顺序。'}所有指标均由当前运行记录计算。</p>
    <DefenseImpactPanel comparison={comparison} validated={incident.proposal_valid === true} />
    <details><summary>展开完整指标表（含费用分项）</summary>
    <div className="proposal-table-wrap"><table className="proposal-metrics"><thead><tr><th>指标</th><th>原定计划 v0</th><th>简单顺延</th><th>候选方案</th></tr></thead><tbody>
      <tr><th>路线距离</th><td>{distance(comparison.baseline.distance_m)}</td><td>{distance(hold.distance_m)}</td><td>{distance(candidate.distance_m)}</td></tr>
      <tr><th>行驶费用</th><td>{money(comparison.baseline.driving_cents)}</td><td>{money(hold.driving_cents)}</td><td>{money(candidate.driving_cents)}</td></tr>
      <tr><th>软时效迟到单数</th><td>{comparison.baseline.late_orders}</td><td>{hold.late_orders}</td><td>{candidate.late_orders}</td></tr>
      <tr><th>累计迟到</th><td>{comparison.baseline.total_late_s}s</td><td>{hold.total_late_s}s</td><td>{candidate.total_late_s}s</td></tr>
      <tr><th>估算综合费用</th><td>{money(comparison.baseline.objective_cents)}</td><td>{money(hold.objective_cents)}</td><td><strong>{money(candidate.objective_cents)}</strong></td></tr>
    </tbody></table></div></details>
    <div className="proposal-summary">
      <div><small>相较简单顺延 · 综合费用变化</small><strong className={delta.objective_saved_cents > 0 && comparison.coverage_preserved && incident.proposal_valid === true ? 'proposal-benefit' : ''}>{delta.objective_saved_cents > 0 ? `节省 ${money(delta.objective_saved_cents)}` : delta.objective_saved_cents < 0 ? `增加 ${money(-delta.objective_saved_cents)}` : '无变化'}</strong></div>
      <div><small>减少迟到</small><strong>{delta.lateness_reduced_s > 0 ? `${delta.lateness_reduced_s} 秒` : '无改善'}</strong></div>
      <div><small>剩余配送顺序</small><strong>{noReroute ? '保持不变' : '已重新安排'}</strong></div>
    </div>
    <p className="proposal-context">{!comparison.coverage_preserved ? '候选与简单顺延的交付范围不同，不能据此认定优化。'
      : !incident.proposal_valid ? '候选未通过校验，不能认定优化收益。'
      : delta.improves_objective ? '当前方案在上述估算口径下优于简单顺延。'
        : '当前方案未在上述估算口径下优于简单顺延；审批代表接受模拟处置，不代表已获得优化收益。'}
      {!comparison.soft_due_configured && ' 当前订单未配置软时效截止，因此不能计算软时效改善。'}</p>
    <details className="proposal-route-details" open><summary>路线及交付时序</summary>
      <div className="proposal-route-grid"><RouteTable title="原计划（v0）" value={comparison.baseline}/>
        <RouteTable title="延误后简单顺延" value={hold}/><RouteTable title="待审批候选方案" value={candidate}/></div>
    </details>
    <p className="proposal-caveat">统计范围：本次异常车辆的完整模拟路线；{comparison.objective_note}。
      {comparison.distance_approximate ? ' 距离按道路矩阵与中途分段比例估算，非实车里程。' : ''}不代表实际运输订单或库存已被修改。</p>
  </section>;
}
