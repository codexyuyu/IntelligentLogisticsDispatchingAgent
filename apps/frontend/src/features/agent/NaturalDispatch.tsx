import DefenseImpactPanel from '../stageB/DefenseImpactPanel';
import type { Comparison } from '../stageB/ProposalComparison';
import { useCallback, useEffect, useState } from 'react';
import { request } from '../../api';
import { readStored, saveStored } from '../../lib/asyncJobs';
import { loadSimulation, runKey, short, type VehicleTrack } from '../stageB/api';

type Task = {
  task_id: string; source_run_id: string; candidate_run_id: string | null;
  status: 'draft' | 'solving' | 'ready' | 'approved' | 'rejected' | 'failed';
  row_version: number; instruction: string;
  intent: { action: string; vehicle_id?: string; time_s?: number; delay_s?: number };
  parser: 'deepseek_tool_call' | 'rule_based';
  evidence: Record<string, unknown>; incident_id: string | null;
};
type TaskList = { items: Task[] };
const taskKey = 'natural_dispatch_last_task';
const statusLabel: Record<Task['status'], string> = {
  draft: '待生成候选', solving: '求解中', ready: '待人工审批',
  approved: '已批准', rejected: '已拒绝', failed: '求解失败',
};
function nav(page: string) { window.dispatchEvent(new CustomEvent('twin:navigate', { detail: page })); }
function fmt(value: unknown) {
  if (typeof value === 'number') return value.toLocaleString('zh-CN');
  return value === null || value === undefined ? '—' : String(value);
}

export default function NaturalDispatch({ currentRun }: { currentRun: string }) {
  const [instruction, setInstruction] = useState('请按当前场景的订单与冷链约束重新进行仓储运输联合调度。');
  const [task, setTask] = useState<Task | null>(null);
  const [history, setHistory] = useState<Task[]>([]);
  const [busy, setBusy] = useState(false);
  const [vehicles, setVehicles] = useState<VehicleTrack[]>([]);
  const [vehicleId, setVehicleId] = useState('');
  const [atSecond, setAtSecond] = useState(0);
  const [delaySecond, setDelaySecond] = useState(90);
  const [error, setError] = useState('');
  const load = useCallback(async (taskId: string) => {
    const value = await request<Task>(`/agents/dispatch-tasks/${encodeURIComponent(taskId)}`);
    setTask(value);
    return value;
  }, []);
  const refreshHistory = useCallback(async () => {
    const response = await request<TaskList>('/agents/dispatch-tasks');
    setHistory(response.items ?? []);
  }, []);
  useEffect(() => {
    const saved = readStored(taskKey);
    if (saved) void load(saved).catch(() => { /* Stale task stays out of the active view. */ });
    void refreshHistory().catch(() => { /* Audit list is optional. */ });
  }, [load, refreshHistory]);
  useEffect(() => {
    if (!currentRun) { setVehicles([]); setVehicleId(''); return; }
    let cancelled = false;
    void loadSimulation(currentRun).then(sim => {
      if (cancelled) return;
      const tracks = sim.tracks ?? [];
      setVehicles(tracks);
      const first = tracks.find(track => track.segments.some(s => s.end_s > s.start_s));
      if (first) {
        setVehicleId(first.vehicle_id);
        const segment = first.segments.find(s => s.end_s - s.start_s >= 2);
        if (segment) setAtSecond(Math.floor((segment.start_s + segment.end_s) / 2));
      }
    }).catch(() => { if (!cancelled) { setVehicles([]); setVehicleId(''); } });
    return () => { cancelled = true; };
  }, [currentRun]);
  useEffect(() => {
    if (!task || task.status !== 'solving') return;
    const timer = window.setInterval(() => {
      void load(task.task_id).catch(cause => {
        setError(cause instanceof Error ? cause.message : '读取求解状态失败');
      });
    }, 3500);
    return () => window.clearInterval(timer);
  }, [task, load]);

  async function create() {
    if (!currentRun || !instruction.trim()) return;
    setBusy(true); setError('');
    try {
      const response = await request<Task>('/agents/dispatch-tasks', {
        method: 'POST', body: JSON.stringify({ schema_version: '2.0.0', run_id: currentRun,
          message: instruction.trim() }),
      });
      setTask(response); saveStored(taskKey, response.task_id);
      await refreshHistory();
    } catch (cause) { setError(cause instanceof Error ? cause.message : '指令无法识别'); }
    finally { setBusy(false); }
  }
  async function act(action: 'preview' | 'approve' | 'reject') {
    if (!task || busy) return;
    setBusy(true); setError('');
    try {
      const response = await request<Task>(`/agents/dispatch-tasks/${encodeURIComponent(task.task_id)}/${action}`, {
        method: 'POST', body: JSON.stringify({ expected_row_version: task.row_version }),
      });
      setTask(response);
      if (response.status === 'approved') {
        const id = response.candidate_run_id ?? response.source_run_id;
        saveStored(runKey, id);
        window.dispatchEvent(new CustomEvent('stageb:run', { detail: id }));
      }
      await refreshHistory();
    } catch (cause) { setError(cause instanceof Error ? cause.message : '操作失败'); }
    finally { setBusy(false); }
  }
  const evidence = task?.evidence ?? {};
  const comparison = evidence.comparison as Record<string, unknown> | undefined;
  const observations = evidence.observations as Record<string, unknown> | undefined;
  const validation = evidence.joint_validation as { valid?: boolean } | undefined;
  const impact = evidence.impact as Record<string, unknown> | undefined;
  return <section className="panel" style={{ display: 'grid', gap: 14 }}>
    <div>
      <h3>自然语言调度任务</h3>
      <p className="muted">根据当前联合运行解析任务、生成候选并校验，方案经人工批准后生效于模拟运行。</p>
    </div>
    <label htmlFor="nl-dispatch-instruction">调度指令</label>
    <textarea id="nl-dispatch-instruction" rows={3} value={instruction}
      onChange={e => setInstruction(e.target.value)} placeholder="输入当前场景的调度需求" />
    <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
      <button className="btn btn-ghost btn-sm" onClick={() => setInstruction('按当前场景的全部订单和既有冷链约束重新进行联合调度。')}>联合求解</button>
      {vehicles.length > 0 && <button className="btn btn-ghost btn-sm" onClick={() => setInstruction(`车辆 ${vehicleId} 在第 ${atSecond} 秒延误 ${delaySecond} 秒，请分析局部重规划。`)}>车辆延误重规划</button>}
      <button className="btn btn-primary" disabled={busy || !instruction.trim() || !currentRun} onClick={() => void create()}>
        {busy ? '处理中…' : '解析调度任务'}
      </button>
    </div>
    {vehicles.length > 0 && <details>
      <summary>选择延误车辆与发生时刻</summary>
      <div className="row" style={{ gap: 10, flexWrap: 'wrap', marginTop: 10 }}>
        <label>车辆 <select value={vehicleId} onChange={e => {
          setVehicleId(e.target.value);
          const track = vehicles.find(v => v.vehicle_id === e.target.value);
          const segment = track?.segments.find(s => s.end_s - s.start_s >= 2);
          if (segment) setAtSecond(Math.floor((segment.start_s + segment.end_s) / 2));
        }}>{vehicles.map(v => <option key={v.vehicle_id} value={v.vehicle_id}>{short(v.vehicle_id)}</option>)}</select></label>
        <label>发生秒数 <input type="number" min={0} value={atSecond} onChange={e => setAtSecond(Number(e.target.value))} /></label>
        <label>延误秒数 <input type="number" min={1} max={3600} value={delaySecond} onChange={e => setDelaySecond(Number(e.target.value))} /></label>
        <button className="btn btn-ghost btn-sm" onClick={() => setInstruction(`车辆 ${vehicleId} 在第 ${atSecond} 秒延误 ${delaySecond} 秒，请分析局部重规划。`)}>填入调度指令</button>
      </div>
    </details>}
    {!currentRun && <p className="callout">请先在「联合调度」完成一次 checked 运行，调度助手将关联真实场景。</p>}
    {error && <p className="callout callout-error" role="alert">{error}</p>}
    {task && <div className="panel" style={{ display: 'grid', gap: 12 }}>
      <div className="row" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
        <strong>{task.intent.action === 'joint_dispatch' ? '联合调度候选' : '车辆延误重规划候选'}</strong>
        <span>{statusLabel[task.status]}</span>
      </div>
      <div className="muted">任务编号：{short(task.task_id)} · 源运行：{short(task.source_run_id)} · 解析方式：{task.parser === 'deepseek_tool_call' ? 'DeepSeek 工具解析' : '规则解析'}</div>
      <p style={{ whiteSpace: 'pre-wrap' }}>{task.instruction}</p>
      <div className="row" style={{ flexWrap: 'wrap', gap: 12 }}>
        <span>任务类型：{task.intent.action === 'joint_dispatch' ? '当前场景联合求解' : '在途局部重规划'}</span>
        {task.intent.vehicle_id && <span>车辆：{short(task.intent.vehicle_id)}</span>}
        {typeof task.intent.time_s === 'number' && <span>发生：{fmt(task.intent.time_s)} 秒</span>}
        {typeof task.intent.delay_s === 'number' && <span>延误：{fmt(task.intent.delay_s)} 秒</span>}
      </div>
      {task.candidate_run_id && <div>候选联合运行：{short(task.candidate_run_id)}</div>}
      {task.status === 'solving' && <p role="status" className="muted">求解器正在生成实际联合方案，系统将自动读取校验结果。</p>}
      {task.status === 'failed' && <p role="alert" className="callout callout-error">求解未通过：{fmt(evidence.reason)}</p>}
      {task.status === 'ready' || task.status === 'approved' || task.status === 'rejected' ? <>
        <div className="row" style={{ flexWrap: 'wrap', gap: 14 }}>
          {task.intent.action === 'joint_dispatch' ? <>
            <span>联合校验：{validation?.valid === true ? '通过' : '未通过'}</span>
            <span>求解结果：{fmt(evidence.status)}</span>
          </> : <>
            <span>候选策略：{fmt(evidence.strategy)}</span>
            <span>路线改变：{evidence.route_changed === true ? '是' : '否'}</span>
            <span>影响说明：{fmt((impact?.affected_order_ids as unknown[] | undefined)?.length)} 单</span>
          </>}
        </div>
        {typeof evidence.notice === 'string' && <p className="muted">{evidence.notice}</p>}
        {observations && <div>
          <strong>联合求解指标</strong>
          <div className="row" style={{ flexWrap: 'wrap', gap: 14, marginTop: 8 }}>
            {((observations.metrics as { values?: { code: string; value: number | null; unit?: string }[] } | undefined)?.values ?? [])
              .filter(m => ['total_distance_m', 'total_cost_cents', 'on_time_delivery_rate', 'demand_satisfaction_rate'].includes(m.code))
              .map(m => <span key={m.code}>{({ total_distance_m: '配送距离', total_cost_cents: '运输成本', on_time_delivery_rate: '准时率', demand_satisfaction_rate: '订单满足率' } as Record<string,string>)[m.code] ?? m.code}：
                {m.value === null ? '—' : m.code === 'total_distance_m' ? `${(m.value / 1000).toFixed(2)} km` : m.code === 'total_cost_cents' ? `¥${(m.value / 100).toFixed(2)}` : m.unit === 'ratio' ? `${(m.value * 100).toFixed(1)}%` : fmt(m.value)}</span>)}
          </div>
          <details><summary>完整指标依据</summary><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: 280, overflowY: 'auto' }}>{JSON.stringify(observations, null, 2)}</pre></details></div>}
        {comparison && typeof comparison === 'object' && 'baseline' in comparison && 'simple_hold' in comparison
          && 'candidate' in comparison && 'delta_vs_hold' in comparison && <>
          <DefenseImpactPanel comparison={comparison as unknown as Comparison} validated={true} />
          <details><summary>完整方案对照原始证据</summary><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: 360, overflowY: 'auto' }}>{JSON.stringify(comparison, null, 2)}</pre></details>
        </>}
        {task.intent.action === 'joint_dispatch' && <p className="muted" style={{ padding: 10, borderRadius: 8, background: '#f2f7f3' }}>
          <strong>方案指标：</strong>本任务尚无同条件基线；异常后的收益请查看「异常处置」对比。
        </p>}
        {evidence.candidate_stops != null && <details><summary>候选车辆停靠顺序与时间</summary><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: 340, overflowY: 'auto' }}>{JSON.stringify(evidence.candidate_stops, null, 2)}</pre></details>}
        {task.intent.action === 'joint_dispatch' && <details><summary>求解器候选路线与交接证据</summary><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: 340, overflowY: 'auto' }}>{JSON.stringify(evidence.transport_solution, null, 2)}</pre></details>}
      </> : null}
      <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
        {task.status === 'draft' && <button className="btn btn-primary" disabled={busy} onClick={() => void act('preview')}>生成并校验候选方案</button>}
        {task.status === 'ready' && <>
          <button className="btn btn-primary" disabled={busy} onClick={() => void act('approve')}>人工批准并应用于模拟</button>
          <button className="btn btn-ghost" disabled={busy} onClick={() => void act('reject')}>拒绝候选方案</button>
        </>}
        {task.status === 'approved' && <>
          <button className="btn btn-ghost" onClick={() => nav('simulations')}>查看模拟回放</button>
          <button className="btn btn-ghost" onClick={() => nav('events')}>查看异常记录</button>
        </>}
        <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => void load(task.task_id).catch(cause => setError(String(cause)))}>更新任务状态</button>
      </div>
      <small className="muted">仅对当前场景及已有车辆道路生效；指定新目的地、单车指派及自定义优先权重尚不支持。</small>
    </div>}
    {history.length > 0 && <details>
      <summary>调度任务历史（{history.length}）</summary>
      <div style={{ display: 'grid', gap: 7, paddingTop: 8 }}>
        {history.map(item => <button key={item.task_id} className="btn btn-ghost btn-sm"
          style={{ textAlign: 'left' }} onClick={() => { setTask(item); saveStored(taskKey, item.task_id); }}>
          {short(item.task_id)} · {statusLabel[item.status]} · {item.intent.action === 'joint_dispatch' ? '联合求解' : '延误重规划'}
        </button>)}
      </div>
    </details>}
  </section>;
}
