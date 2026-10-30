import { useEffect, useState } from 'react';
import { candidateAllowed, decideDelay, loadSimulation, selectIncident, submitDelay, short } from './api';
import type { SimIncident } from './api';
import { RunBar, useStageRun } from './RunContext';
import { readStored } from '../../lib/asyncJobs';

/** Stage A simulation approval deliberately does not submit a real dispatch plan. */
export default function StageIncident() {
  const stage = useStageRun();
  const [vehicle, setVehicle] = useState('');
  const [occurredAt, setOccurredAt] = useState(0);
  const [delay, setDelay] = useState(60);
  const [reason, setReason] = useState('模拟运输途中延误');
  const [proposal, setProposal] = useState<SimIncident | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const incident = proposal ?? selectIncident(stage.simulation);
  useEffect(() => {
    const departure = stage.simulation?.events.find(event => event.kind === 'vehicle_departure' && !!event.vehicle_id);
    if (departure) { setVehicle(departure.vehicle_id!); setOccurredAt(departure.time_s + 1); }
    // Transfer Agent's read-only preview into the EXISTING human-confirmed form.
    // Stored input is never trusted as authorization and is revalidated by the backend.
    const saved = readStored('dispatch_delay_handoff');
    if (saved && stage.simulation) {
      try {
        const handoff: unknown = JSON.parse(saved);
        if (handoff && typeof handoff === 'object' && 'run_id' in handoff
          && 'vehicle_id' in handoff && 'time_s' in handoff && 'delay_s' in handoff
          && handoff.run_id === stage.runId && typeof handoff.vehicle_id === 'string'
          && stage.simulation.tracks.some(track => track.vehicle_id === handoff.vehicle_id)
          && typeof handoff.time_s === 'number' && Number.isSafeInteger(handoff.time_s)
          && typeof handoff.delay_s === 'number' && Number.isSafeInteger(handoff.delay_s)) {
          setVehicle(handoff.vehicle_id); setOccurredAt(handoff.time_s); setDelay(handoff.delay_s);
          setNotice('已带入调度 Agent 的延误预分析参数；登记仍须由你确认。');
        }
      } catch { /* Invalid local data is ignored; backend remains the authority. */ }
      try { localStorage.removeItem('dispatch_delay_handoff'); } catch { /* optional */ }
    }
  }, [stage.simulation?.simulation_id]);
  const valid = Number.isInteger(occurredAt) && occurredAt >= 0 && occurredAt <= (stage.simulation?.horizon_s ?? 0)
    && Number.isInteger(delay) && delay > 0 && reason.trim().length > 0;
  async function run(task: () => Promise<void>) {
    setBusy(true); setError(''); setNotice('');
    try { await task(); } catch (cause) { setError(String(cause)); } finally { setBusy(false); }
  }
  async function refresh() {
    const updated = await loadSimulation(stage.runId);
    stage.setSimulation(updated);
  }
  async function create() {
    const chosen = vehicle || stage.simulation?.tracks[0]?.vehicle_id;
    if (!chosen || !valid) throw new Error('请选择车辆并填写有效发生时间、延误时长与原因。');
    if (!window.confirm('确认在隔离模拟中登记运输延误？该操作会向当前连接的数据库写入异常事件，不会修改真实派车和库存。')) return;
    const result = await submitDelay(stage.runId, chosen, occurredAt, delay, reason);
    setProposal(result); await refresh(); setNotice('模拟延误已登记，候选方案等待人工决策。');
  }
  async function decide(kind: 'approve' | 'reject') {
    if (!incident || incident.status !== 'pending') return;
    if (!window.confirm(`确认${kind === 'approve' ? '批准' : '拒绝'}模拟延误方案？批准只切换模拟版本，不修改真实派车。`)) return;
    const result = await decideDelay(stage.runId, incident, kind);
    setProposal(result); await refresh(); setNotice(kind === 'approve' ? '模拟方案已批准，回放生效版本更新。' : '模拟方案已拒绝，保留原方案。');
  }
  const impact = incident?.impact;
  const delays = Object.entries(impact?.after_eta_s ?? {}).map(([order, after]) => ({ order,
    shift: after - (impact?.before_eta_s?.[order] ?? after) }));
  return <section className="panel" aria-label="模拟车辆延误及人工审批">
    <h3>车辆延误 · 人机协同处置</h3>
    <p>Stage A 合法事件 <code>transport_delay</code>；先生成影响候选，再由调度员批准或拒绝。一次模拟仅支持一条延误。</p>
    <RunBar state={stage} allowCreate />
    {stage.simulation && <>
      <div className="form-grid">
        <label>延误车辆 <select aria-label="延误车辆" value={vehicle} disabled={Boolean(incident) || busy}
          onChange={event => {
            setVehicle(event.target.value);
            const departure = stage.simulation?.events.find(item => item.kind === 'vehicle_departure' && item.vehicle_id === event.target.value);
            if (departure) setOccurredAt(departure.time_s + 1);
          }}><option value="">自动选择首辆 / 请选择</option>
          {stage.simulation.tracks.map(track => <option key={track.vehicle_id} value={track.vehicle_id}>{short(track.vehicle_id)}</option>)}</select></label>
        <label>发生时刻（秒）<input type="number" min={0} max={stage.simulation.horizon_s} value={occurredAt}
          disabled={Boolean(incident) || busy} onChange={event => setOccurredAt(Number(event.target.value))} /></label>
        <label>延误时长（秒）<input type="number" min={1} value={delay} disabled={Boolean(incident) || busy} onChange={event => setDelay(Number(event.target.value))} /></label>
        <label>异常原因 <input value={reason} disabled={Boolean(incident) || busy} onChange={event => setReason(event.target.value)} /></label>
      </div>
      <p className="s5-muted">延误发生时刻必须位于所选车辆运输途中；如不满足，后端会拒绝，不能伪造在途状态。</p>
      {!incident && <button className="btn btn-primary" disabled={!valid || busy} onClick={() => void run(create)}>触发模拟延误并分析</button>}
      {incident && <><p role="status">异常：{short(incident.id)} · 状态：{incident.status} · 候选独立校验：{incident.proposal_valid ? '通过' : '未通过/未返回'}</p>
        <p>受影响订单：{impact?.affected_order_ids?.length ?? 0} · 最大预计顺延：{delays.length ? Math.max(...delays.map(d => d.shift)) : '—'} 秒</p>
        {delays.length > 0 && <div className="table-wrap"><table><thead><tr><th>订单</th><th>预计顺延（秒）</th></tr></thead><tbody>
          {delays.map(item => <tr key={item.order}><td>{short(item.order)}</td><td>{item.shift}</td></tr>)}</tbody></table></div>}
        <p className="s5-muted">候选策略：{incident.strategy === 'simulated_local_reroute' ? '局部路线重新优化（剩余停靠顺序已改变）'
          : incident.strategy === 'simulated_local_retimed' ? '局部求解接续（停靠顺序未变）'
          : '安全等待＋顺延（局部优化不可行或未优于保底方案）'}。{incident.s1_local_solver?.reason ? ` 局部求解状态：${incident.s1_local_solver.reason}` : ''}仅影响数据库模拟，不写入真实运营排程。</p>
        {incident.status === 'pending' && <div className="stageb-actions">
          <button className="btn btn-primary" disabled={busy || !candidateAllowed(incident)} onClick={() => void run(() => decide('approve'))}>人工批准模拟方案</button>
          <button className="btn btn-ghost" disabled={busy} onClick={() => void run(() => decide('reject'))}>拒绝 · 保留原方案</button></div>}
        </>}
    </>}
    <button className="btn btn-ghost btn-sm" disabled={busy || !stage.simulation} onClick={() => void run(refresh)}>刷新审批记录</button>
    {error && <p role="alert" className="callout callout-error">{error}</p>}
    {notice && <p role="status">{notice}</p>}
  </section>;
}
