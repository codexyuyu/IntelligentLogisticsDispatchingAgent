import { useEffect, useState } from 'react';
import { request, idempotencyKey } from '../../api';
import SectionHeader from '../../components/SectionHeader';

type Scenario = { id: string; name: string; source_kind: string };
type Message = { seq: number; at_s: number; kind: string; role: string; task_id: string; detail: string };
type Metric = { code: string; value: number | null; unit: string; reason: string | null; sample_count: number };
type Run = { run_id: string; status: string; reason?: string; source_kind: string;
  negotiation?: { result: { status: string; digest: string; transcript: Message[] } | null };
  observations?: { metrics: { values: Metric[] }; handoffs: { task_id: string; warehouse_ready_s: number; pickup_start_s: number | null }[];
    coldchain: { rule_version: string; occupancies: { occupancy_id: string; batch_id: string; location_id: string; start_s: number; end_s: number }[] } };
};
const labels: Record<string, string> = { delivery_rate: '需求满足率', on_time_rate: '订单准时率', average_delay_s: '平均延误',
  total_distance_m: '运输总距离', total_cost_cents: '运输总成本', vehicle_utilization: '车辆利用率', warehouse_utilization: '仓储利用率',
  dock_utilization: '月台利用率', equipment_utilization: '设备利用率', solve_time_ms: '求解时间', exception_detection_ms: '异常检测时间',
  reschedule_time_ms: '重调度时间', changed_tasks: '被修改任务数量', plan_disturbance: '方案扰动程度' };
const roles: Record<string, string> = { coordinator: '协调者', warehouse: '仓储', transport: '运输', exception: '异常恢复' };
const messages: Record<string, string> = { cfp: '发布任务', bid: '报价', award: '授标', confirm: '确认', revoke: '撤销', conflict: '冲突', close: '结束' };

export default function IntegrationPage({ initialView = 'negotiation' }: { initialView?: string }) {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selected, setSelected] = useState('');
  const [source, setSource] = useState('');
  const [run, setRun] = useState<Run | null>(null);
  const [view, setView] = useState(initialView);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [budget, setBudget] = useState(4000);
  const [seed, setSeed] = useState(0);
  async function loadScenarios() {
    const data = await request<{ items: Scenario[] }>('/integration/scenarios');
    setScenarios(data.items);
    setSelected(previous => previous || data.items[0]?.id || '');
  }
  useEffect(() => {
    let active = true;
    void loadScenarios().catch(e => { if (active) setError(String(e)); });
    const last = localStorage.getItem('integration_last_run');
    if (last) void request<Run>(`/integration/runs/${encodeURIComponent(last)}`).then(value => {
      if (active) setRun(value);
    }).catch(e => { if (active) setError(String(e)); });
    return () => { active = false; };
  }, []);
  async function action(fn: () => Promise<void>) {
    setError(''); setNotice(''); setBusy(true);
    try { await fn(); } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  async function importData() {
    const value = JSON.parse(source);
    const result = await request<{ status: string; scenario_id?: string; issues?: string[] }>('/integration/scenarios',
      { method: 'POST', body: JSON.stringify(value) });
    if (result.status !== 'checked') throw new Error(`资料不完整：${result.issues?.join('；')}`);
    await loadScenarios(); setSelected(result.scenario_id!); setNotice('场景已校验并保存。');
  }
  async function compute() {
    const value = await request<Run>('/integration/runs', { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey() },
      body: JSON.stringify({ schema_version: '2.0.0', scenario_id: selected, budget_ms: budget, seed, recoveries: [] }) });
    setRun(value); localStorage.setItem('integration_last_run', value.run_id);
  }
  const negotiation = run?.negotiation?.result;
  const transcript = negotiation?.transcript ?? [];
  const confirmed = new Map<string, Message>();
  for (const message of transcript) {
    if (message.kind === 'confirm') confirmed.set(message.task_id, message);
    if (message.kind === 'revoke') confirmed.delete(message.task_id);
  }
  async function revoke(taskId: string) {
    if (!run || !negotiation) return;
    const value = await request<Run>(`/integration/runs/${run.run_id}/revoke`, { method: 'POST', body: JSON.stringify({
      schema_version: '2.0.0', task_id: taskId, now_s: Math.max(0, ...transcript.map(m => m.at_s)), expected_digest: negotiation.digest,
    }) });
    setRun(value);
  }
  return <div>
    <SectionHeader title="冷链调度、协商与业务观测" desc="从已导入的场景计算仓储与运输方案，经独立校验后协商。协商确认不会直接提交派车计划。" />
    <section className="panel">
      <h3>场景数据</h3><p>企业数据尚未提供。合成样本仅用于验证流程，页面始终保留数据来源。</p>
      <input aria-label="导入场景文件" type="file" accept=".json,application/json" disabled={busy}
        onChange={event => { const file = event.target.files?.[0]; if (file) void action(async () => setSource(await file.text())); }} />
      <button className="btn btn-ghost" disabled={busy} onClick={() => void action(async () => {
        const template = await request<unknown>('/integration/template'); setSource(JSON.stringify(template, null, 2));
      })}>加载合成测试样本</button>
      <textarea aria-label="场景 JSON" rows={5} value={source} onChange={event => setSource(event.target.value)} placeholder="选择 JSON 文件或加载合成测试样本" />
      <button className="btn btn-primary" disabled={busy || !source.trim()} onClick={() => void action(importData)}>校验并导入</button>
      <hr />
      <label>已导入场景 <select value={selected} onChange={e => setSelected(e.target.value)} disabled={busy}>
        <option value="">请选择</option>{scenarios.map(s => <option key={s.id} value={s.id}>{s.name} · {s.source_kind === 'synthetic' ? '合成测试' : '企业来源声明'}</option>)}
      </select></label>
      <label>计算预算（毫秒） <input type="number" min={100} max={12000} value={budget} onChange={e => setBudget(Number(e.target.value))} /></label>
      <label>随机种子 <input type="number" min={0} value={seed} onChange={e => setSeed(Number(e.target.value))} /></label>
      <button className="btn btn-primary" disabled={busy || !selected} onClick={() => void action(compute)}>{busy ? '处理中…' : '计算并协商'}</button>
      {error && <p role="alert" className="callout callout-error">{error}</p>}{notice && <p role="status">{notice}</p>}
    </section>
    {run && <section className="panel">
      <h3>运行记录</h3><p>来源：{run.source_kind === 'synthetic' ? '合成测试数据' : '企业来源声明（尚未独立核实）'} · {run.status === 'checked' ? '求解证据已校验' : '未完成校验'} · {run.reason}</p>
      <small>记录编号：{run.run_id}</small>
      <div className="seg">{[['negotiation', '协商记录'], ['metrics', '14 项指标'], ['coldchain', '冷链与交接']].map(([key, title]) =>
        <button key={key} className={`seg-btn ${view === key ? 'is-active' : ''}`} onClick={() => setView(key)}>{title}</button>)}</div>
      {view === 'negotiation' && <>
        {!negotiation ? <p>缺少有效求解证据，未生成报价。</p> : <>
          <p>当前已确认 {confirmed.size} 个任务。未声明扰动时，异常恢复角色不报价。</p>
          {[...confirmed].map(([id, message]) => <p key={id}>{id} · {roles[message.role]} <button disabled={busy}
            className="btn btn-ghost" onClick={() => void action(() => revoke(id))}>撤销确认</button></p>)}
          <div className="table-wrap"><table><thead><tr><th>序号</th><th>时间（秒）</th><th>角色</th><th>动作</th><th>任务</th><th>记录</th></tr></thead>
            <tbody>{transcript.map(m => <tr key={m.seq}><td>{m.seq}</td><td>{m.at_s}</td><td>{roles[m.role]}</td><td>{messages[m.kind]}</td><td>{m.task_id}</td><td style={{ overflowWrap: 'anywhere', maxWidth: 450 }}>{m.detail}</td></tr>)}</tbody></table></div>
          <small style={{ overflowWrap: 'anywhere' }}>摘要：{negotiation.digest}</small>
        </>}
      </>}
      {view === 'metrics' && (!run.observations ? <p>没有通过校验的观测结果。</p> : <div className="table-wrap"><table>
        <thead><tr><th>指标</th><th>数值</th><th>单位</th><th>样本数</th><th>缺失原因</th></tr></thead>
        <tbody>{run.observations.metrics.values.map(m => <tr key={m.code}><td>{labels[m.code] ?? m.code}</td>
          <td>{m.value === null ? '—' : m.unit === 'ratio' ? `${(m.value*100).toFixed(2)}%` : m.value.toLocaleString()}</td>
          <td>{m.unit}</td><td>{m.sample_count}</td><td>{m.reason === 'missing_data' ? '缺少测量证据' : m.reason === 'division_by_zero' ? '分母为零' : m.reason ?? '—'}</td></tr>)}</tbody>
      </table><p>以上为计划口径。没有异常检测或重排测量时，相应指标保持缺失。</p></div>)}
      {view === 'coldchain' && (!run.observations ? <p>没有通过校验的冷链结果。</p> : <>
        <p>规则版本：{run.observations.coldchain.rule_version}</p><h4>库存占用区间</h4>
        <div className="table-wrap"><table><thead><tr><th>批次</th><th>库位</th><th>开始（秒）</th><th>结束（秒）</th></tr></thead><tbody>
          {run.observations.coldchain.occupancies.map(o => <tr key={o.occupancy_id}><td>{o.batch_id}</td><td>{o.location_id}</td><td>{o.start_s}</td><td>{o.end_s}</td></tr>)}
        </tbody></table></div><h4>仓运交接</h4><div className="table-wrap"><table><thead><tr><th>任务</th><th>仓储完成（秒）</th><th>提货开始（秒）</th></tr></thead><tbody>
          {run.observations.handoffs.map(h => <tr key={h.task_id}><td>{h.task_id}</td><td>{h.warehouse_ready_s}</td><td>{h.pickup_start_s ?? '缺少证据'}</td></tr>)}
        </tbody></table></div>
      </>)}
    </section>}
  </div>;
}

export function ObservationPage() { return <IntegrationPage initialView="metrics" />; }
export function ColdChainPage() { return <IntegrationPage initialView="coldchain" />; }
