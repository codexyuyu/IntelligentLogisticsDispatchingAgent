import { useEffect, useState } from 'react';
import { request, idempotencyKey } from '../../api';
import SectionHeader from '../../components/SectionHeader';
import { RunBar, useStageRun } from '../stageB/RunContext';
import { isPending, pollStatus, readStored, saveStored, useTaskRunner, validInteger } from '../../lib/asyncJobs';
import { statusLabel } from '../../lib/labels';

type Scenario = { id: string; name: string; source_kind: string };
type Message = { seq: number; at_s: number; kind: string; role: string; task_id: string; detail: string };
type Metric = { code: string; value: number | null; unit: string; reason: string | null; sample_count: number };
type Run = { run_id: string; job_id?: string; status: string; reason?: string; source_kind?: string;
  warehouse_solution?: { status: string; storage_allocations: unknown[] };
  transport_solution?: { status: string };
  joint_validation?: { valid: boolean; violations: unknown[] };
  candidate?: { id: string; task_assignments: { task_kind: string }[] };
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
const importantMetrics = [
  { code: 'total_distance_m', title: '配送总距离' },
  { code: 'total_cost_cents', title: '预计运输成本' },
  { code: 'on_time_rate', title: '订单准时率' },
  { code: 'delivery_rate', title: '需求满足率' },
];
function metricValue(metric?: Metric): string {
  if (!metric || metric.value === null || !Number.isFinite(metric.value)) return '—';
  switch (metric.code) {
    case 'total_distance_m': return `${(metric.value / 1000).toLocaleString('zh-CN', { maximumFractionDigits: 2 })} km`;
    case 'total_cost_cents': return `¥${(metric.value / 100).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    default:
      return metric.unit === 'ratio' ? `${(metric.value * 100).toFixed(1)}%` : metric.value.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
  }
}
function jump(page: string) { window.dispatchEvent(new CustomEvent('twin:navigate', { detail: page })); }
function shortId(id: string) { return id.length > 12 ? `${id.slice(0, 8)}…` : id; }

export default function IntegrationPage({ initialView = 'negotiation' }: { initialView?: string }) {
  const stage = useStageRun();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selected, setSelected] = useState('');
  const [source, setSource] = useState('');
  const [run, setRun] = useState<Run | null>(null);
  const [view, setView] = useState(initialView);
  const [notice, setNotice] = useState('');
  const { busy, error, setError, run: action } = useTaskRunner();
  const [budget, setBudget] = useState(4000);
  const [seed, setSeed] = useState(0);
  const validInput = validInteger(budget, 100, 12000) && validInteger(seed, 0);
  async function loadScenarios(signal: AbortSignal) {
    const data = await request<{ items: Scenario[] }>('/integration/scenarios', { signal });
    signal.throwIfAborted();
    setScenarios(data.items);
    setSelected(previous => data.items.some(item => item.id === previous) ? previous : data.items[0]?.id ?? '');
  }
  async function refreshRun(runId: string, signal: AbortSignal): Promise<Run> {
    const latest = await request<Run>(`/integration/runs/${encodeURIComponent(runId)}`, { signal });
    signal.throwIfAborted(); setRun(latest);
    return latest;
  }
  async function followRun(runId: string, signal: AbortSignal) {
    await pollStatus(() => refreshRun(runId, signal), signal, setRun);
  }
  useEffect(() => {
    void action(async signal => {
      const last = readStored('integration_last_run');
      await Promise.all([
        loadScenarios(signal).catch(cause => { if (!signal.aborted) setError(String(cause)); }),
        last ? followRun(last, signal).catch(cause => { if (!signal.aborted) setError(String(cause)); }) : Promise.resolve(),
      ]);
    });
  }, []);
  async function importData(signal: AbortSignal) {
    const value = JSON.parse(source);
    const result = await request<{ status: string; scenario_id?: string; issues?: string[] }>('/integration/scenarios',
      { method: 'POST', body: JSON.stringify(value), signal });
    if (result.status !== 'checked' || !result.scenario_id) throw new Error(`资料不完整：${result.issues?.join('；') ?? result.status}`);
    await loadScenarios(signal); setSelected(result.scenario_id); setNotice('场景已校验并保存。');
  }
  async function importPriorityDelay(signal: AbortSignal) {
    const sample = await request<unknown>('/integration/priority-delay-template', { signal });
    const result = await request<{ status: string; scenario_id?: string; issues?: string[] }>('/integration/scenarios',
      { method: 'POST', body: JSON.stringify(sample), signal });
    if (result.status !== 'checked' || !result.scenario_id) throw new Error(`场景导入失败：${result.issues?.join('；') ?? result.status}`);
    await loadScenarios(signal); setSelected(result.scenario_id);
    setNotice('多收货点时效约束场景已准备，可执行联合求解。');
  }
  async function importSample(signal: AbortSignal) {
    const template = await request<unknown>('/integration/template', { signal });
    const result = await request<{ status: string; scenario_id?: string; issues?: string[] }>('/integration/scenarios',
      { method: 'POST', body: JSON.stringify(template), signal });
    if (result.status !== 'checked' || !result.scenario_id) throw new Error(`场景导入失败：${result.issues?.join('；') ?? result.status}`);
    await loadScenarios(signal); setSelected(result.scenario_id); setNotice('场景已准备完成。');
  }
  async function compute(signal: AbortSignal) {
    if (!selected || !validInput) throw new Error('预算须为 100–12000 的整数，种子须为非负整数。');
    setNotice('');
    const value = await request<Run>('/integration/runs?wait=false', { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey() },
      body: JSON.stringify({ schema_version: '2.0.0', scenario_id: selected, budget_ms: budget, seed, recoveries: [] }) });
    const saved = saveStored('integration_last_run', value.run_id);
    window.dispatchEvent(new CustomEvent('stageb:run', { detail: value.run_id }));
    signal.throwIfAborted(); setRun(value);
    if (!saved) setNotice('浏览器无法保存运行编号，请复制记录编号以便回查。');
    if (isPending(value.status)) await followRun(value.run_id, signal);
    signal.throwIfAborted();
    window.dispatchEvent(new CustomEvent('stageb:run', { detail: value.run_id }));
  }
  const negotiation = run?.negotiation?.result;
  const transcript = negotiation?.transcript ?? [];
  const warehouseIntervals = run?.warehouse_solution?.storage_allocations?.length ?? 0;
  const candidateTasks = run?.candidate?.task_assignments ?? [];
  const warehouses = candidateTasks.filter(t => t.task_kind === 'warehouse_task').length;
  const transports = candidateTasks.filter(t => t.task_kind === 'transport_task').length;
  const confirmed = new Map<string, Message>();
  for (const message of transcript) {
    if (message.kind === 'confirm') confirmed.set(message.task_id, message);
    if (message.kind === 'revoke') confirmed.delete(message.task_id);
  }
  async function revoke(taskId: string, signal: AbortSignal) {
    if (!run || !negotiation) return;
    const value = await request<Run>(`/integration/runs/${run.run_id}/revoke`, { method: 'POST', signal, body: JSON.stringify({
      schema_version: '2.0.0', task_id: taskId, now_s: Math.max(0, ...transcript.map(m => m.at_s)), expected_digest: negotiation.digest,
    }) });
    signal.throwIfAborted(); setRun(value);
  }
  const metrics = run?.observations?.metrics.values ?? [];
  const resultValid = run?.status === 'checked' && run.joint_validation?.valid === true;
  const handoffs = run?.observations?.handoffs ?? [];
  const maxHandoff = Math.max(1, ...handoffs.flatMap(h => [h.warehouse_ready_s, h.pickup_start_s ?? 0]));

  return <div className="integration-workbench">
    <SectionHeader title="仓储—运输联合调度" desc="协同仓储作业、车辆配送与冷链时效约束，生成并校验联合调度方案。" />

    <section className="panel integration-task-panel" aria-label="联合调度任务">
      <div className="integration-section-heading"><div><span className="integration-kicker">调度任务</span><h3>选择场景并开始优化</h3></div>
        {run && <span className={`pill ${resultValid ? 'pill-success' : isPending(run.status) ? 'pill-warning' : 'pill-neutral'}`}>{statusLabel(run.status)}</span>}</div>
      <div className="integration-task-form">
        <label className="integration-select-label">调度场景
          <select value={selected} onChange={e => setSelected(e.target.value)} disabled={busy}>
            <option value="">请选择调度场景</option>{scenarios.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </label>
        <button className="btn btn-primary integration-start-btn" disabled={busy || !selected || !validInput || !!run && isPending(run.status)}
          onClick={() => void action(compute)}>{busy ? '处理中…' : '计算并协商'}</button>
      </div>
      {selected && <div className="integration-source-line">数据来源：{scenarios.find(s => s.id === selected)?.source_kind === 'synthetic' ? '合成场景' : '导入场景'} <span>·</span> 求解器：仓储 CP-SAT / 运输 OR-Tools</div>}
      <details className="integration-advanced"><summary>场景管理与高级设置</summary>
        <div className="integration-advanced-body">
          <div className="integration-advanced-buttons"><button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => void action(importSample)}>准备内置场景</button>
            <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => void action(importPriorityDelay)}>准备时效约束场景</button>
            <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => void action(loadScenarios)}>刷新场景列表</button></div>
          <div className="integration-advanced-fields"><label>计算预算（毫秒）<input type="number" min={100} max={12000} step={1} disabled={busy} value={budget} onChange={e => setBudget(Number(e.target.value))} /></label>
            <label>随机种子<input type="number" min={0} step={1} disabled={busy} value={seed} onChange={e => setSeed(Number(e.target.value))} /></label></div>
          <details className="integration-file-import"><summary>导入 JSON 场景</summary>
            <input aria-label="导入场景文件" type="file" accept=".json,application/json" disabled={busy}
              onChange={event => { const file = event.target.files?.[0]; if (file) void action(async signal => { const text = await file.text(); signal.throwIfAborted(); setSource(text); }); }} />
            <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => void action(async signal => {
              const template = await request<unknown>('/integration/template', { signal }); signal.throwIfAborted(); setSource(JSON.stringify(template, null, 2));
            })}>加载场景模板</button>
            <textarea aria-label="场景 JSON" rows={5} disabled={busy} value={source} onChange={event => setSource(event.target.value)} placeholder="粘贴场景 JSON 或选择文件" />
            <button className="btn btn-primary btn-sm" disabled={busy || !source.trim()} onClick={() => void action(importData)}>校验并导入</button>
          </details>
        </div>
      </details>
      {!validInput && <p role="alert" className="callout callout-error">预算须为 100–12000 的整数，种子须为非负整数。</p>}
      {error && <p role="alert" className="callout callout-error">{error}</p>}
      {notice && <p role="status" className="muted-line">{notice}</p>}
    </section>

    <section className="panel integration-process-panel" aria-label="联合求解状态">
      <div className="integration-section-heading"><div><span className="integration-kicker">联合决策</span><h3>求解与校验</h3></div>
        {run && <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => void action(signal => followRun(run.run_id, signal))}>刷新运行状态</button>}</div>
      <div className="integration-process-grid">
        <div className="integration-process-node"><span className="integration-process-icon">仓</span><div><strong>仓储排程</strong><small>CP-SAT</small></div><b>{run?.warehouse_solution?.status ?? '待求解'}</b></div>
        <div className="integration-process-node"><span className="integration-process-icon">运</span><div><strong>运输规划</strong><small>OR-Tools</small></div><b>{run?.transport_solution?.status ?? '待求解'}</b></div>
        <div className={`integration-process-node ${resultValid ? 'integration-process-success' : ''}`}><span className="integration-process-icon">验</span><div><strong>联合校验</strong><small>一致性与约束</small></div>
          <b>{run?.joint_validation ? run.joint_validation.valid ? '已通过' : '未通过' : '待校验'}</b></div>
      </div>
      <div className="integration-process-foot">
        <span>仓储任务 <b>{run?.candidate ? warehouses : '—'}</b></span>
        <span>运输任务 <b>{run?.candidate ? transports : '—'}</b></span>
        <span>资源占用区间 <b>{run?.warehouse_solution ? warehouseIntervals : '—'}</b></span>
        <span>协商确认 <b>{negotiation ? confirmed.size : '—'}</b></span>
      </div>
      {run && <details className="integration-record-details"><summary>运行详情</summary>
        <div className="integration-record-data"><span>记录编号：{run.run_id}</span><span>任务编号：{run.job_id ?? '—'}</span>
          <span>方案编号：{run.candidate?.id ?? '—'}</span><span>运行状态：{statusLabel(run.status)}{run.reason ? ` · ${run.reason}` : ''}</span>
          <span>来源：{run.source_kind === 'synthetic' ? '合成场景' : run.source_kind === 'enterprise' ? '企业来源声明' : run.source_kind ?? '—'}</span>
          <span>约束违例数：{run.joint_validation?.violations.length ?? '—'}</span></div>
      </details>}
    </section>

    <section className="panel integration-results-panel" aria-label="联合调度结果">
      <div className="integration-section-heading"><div><span className="integration-kicker">决策结果</span><h3>调度方案指标</h3></div>
        {run?.observations && <span className="pill pill-info">计划数据</span>}</div>
      <div className="integration-metric-grid">
        {importantMetrics.map(({ code, title }) => {
          const metric = metrics.find(m => m.code === code);
          return <div key={code} className="integration-metric-card"><span>{title}</span><strong>{metricValue(metric)}</strong>
            <small>{metric?.value === null && metric.reason ? '暂无有效测量值' : metric?.value != null ? `样本数 ${metric.sample_count}` : '等待结果'}</small></div>;
        })}
      </div>
      <div className="integration-result-bottom">
        <div className="integration-validation"><strong>联合方案校验</strong><span className={resultValid ? 'text-ok' : run?.joint_validation ? 'text-bad' : 'text-na'}>
          {run?.joint_validation ? run.joint_validation.valid ? '约束校验通过' : '存在约束违例' : '等待校验'}</span></div>
        <span className="integration-result-note">{run?.observations ? '以上为求解方案的计划口径' : '计算完成后展示方案指标'}</span>
      </div>
      {resultValid && <div className="integration-next-actions"><div><strong>联合方案已就绪</strong><small>可查看仓储、运输结果或创建可回放的模拟运行。</small></div>
        <div className="integration-action-buttons"><button className="btn btn-ghost btn-sm" onClick={() => jump('warehouseOps')}>仓储作业</button>
          <button className="btn btn-ghost btn-sm" onClick={() => jump('vehicles')}>车辆路线</button></div></div>}
      {resultValid && <RunBar state={stage} allowCreate />}
    </section>

    {run && <section className="panel integration-detail-panel" aria-label="调度方案明细">
      <div className="integration-section-heading"><div><span className="integration-kicker">运行分析</span><h3>仓运协同与协商明细</h3></div></div>
      {handoffs.length > 0 && <div className="integration-handoff-section">
        <div className="integration-subhead"><h4>仓储—运输交接</h4><span>秒 · 计划时间</span></div>
        <div className="integration-handoff-legend"><span><i className="integration-ready-dot" />出库就绪</span><span><i className="integration-pickup-dot" />提货开始</span></div>
        <div className="integration-handoff-list">{handoffs.slice(0, 6).map(h => <div className="integration-handoff-row" key={h.task_id}>
          <span title={h.task_id}>{shortId(h.task_id)}</span><div className="integration-handoff-track">
            <i className="integration-handoff-mark integration-handoff-ready" style={{ left: `${Math.min(98, 100 * h.warehouse_ready_s / maxHandoff)}%` }} title={`仓储就绪 ${h.warehouse_ready_s} 秒`} />
            {h.pickup_start_s !== null && <i className="integration-handoff-mark integration-handoff-pickup" style={{ left: `${Math.min(98, 100 * h.pickup_start_s / maxHandoff)}%` }} title={`提货开始 ${h.pickup_start_s} 秒`} />}
          </div><span>{h.pickup_start_s === null ? '未安排提货' : `${h.warehouse_ready_s}s → ${h.pickup_start_s}s`}</span>
        </div>)}</div>
        {handoffs.length > 6 && <small className="muted-line">其余 {handoffs.length - 6} 项可在冷链与交接明细中查看。</small>}
      </div>}
      <div className="seg integration-tabs" role="group" aria-label="调度分析分类">
        {([['negotiation', '协商记录'], ['metrics', '详细指标'], ['coldchain', '冷链与交接']] as const).map(([key, title]) =>
          <button key={key} className={`seg-btn ${view === key ? 'is-active' : ''}`} onClick={() => setView(key)}>{title}</button>)}
      </div>
      {view === 'negotiation' && <div className="integration-analysis-content">
        {!negotiation ? <p className="muted-line">当前运行尚未生成协商记录。</p> : <>
          <div className="integration-negotiation-summary"><span><b>{confirmed.size}</b><small>已确认任务</small></span>
            <span><b>{transcript.length}</b><small>协商消息</small></span><span><b>{statusLabel(negotiation.status)}</b><small>协商状态</small></span></div>
          {confirmed.size > 0 && <details className="integration-subdetails"><summary>已确认任务（{confirmed.size}）</summary>
            <div className="integration-confirmations">{[...confirmed].map(([id, message]) => <div key={id} className="integration-confirmation-row">
              <span title={id}>{shortId(id)} · {roles[message.role] ?? message.role}</span>
              <button disabled={busy} className="btn btn-ghost btn-sm" onClick={() => void action(signal => revoke(id, signal))}>撤销确认</button></div>)}</div>
          </details>}
          <details className="integration-subdetails"><summary>完整协商日志（{transcript.length}）</summary>
            <div className="table-wrap"><table><thead><tr><th>序号</th><th>时间（秒）</th><th>角色</th><th>动作</th><th>任务</th><th>记录</th></tr></thead>
              <tbody>{transcript.map(m => <tr key={m.seq}><td>{m.seq}</td><td>{m.at_s}</td><td>{roles[m.role] ?? m.role}</td><td>{messages[m.kind] ?? m.kind}</td>
                <td title={m.task_id}>{shortId(m.task_id)}</td><td style={{ overflowWrap: 'anywhere', maxWidth: 450 }}>{m.detail}</td></tr>)}</tbody></table></div>
            <small className="integration-digest">协商摘要：{negotiation.digest}</small>
          </details>
        </>}
      </div>}
      {view === 'metrics' && <div className="integration-analysis-content">{!run.observations ? <p className="muted-line">没有通过校验的观测结果。</p> : <div className="table-wrap"><table>
        <thead><tr><th>指标</th><th>数值</th><th>单位</th><th>样本数</th><th>缺失原因</th></tr></thead>
        <tbody>{metrics.map(m => <tr key={m.code}><td>{labels[m.code] ?? m.code}</td>
          <td>{metricValue(m)}</td><td>{m.unit}</td><td>{m.sample_count}</td>
          <td>{m.reason === 'missing_data' ? '缺少测量证据' : m.reason === 'division_by_zero' ? '分母为零' : m.reason ?? '—'}</td></tr>)}</tbody>
      </table></div>}</div>}
      {view === 'coldchain' && <div className="integration-analysis-content">{!run.observations ? <p className="muted-line">尚无冷链约束观测结果。</p> : <>
        <p className="muted-line">规则版本：{run.observations.coldchain.rule_version}</p><h4>库存占用区间</h4>
        <div className="table-wrap"><table><thead><tr><th>批次</th><th>库位</th><th>开始（秒）</th><th>结束（秒）</th></tr></thead><tbody>
          {run.observations.coldchain.occupancies.map(o => <tr key={o.occupancy_id}><td>{o.batch_id}</td><td>{o.location_id}</td><td>{o.start_s}</td><td>{o.end_s}</td></tr>)}
        </tbody></table></div><h4>仓运交接</h4><div className="table-wrap"><table><thead><tr><th>任务</th><th>仓储完成（秒）</th><th>提货开始（秒）</th></tr></thead><tbody>
          {handoffs.map(h => <tr key={h.task_id}><td>{h.task_id}</td><td>{h.warehouse_ready_s}</td><td>{h.pickup_start_s ?? '缺少证据'}</td></tr>)}
        </tbody></table></div>
      </>}</div>}
    </section>}
  </div>;
}

export function ObservationPage() { return <IntegrationPage initialView="metrics" />; }
export function ColdChainPage() { return <IntegrationPage initialView="coldchain" />; }
