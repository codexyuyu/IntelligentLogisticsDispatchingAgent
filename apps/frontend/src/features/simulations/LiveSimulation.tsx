import { useEffect, useState } from 'react';
import { request, idempotencyKey } from '../../api';
import SectionHeader from '../../components/SectionHeader';
import { pollStatus, readStored, saveStored, useTaskRunner, validInteger } from '../../lib/asyncJobs';
import { statusLabel } from '../../lib/labels';

type Event = { event_id: string; time_s: number; kind: string; vehicle_id: string | null; order_id: string | null };
type Result = { status: string; final_time_s: number; events: Event[]; delivered_order_ids: string[]; seed: number };
type SimulationJob = { job_id: string; status: string; error_message?: string };
const savedJobKey = 'dsh_simulation_job_id';
const eventLabels: Record<string, string> = { arrival: '到达', departure: '出发', delivery: '送达',
  vehicle_arrived: '车辆到达', vehicle_departed: '车辆出发', order_delivered: '订单送达' };

export default function LiveSimulation() {
  const [job, setJob] = useState(() => readStored('dsh_transport_job_id') ?? '');
  const [simulationId, setSimulationId] = useState(() => readStored(savedJobKey) ?? '');
  const [jobStatus, setJobStatus] = useState('');
  const [seed, setSeed] = useState(0);
  const [until, setUntil] = useState(86400);
  const [result, setResult] = useState<Result | null>(null);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [notice, setNotice] = useState('');
  const { busy, error, run } = useTaskRunner();
  const validInput = validInteger(seed, 0) && validInteger(until, 1);

  async function recover(id: string, signal: AbortSignal) {
    const state = await pollStatus(() => request<SimulationJob>(`/jobs/${encodeURIComponent(id)}`, { signal }), signal,
      latest => setJobStatus(latest.status));
    if (state.status !== 'completed') throw new Error(state.error_message ?? `仿真任务${statusLabel(state.status)}`);
    const response = await request<{ kind: string; value: Result }>(`/jobs/${encodeURIComponent(id)}/result`, { signal });
    signal.throwIfAborted();
    if (response.kind !== 'simulation' || !response.value || !Array.isArray(response.value.events)
      || !Array.isArray(response.value.delivered_order_ids) || !Number.isFinite(response.value.final_time_s)) {
      throw new Error('任务返回的内容不是有效仿真结果，请核对任务编号。');
    }
    setResult(response.value); setCursor(0); setPlaying(false);
  }
  useEffect(() => {
    const id = readStored(savedJobKey);
    if (id) void run(signal => recover(id, signal));
  }, []);
  useEffect(() => {
    if (!playing || !result) return;
    if (cursor >= result.events.length) { setPlaying(false); return; }
    const timer = setTimeout(() => setCursor(value => value + 1), 500);
    return () => clearTimeout(timer);
  }, [playing, result, cursor]);

  async function simulate(signal: AbortSignal) {
    if (!job.trim() || !validInput) throw new Error('请填写运输任务编号；种子须为非负整数，结束时间须为正整数。');
    setPlaying(false); setNotice('');
    const source = await request<{ kind: string; value: { candidate: unknown; stops: unknown[]; validation?: { valid: boolean } } }>(`/jobs/${encodeURIComponent(job.trim())}/result`, { signal });
    if (source.kind !== 'transport' || !source.value?.candidate || !source.value.validation?.valid) throw new Error('请选择已完成且独立校验通过的运输任务。');
    signal.throwIfAborted();
    const accepted = await request<SimulationJob>('/simulations', { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey() },
      body: JSON.stringify({ schema_version: '2.0.0', plan: source.value.candidate, stops: source.value.stops, seed, until_s: until }) });
    const saved = saveStored(savedJobKey, accepted.job_id);
    signal.throwIfAborted();
    setSimulationId(accepted.job_id); setJobStatus(accepted.status); setResult(null); setCursor(0);
    if (!saved) setNotice('浏览器无法保存任务编号，请复制编号后再离开本页。');
    await recover(accepted.job_id, signal);
  }
  return <div><SectionHeader title="真实运输仿真与回放" desc="读取已求解的运输任务，由后台 SimPy 工作进程执行，按实际事件记录回放。离开本页停止等待，后台任务仍可回查。" />
    <section className="panel">
      <label>运输任务 ID <input disabled={busy} value={job} onChange={e => setJob(e.target.value)} placeholder="从运输计划复制已完成的任务 ID" /></label>
      <button className="btn btn-ghost" disabled={busy} onClick={() => {
        const latest = readStored('dsh_transport_job_id');
        if (latest) { setJob(latest); setNotice('已带入最近的运输任务。'); }
        else setNotice('尚无运输任务，请先在运输计划中完成求解。');
      }}>带入最近运输任务</button>
      <label>种子 <input disabled={busy} type="number" min={0} step={1} value={seed} onChange={e => setSeed(Number(e.target.value))} /></label>
      <label>结束时间（秒）<input disabled={busy} type="number" min={1} step={1} value={until} onChange={e => setUntil(Number(e.target.value))} /></label>
      {!validInput && <p role="alert">种子须为非负整数，结束时间须为正整数。</p>}
      <button className="btn btn-primary" disabled={busy || !job.trim() || !validInput} onClick={() => void run(simulate)}>{busy ? '正在读取仿真…' : '运行仿真'}</button>
      {notice && <p role="status">{notice}</p>}
      {simulationId && <p>仿真任务 ID：<code>{simulationId}</code> · {statusLabel(jobStatus)}
        <button className="btn btn-ghost" disabled={busy} onClick={() => void run(signal => recover(simulationId, signal))}>刷新仿真状态</button></p>}
      {error && <p role="alert">{error}</p>}
      {result && <><p>状态：{statusLabel(result.status)}；最终时间：{result.final_time_s} 秒；送达订单：{result.delivered_order_ids.length}；事件：{result.events.length}</p>
        <button className="btn btn-ghost" disabled={!result.events.length} onClick={() => { if (!playing && cursor >= result.events.length) setCursor(0); setPlaying(!playing); }}>{playing ? '暂停' : '播放'}</button>
        <button className="btn btn-ghost" onClick={() => { setPlaying(false); setCursor(0); }}>回到起点</button>
        <input aria-label="事件回放进度" type="range" min={0} max={result.events.length} value={cursor} onChange={e => { setPlaying(false); setCursor(Number(e.target.value)); }} />
        <p>已显示 {cursor} / {result.events.length} 个事件。{!result.events.length && '本次仿真没有事件。'}</p>
        <div className="table-wrap"><table><thead><tr><th>时间（秒）</th><th>事件</th><th>车辆</th><th>订单</th></tr></thead><tbody>{result.events.slice(0, cursor).map(event => <tr key={event.event_id}><td>{event.time_s}</td><td>{eventLabels[event.kind] ?? event.kind}</td><td>{event.vehicle_id ?? '—'}</td><td>{event.order_id ?? '—'}</td></tr>)}</tbody></table></div>
      </>}
    </section></div>;
}
