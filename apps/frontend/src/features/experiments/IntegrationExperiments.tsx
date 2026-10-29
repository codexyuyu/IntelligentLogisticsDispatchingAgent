import { useEffect, useRef, useState } from 'react';
import { request, idempotencyKey } from '../../api';
import SectionHeader from '../../components/SectionHeader';
import { sourceKindLabel, statusLabel } from '../../lib/labels';
import { isPending, pollStatus, readStored, saveStored, useTaskRunner, validInteger } from '../../lib/asyncJobs';

type Scenario = { id: string; name: string; source_kind: string };
type Metric = { code: string; value: number | null; unit: string; reason: string | null };
type Run = { run_id: string; status: string; reason?: string; observations?: { metrics: { values: Metric[] } } };
type Row = { batch_id?: string; started_at?: string; scenario: string; seed: number; budget_ms: number; elapsed_ms: number; result?: Run; error?: string };
const historyKey = 'integration-experiments-v2';
function saved(): Row[] {
  try { const value = JSON.parse(readStored(historyKey) ?? '[]'); return Array.isArray(value) ? value.filter(row => row && typeof row.scenario === 'string' && Number.isInteger(row.seed) && Number.isFinite(row.budget_ms) && Number.isFinite(row.elapsed_ms)) : []; }
  catch { return []; }
}

export default function IntegrationExperiments() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenario, setScenario] = useState('');
  const [count, setCount] = useState(10);
  const [budget, setBudget] = useState(4000);
  const [rows, setRows] = useState<Row[]>(saved);
  const { busy, error, run } = useTaskRunner();
  const [notice, setNotice] = useState('');
  const [stopping, setStopping] = useState(false);
  const rowsRef = useRef(rows);
  const validInput = validInteger(count, 1, 30) && validInteger(budget, 100, 12000);
  const stop = useRef(false);
  async function loadScenarios(signal: AbortSignal) {
    const data = await request<{ items: Scenario[] }>('/integration/scenarios', { signal });
    signal.throwIfAborted(); setScenarios(data.items);
    setScenario(previous => data.items.some(item => item.id === previous) ? previous : data.items[0]?.id ?? '');
  }
  useEffect(() => {
    void run(loadScenarios);
    return () => { stop.current = true; };
  }, []);
  function store(next: Row[], signal?: AbortSignal) {
    // Persist accepted IDs even when the page was closed during submission.
    rowsRef.current = next;
    const saved = saveStored(historyKey, JSON.stringify(next));
    if (!signal?.aborted) {
      setRows(next);
      if (!saved) setNotice('浏览器存储已满，请立即导出结果；刷新后本轮新增记录可能丢失。');
    }
  }
  async function refreshRow(index: number, signal: AbortSignal) {
    const original = rowsRef.current[index];
    if (!original?.result?.run_id) return;
    const id = original.result.run_id;
    await pollStatus(() => request<Run>(`/integration/runs/${encodeURIComponent(id)}`, { signal }), signal, result => {
      const next = [...rowsRef.current];
      next[index] = { ...next[index], result, error: undefined };
      store(next, signal);
    });
  }
  async function runBatch(signal: AbortSignal) {
    if (!scenario || !validInput) throw new Error('运行次数须为 1–30 的整数，预算须为 100–12000 的整数。');
    stop.current = false; setStopping(false); setNotice('');
    const batchId = new Date().toISOString();
    for (let seed = 0; seed < count && !stop.current; seed++) {
      signal.throwIfAborted();
      const started = performance.now();
      const row: Row = { batch_id: batchId, started_at: new Date().toISOString(), scenario, seed, budget_ms: budget, elapsed_ms: 0 };
      const index = rowsRef.current.length;
      store([...rowsRef.current, row], signal);
      try {
        const result = await request<Run>('/integration/runs?wait=false', { method: 'POST',
          headers: { 'Idempotency-Key': idempotencyKey() },
          body: JSON.stringify({ schema_version: '2.0.0', scenario_id: scenario, seed, budget_ms: budget, recoveries: [] }) });
        row.result = result;
        const next = [...rowsRef.current]; next[index] = { ...row }; store(next, signal);
        signal.throwIfAborted();
        if (isPending(result.status)) await refreshRow(index, signal);
      } catch (cause) {
        if (signal.aborted) throw cause;
        const next = [...rowsRef.current];
        next[index] = { ...next[index], error: cause instanceof Error ? cause.message : String(cause) }; store(next, signal);
      } finally {
        const next = [...rowsRef.current];
        next[index] = { ...next[index], elapsed_ms: Math.round(performance.now() - started) }; store(next, signal);
      }
    }
    setNotice(stop.current ? '已停止后续任务，保留已提交任务和全部历史记录。' : '本轮完成；全部历史记录已保留。');
  }
  function download() {
    const blob = new Blob([JSON.stringify({ schema_version: '2.0.0', exported_at: new Date().toISOString(), runs: rows }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob); const link = document.createElement('a');
    link.href = url; link.download = 'competition-experiments.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const pending = rows.filter(row => !row.result || isPending(row.result.status));
  const checked = rows.filter(row => !row.error && row.result?.status === 'checked');
  return <div><SectionHeader title="批量实验" desc="同一场景、相同预算、连续种子重复求解；保存真实指标和失败记录。本页用于重复性评测，不将不同种子称为算法对照。" />
    <section className="panel">
      <label>场景 <select value={scenario} disabled={busy} onChange={e => setScenario(e.target.value)}>
        <option value="">请先在协商记录导入场景</option>{scenarios.map(s => <option key={s.id} value={s.id}>{s.name} · {sourceKindLabel(s.source_kind)}</option>)}
      </select></label>
      <label>运行次数 <input type="number" min={1} max={30} value={count} disabled={busy} onChange={e => setCount(Number(e.target.value))} /></label>
      <label>每次预算（毫秒）<input type="number" min={100} max={12000} value={budget} disabled={busy} onChange={e => setBudget(Number(e.target.value))} /></label>
      <button className="btn btn-primary" disabled={busy || !scenario || !validInput} onClick={() => void run(runBatch)}>{busy ? '实验执行中…' : '开始新一轮'}</button>
      <button className="btn btn-ghost" disabled={!busy || stopping} onClick={() => { stop.current = true; setStopping(true); }}>{stopping ? '将在本次结束后停止' : '本次结束后停止'}</button>
      <button className="btn btn-ghost" disabled={!rows.length} onClick={download}>导出完整结果</button>
      <button className="btn btn-ghost" disabled={busy} onClick={() => void run(loadScenarios)}>刷新场景列表</button>
      {!validInput && <p role="alert">运行次数须为 1–30 的整数，预算须为 100–12000 的整数。</p>}
      {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
      <p>共记录 {rows.length} 次；校验通过 {checked.length} 次；待回查 {pending.length} 次；其余失败或未通过 {rows.length - checked.length - pending.length} 次。新一轮追加记录，刷新页面不会自动派发剩余任务。</p>
      <div className="table-wrap"><table><thead><tr><th>批次 / 场景</th><th>种子</th><th>预算</th><th>端到端耗时</th><th>状态</th><th>运行 ID / 原因</th></tr></thead>
        <tbody>{rows.map((row, index) => <tr key={index}><td>{row.batch_id ?? '历史记录'}<br />{row.scenario}</td><td>{row.seed}</td><td>{row.budget_ms} 毫秒</td><td>{row.elapsed_ms} 毫秒</td><td>{row.error ? '等待失败，可回查' : row.result ? statusLabel(row.result.status) : '提交结果待确认'}</td><td>{row.result?.run_id}<br />{row.error ?? row.result?.reason}{row.result?.run_id && <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => void run(signal => refreshRow(index, signal))}>回查结果</button>}</td></tr>)}</tbody></table></div>
      {rows.map((row, index) => row.result?.observations && <details key={index}><summary>种子 {row.seed} 的业务指标</summary>
        <table><tbody>{row.result.observations.metrics.values.map(m => <tr key={m.code}><td>{m.code}</td><td>{m.value ?? '无数据'} {m.unit}</td><td>{m.reason}</td></tr>)}</tbody></table>
      </details>)}
    </section></div>;
}
