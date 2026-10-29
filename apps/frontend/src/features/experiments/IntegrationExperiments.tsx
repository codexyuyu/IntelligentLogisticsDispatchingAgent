import { useEffect, useRef, useState } from 'react';
import { request, idempotencyKey } from '../../api';
import SectionHeader from '../../components/SectionHeader';
import { sourceKindLabel, statusLabel } from '../../lib/labels';

type Scenario = { id: string; name: string; source_kind: string };
type Metric = { code: string; value: number | null; unit: string; reason: string | null };
type Run = { run_id: string; status: string; reason?: string; observations?: { metrics: { values: Metric[] } } };
type Row = { scenario: string; seed: number; budget_ms: number; elapsed_ms: number; result?: Run; error?: string };
const historyKey = 'integration-experiments-v2';
function saved(): Row[] {
  try { const value = JSON.parse(localStorage.getItem(historyKey) ?? '[]'); return Array.isArray(value) ? value : []; }
  catch { return []; }
}

export default function IntegrationExperiments() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenario, setScenario] = useState('');
  const [count, setCount] = useState(10);
  const [budget, setBudget] = useState(4000);
  const [rows, setRows] = useState<Row[]>(saved);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const stop = useRef(false);
  useEffect(() => { void request<{ items: Scenario[] }>('/integration/scenarios').then(data => {
    setScenarios(data.items); setScenario(data.items[0]?.id ?? '');
  }).catch(e => setError(String(e))); return () => { stop.current = true; }; }, []);
  function store(next: Row[]) {
    setRows(next);
    try { localStorage.setItem(historyKey, JSON.stringify(next)); }
    catch { setError('浏览器存储已满，请导出本轮结果。'); }
  }
  async function runBatch() {
    if (busy || !scenario || !Number.isInteger(count) || count < 1 || count > 30 || budget < 100 || budget > 12000) return;
    stop.current = false; setBusy(true); setError('');
    const collected: Row[] = []; store(collected);
    try {
      for (let seed = 0; seed < count && !stop.current; seed++) {
        const started = performance.now();
        const row: Row = { scenario, seed, budget_ms: budget, elapsed_ms: 0 };
        try {
          let result = await request<Run>('/integration/runs?wait=false', { method: 'POST',
            headers: { 'Idempotency-Key': idempotencyKey() },
            body: JSON.stringify({ schema_version: '2.0.0', scenario_id: scenario, seed, budget_ms: budget, recoveries: [] }) });
          row.result = result;
          while (['queued', 'running', 'pending'].includes(result.status)) {
            if (performance.now() - started > 120000) throw new Error('等待结果超过 120 秒；任务可能仍在执行，可按运行 ID 回查。');
            await new Promise(resolve => setTimeout(resolve, 1000));
            result = await request<Run>(`/integration/runs/${encodeURIComponent(result.run_id)}`);
            row.result = result;
          }
        } catch (e) { row.error = e instanceof Error ? e.message : String(e); }
        row.elapsed_ms = Math.round(performance.now() - started);
        collected.push(row); store([...collected]);
      }
    } finally { setBusy(false); }
  }
  function download() {
    const blob = new Blob([JSON.stringify({ schema_version: '2.0.0', exported_at: new Date().toISOString(), runs: rows }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob); const link = document.createElement('a');
    link.href = url; link.download = 'competition-experiments.json'; link.click(); URL.revokeObjectURL(url);
  }
  const checked = rows.filter(row => !row.error && row.result?.status === 'checked');
  return <div><SectionHeader title="批量实验" desc="同一场景、相同预算、连续种子重复求解；保存真实指标和失败记录。本页用于重复性评测，不将不同种子称为算法对照。" />
    <section className="panel">
      <label>场景 <select value={scenario} disabled={busy} onChange={e => setScenario(e.target.value)}>
        <option value="">请先在协商记录导入场景</option>{scenarios.map(s => <option key={s.id} value={s.id}>{s.name} · {sourceKindLabel(s.source_kind)}</option>)}
      </select></label>
      <label>运行次数 <input type="number" min={1} max={30} value={count} disabled={busy} onChange={e => setCount(Number(e.target.value))} /></label>
      <label>每次预算（毫秒）<input type="number" min={100} max={12000} value={budget} disabled={busy} onChange={e => setBudget(Number(e.target.value))} /></label>
      <button className="btn btn-primary" disabled={busy || !scenario} onClick={() => void runBatch()}>{busy ? '实验执行中…' : '开始新一轮'}</button>
      <button className="btn btn-ghost" disabled={!busy} onClick={() => { stop.current = true; }}>本次结束后停止</button>
      <button className="btn btn-ghost" disabled={!rows.length} onClick={download}>导出完整结果</button>
      {error && <p role="alert">{error}</p>}
      <p>已完成 {rows.length} 次；校验通过 {checked.length} 次；失败或未通过 {rows.length - checked.length} 次。</p>
      <table><thead><tr><th>种子</th><th>预算</th><th>端到端耗时</th><th>状态</th><th>运行 ID / 原因</th></tr></thead>
        <tbody>{rows.map((row, index) => <tr key={index}><td>{row.seed}</td><td>{row.budget_ms} 毫秒</td><td>{row.elapsed_ms} 毫秒</td><td>{row.error ? '失败' : statusLabel(row.result?.status)}</td><td>{row.result?.run_id}<br />{row.error ?? row.result?.reason}</td></tr>)}</tbody></table>
      {rows.map((row, index) => row.result?.observations && <details key={index}><summary>种子 {row.seed} 的业务指标</summary>
        <table><tbody>{row.result.observations.metrics.values.map(m => <tr key={m.code}><td>{m.code}</td><td>{m.value ?? '无数据'} {m.unit}</td><td>{m.reason}</td></tr>)}</tbody></table>
      </details>)}
    </section></div>;
}
