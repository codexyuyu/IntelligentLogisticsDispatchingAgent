import { useEffect, useState } from 'react';
import { request, idempotencyKey } from '../../api';
import SectionHeader from '../../components/SectionHeader';

type Event = { event_id: string; time_s: number; kind: string; vehicle_id: string | null; order_id: string | null };
type Result = { status: string; final_time_s: number; events: Event[]; delivered_order_ids: string[]; seed: number };
export default function LiveSimulation() {
  const [job, setJob] = useState('');
  const [seed, setSeed] = useState(0);
  const [until, setUntil] = useState(86400);
  const [result, setResult] = useState<Result | null>(null);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!playing || !result) return;
    const timer = setInterval(() => setCursor(value => {
      if (value >= result.events.length) { setPlaying(false); return value; }
      return value + 1;
    }), 500);
    return () => clearInterval(timer);
  }, [playing, result]);
  async function simulate() {
    setBusy(true); setError(''); setPlaying(false); setResult(null);
    try {
      const source = await request<{ kind: string; value: { candidate: unknown; stops: unknown[]; validation?: { valid: boolean } } }>(`/jobs/${encodeURIComponent(job.trim())}/result`);
      if (source.kind !== 'transport' || !source.value.candidate || !source.value.validation?.valid) throw new Error('请选择已完成且独立校验通过的运输任务。');
      const accepted = await request<{ job_id: string }>('/simulations', { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey() },
        body: JSON.stringify({ schema_version: '2.0.0', plan: source.value.candidate, stops: source.value.stops, seed, until_s: until }) });
      const started = Date.now();
      while (true) {
        const state = await request<{ status: string; error_message?: string }>(`/jobs/${accepted.job_id}`);
        if (state.status === 'completed') break;
        if (['failed', 'cancelled'].includes(state.status)) throw new Error(state.error_message ?? state.status);
        if (Date.now() - started > 120000) throw new Error(`等待超时，仿真任务 ID：${accepted.job_id}`);
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
      const response = await request<{ kind: string; value: Result }>(`/jobs/${accepted.job_id}/result`);
      setResult(response.value); setCursor(0);
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  return <div><SectionHeader title="真实运输仿真与回放" desc="读取已求解的运输任务，由后台 SimPy 工作进程执行，按实际事件记录回放。" />
    <section className="panel">
      <label>运输任务 ID <input value={job} onChange={e => setJob(e.target.value)} placeholder="从运输计划复制已完成的任务 ID" /></label>
      <label>种子 <input type="number" min={0} value={seed} onChange={e => setSeed(Number(e.target.value))} /></label>
      <label>结束时间（秒）<input type="number" min={1} value={until} onChange={e => setUntil(Number(e.target.value))} /></label>
      <button className="btn btn-primary" disabled={busy || !job.trim()} onClick={() => void simulate()}>{busy ? '正在仿真…' : '运行仿真'}</button>
      {error && <p role="alert">{error}</p>}
      {result && <><p>状态：{result.status}；最终时间：{result.final_time_s} 秒；送达订单：{result.delivered_order_ids.length}；事件：{result.events.length}</p>
        <button className="btn btn-ghost" onClick={() => setPlaying(!playing)}>{playing ? '暂停' : '播放'}</button>
        <button className="btn btn-ghost" onClick={() => { setPlaying(false); setCursor(0); }}>回到起点</button>
        <input aria-label="事件回放进度" type="range" min={0} max={result.events.length} value={cursor} onChange={e => { setPlaying(false); setCursor(Number(e.target.value)); }} />
        <table><thead><tr><th>时间（秒）</th><th>事件</th><th>车辆</th><th>订单</th></tr></thead><tbody>{result.events.slice(0, cursor).map(event => <tr key={event.event_id}><td>{event.time_s}</td><td>{event.kind}</td><td>{event.vehicle_id}</td><td>{event.order_id}</td></tr>)}</tbody></table>
      </>}
    </section></div>;
}
