import { useEffect, useState } from 'react';
import { request } from '../../api';

type Outcome = {
  order: string[];
  deliveries: { name: string; arrival_s: number; soft_due_s: number; late_s: number }[];
  distance_m: number;
  driving_cents: number;
  fixed_vehicle_cents: number;
  soft_late_cents: number;
  objective_cents: number;
  late_orders: number;
  total_late_s: number;
  hard_window_valid: boolean;
  last_return_s: number;
  delivered_orders: number;
};
type Benchmark = {
  case_id: string;
  name: string;
  description: string;
  method: string;
  candidate_count: number;
  source_scenario: string;
  simulation_only: boolean;
  assumptions: { delay_s: number; anchor_time_s: number; penalty_cents_per_late_second: number };
  before_delay: Outcome;
  simple_hold: Outcome;
  optimized_continuation: Outcome;
  comparison: { route_changed: boolean; lateness_reduced_s: number; late_orders_reduced: number;
    objective_saved_cents: number; distance_saved_m: number; improves_objective: boolean };
};
const money = (cents: number) => `¥${(cents / 100).toFixed(2)}`;
const time = (seconds: number) => `${seconds} 秒`;

/** A factual, read-only comparison; every number comes from the server's enumeration. */
export default function DelayReplanningBenchmark() {
  const [delay, setDelay] = useState(90);
  const [data, setData] = useState<Benchmark | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  async function refresh(signal?: AbortSignal, seconds = delay) {
    setLoading(true); setError('');
    try {
      const result = await request<Benchmark>(`/integration/benchmarks/delay-replanning?delay_s=${seconds}`, { signal });
      if (!signal?.aborted) setData(result);
    } catch (err) {
      if (!signal?.aborted) setError(err instanceof Error ? err.message : String(err));
    } finally { if (!signal?.aborted) setLoading(false); }
  }
  useEffect(() => {
    const controller = new AbortController();
    void refresh(controller.signal, 90);
    return () => controller.abort();
  }, []);
  function exportEvidence() {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `delay-replanning-${data.assumptions.delay_s}s.json`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const hold = data?.simple_hold;
  const candidate = data?.optimized_continuation;
  return <section className="panel" aria-label="途中延误路线优化对照">
    <div className="s5-flex-row" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
      <div><h3 style={{ marginBottom: 4 }}>途中延误 · 路线优化对照</h3>
        <p className="s5-muted" style={{ marginTop: 0 }}>同一起点、相同延误与车辆成本，对比保留原路线和重新规划剩余收货点。</p>
      </div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'end', flexWrap: 'wrap' }}>
        <label>延误时长（秒） <input aria-label="对照延误时长" type="number" min={0} max={1200} step={10}
          style={{ width: 96 }} value={delay} onChange={e => setDelay(Number(e.target.value))} /></label>
        <button className="btn btn-primary" disabled={loading || !Number.isInteger(delay) || delay < 0 || delay > 1200}
          onClick={() => void refresh()}>{loading ? '计算中…' : '重新计算对照'}</button>
        <button className="btn btn-ghost" disabled={!data || loading} onClick={exportEvidence}>导出计算结果</button>
      </div>
    </div>
    {error && <p role="alert" className="callout callout-error">对照计算失败：{error}</p>}
    {data && data.before_delay && data.simple_hold && data.optimized_continuation ? <>
      <p className="s5-muted">{data.name} · {data.source_scenario} 的道路矩阵 · {data.candidate_count} 种接续顺序穷举求优。
        这是独立合成的三收货点子问题，不代表已执行的十订单联合调度或 PostgreSQL 中的审批记录。</p>
      <div className="form-grid">
        <div className="panel" style={{ padding: 14 }}><div className="s5-muted">综合目标差额（顺延 − 重规划）</div>
          <h2 style={{ margin: '6px 0' }}>{money(data.comparison.objective_saved_cents)}</h2>
          <small>{data.comparison.improves_objective ? '重新规划目标值更低' : '未获得目标值改善'}</small></div>
        <div className="panel" style={{ padding: 14 }}><div className="s5-muted">累计软时效逾期减少</div>
          <h2 style={{ margin: '6px 0' }}>{time(data.comparison.lateness_reduced_s)}</h2>
          <small>逾期订单减少 {data.comparison.late_orders_reduced} 单</small></div>
        <div className="panel" style={{ padding: 14 }}><div className="s5-muted">里程变化（重规划 − 顺延）</div>
          <h2 style={{ margin: '6px 0' }}>{((candidate!.distance_m - hold!.distance_m) / 1000).toFixed(1)} km</h2>
          <small>路程变长也可能换来更少的配送迟到</small></div>
      </div>
      <div className="table-wrap"><table><thead><tr><th>指标</th><th>无延误原方案</th><th>简单等待并顺延</th><th>延误后重新规划</th></tr></thead>
        <tbody>
          <tr><td>累计行驶里程</td>{[data.before_delay, hold!, candidate!].map((x, i) => <td key={i}>{(x.distance_m / 1000).toFixed(1)} km</td>)}</tr>
          <tr><td>里程费用</td>{[data.before_delay, hold!, candidate!].map((x, i) => <td key={i}>{money(x.driving_cents)}</td>)}</tr>
          <tr><td>软时效违约成本</td>{[data.before_delay, hold!, candidate!].map((x, i) => <td key={i}>{money(x.soft_late_cents)}</td>)}</tr>
          <tr><td>综合目标（含固定车辆成本）</td>{[data.before_delay, hold!, candidate!].map((x, i) => <td key={i}><strong>{money(x.objective_cents)}</strong></td>)}</tr>
          <tr><td>迟到订单</td>{[data.before_delay, hold!, candidate!].map((x, i) => <td key={i}>{x.late_orders} / {x.delivered_orders}</td>)}</tr>
          <tr><td>累计迟到时间</td>{[data.before_delay, hold!, candidate!].map((x, i) => <td key={i}>{time(x.total_late_s)}</td>)}</tr>
          <tr><td>车辆返回时刻</td>{[data.before_delay, hold!, candidate!].map((x, i) => <td key={i}>{x.last_return_s}s</td>)}</tr>
          <tr><td>硬时窗约束</td>{[data.before_delay, hold!, candidate!].map((x, i) => <td key={i}>{x.hard_window_valid ? '满足' : '不满足'}</td>)}</tr>
        </tbody></table></div>
      <div className="form-grid">
        <div className="panel" style={{ padding: 14 }}><strong>简单顺延 · 原停靠顺序</strong>
          <p>{hold!.order.join(' → ')}</p><small>延误后仍沿用未受扰动时的原线路。</small></div>
        <div className="panel" style={{ padding: 14 }}><strong>重新规划 · 接续停靠顺序</strong>
          <p>{candidate!.order.join(' → ')}</p><small>从相同的已到达安全节点重新求解剩余收货点。</small></div>
      </div>
      <details><summary>配送时效与计算依据</summary>
        <p>{data.description} 目标为“行驶里程费 + 软时效逾期惩罚 + 固定车辆费”；仅剩余配送停靠顺序可变，已完成行程保持不变。</p>
        <p>默认延误 {data.assumptions.delay_s}s，软时效每逾期 1 秒计 {data.assumptions.penalty_cents_per_late_second} 分。
          对所有 {data.candidate_count} 个有效顺序计算相同费用并取最小值，没有预设优化率。</p>
        <div className="table-wrap"><table><thead><tr><th>收货点</th><th>软时效截止</th><th>简单顺延到达</th><th>重新规划到达</th></tr></thead><tbody>
          {hold!.deliveries.map(item => {
            const adjusted = candidate!.deliveries.find(other => other.name === item.name);
            return <tr key={item.name}><td>{item.name}</td><td>{item.soft_due_s}s</td><td>{item.arrival_s}s {item.late_s > 0 ? `(迟到 ${item.late_s}s)` : ''}</td>
              <td>{adjusted?.arrival_s ?? '—'}s {adjusted?.late_s ? `(迟到 ${adjusted.late_s}s)` : ''}</td></tr>;
          })}
        </tbody></table></div>
      </details>
    </> : <p className="s5-muted" style={{ margin: 0 }}>当前后端未返回延误对照数据（旧接口或旧记录），本面板暂不显示。</p>}
  </section>;
}
