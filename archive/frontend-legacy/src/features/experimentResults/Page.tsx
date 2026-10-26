import { useMemo, useRef, useState } from 'react';
import { readBundle, performance, pairDifference, type Bundle } from './model';
import './results.css';

const labels: Record<string, string> = { demand_satisfaction: '需求满足率', on_time_rate: '准时率', mean_delay: '平均延误', transport_distance: '运输距离', transport_cost: '运输成本', vehicle_utilization: '车辆利用率', warehouse_utilization: '仓库利用率', dock_utilization: '月台利用率', equipment_utilization: '设备利用率', solve_time: '求解耗时', exception_detection_time: '异常检测耗时', reschedule_time: '重排耗时', changed_tasks: '变更任务数', disturbance: '扰动比例' };
const statusLabel: Record<string, string> = { succeeded: '成功', failed: '失败', invalid: '无效' };
const fmt = (n: number | null) => n === null ? '—' : n.toLocaleString('zh-CN', { maximumFractionDigits: 3 });
function download(name: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: 'application/json;charset=utf-8' }));
  const link = document.createElement('a'); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export default function ExperimentResultsPage() {
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [strategy, setStrategy] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(0);
  const [detail, setDetail] = useState<string | null>(null);
  const [left, setLeft] = useState('');
  const [right, setRight] = useState('');
  const [metric, setMetric] = useState('transport_distance');
  const token = useRef(0);
  const filtered = useMemo(() => bundle?.runs.filter(r => (!strategy || r.strategy === strategy) && (!status || (status === 'over' ? r.budget_exceeded : r.status === status))) ?? [], [bundle, strategy, status]);
  const metricNames = useMemo(() => [...new Set([...Object.keys(labels), ...(bundle?.runs.flatMap(r => Object.keys(r.metrics)) ?? [])])], [bundle]);
  const selected = bundle?.runs.find(r => JSON.stringify([r.strategy, r.seed]) === detail);
  async function load(files: FileList | null) {
    if (!files?.length) return;
    const id = ++token.current; setBusy(true); setError('');
    try {
      const list = Array.from(files);
      if (list.length !== 2 || !list.some(f => f.name === 'manifest.json') || !list.some(f => f.name === 'runs.jsonl')) throw new Error('请同时选择同一实验目录的 manifest.json 与 runs.jsonl');
      if (list.reduce((n, f) => n + f.size, 0) > 30 * 1024 * 1024) throw new Error('两个文件总大小不能超过 30 MB');
      const manifest = await list.find(f => f.name === 'manifest.json')!.text();
      const runs = await list.find(f => f.name === 'runs.jsonl')!.text();
      const next = readBundle(manifest, runs);
      if (id !== token.current) return;
      setBundle(next); setLeft(next.strategies[0]); setRight(next.strategies[1]);
      setStrategy(''); setStatus(''); setPage(0); setDetail(null); setMetric('transport_distance');
    } catch (e) { if (id === token.current) setError(`${e instanceof Error ? e.message : String(e)}。未替换当前实验。`); }
    finally { if (id === token.current) setBusy(false); }
  }
  return <section className="experiment-results" aria-label="实验结果工作台">
    <p>读取现有实验产物，查看全部尝试、失败原因及同口径差值。文件只在浏览器内处理，不执行新实验。</p>
    <div className="results-controls"><label>选择两个实验文件 <input type="file" multiple accept=".json,.jsonl" disabled={busy} onChange={e => { void load(e.target.files); e.target.value = ''; }} /></label>
      <button onClick={() => { token.current++; setBusy(false); setBundle(null); setError(''); setDetail(null); }}>清空</button></div>
    {busy && <p role="status">正在读取实验记录…</p>}{error && <p role="alert">{error}</p>}
    {!bundle ? <div className="results-panel"><h2>尚未载入实验</h2><p>同时选择同一输出目录中的 manifest.json 和 runs.jsonl。没有结果时不显示示例数值。</p></div> : <>
      <div className="results-panel"><h2>实验来源</h2><p>单次预算 {bundle.budget} ms · 计划尝试 {bundle.seeds.length * bundle.strategies.length} · 已记录 {bundle.runs.length} · 缺失 {bundle.seeds.length * bundle.strategies.length - bundle.runs.length}</p>
        <p className="results-hash">声明的快照 SHA256：{bundle.snapshotHash}</p>
        <p>未复算源代码或快照哈希。当前 sequential/deep 执行器的 seed 是配对重复编号，不是已传入求解器的随机种子；本页不代表完整 B0–B3 或大模型效果验收。</p>
        <div className="results-controls"><button onClick={() => download('manifest.json', bundle.rawManifest)}>导出原始清单</button><button onClick={() => download('runs.jsonl', bundle.rawRuns)}>导出全部原始运行</button></div>
        <details><summary>环境、依赖与源码清单原文</summary><pre>{bundle.rawManifest}</pre></details>
      </div>
      <div className="results-panel"><h2>策略汇总</h2><p>耗时包含成功、失败和无效尝试；P95 使用 nearest-rank。失败与超预算计数可重叠。缺失运行不按零计入。</p>
        <div className="results-table"><table><thead><tr><th>策略</th><th>记录/计划</th><th>失败或无效</th><th>超预算</th><th>中位耗时 ms</th><th>P95 ms</th></tr></thead><tbody>{bundle.strategies.map(name => { const p = performance(bundle.runs.filter(r => r.strategy === name)); return <tr key={name}><th>{name}</th><td>{p.count}/{bundle.seeds.length}</td><td>{p.failed}</td><td>{p.over}</td><td>{fmt(p.median)}</td><td>{fmt(p.p95)}</td></tr>; })}</tbody></table></div>
      </div>
      <div className="results-panel"><h2>逐次运行</h2><div className="results-controls">
        <label>策略 <select value={strategy} onChange={e => { setStrategy(e.target.value); setPage(0); }}><option value="">全部</option>{bundle.strategies.map(s => <option key={s}>{s}</option>)}</select></label>
        <label>状态 <select value={status} onChange={e => { setStatus(e.target.value); setPage(0); }}><option value="">全部</option><option value="succeeded">成功</option><option value="failed">失败</option><option value="invalid">无效</option><option value="over">超预算</option></select></label></div>
        <div className="results-table"><table><thead><tr><th>策略</th><th>编号</th><th>状态</th><th>耗时 ms</th><th>超预算</th><th>详情</th></tr></thead><tbody>{filtered.slice(page * 25, (page + 1) * 25).map(r => <tr key={JSON.stringify([r.strategy, r.seed])}><td>{r.strategy}</td><td>{r.seed}</td><td>{statusLabel[r.status]}</td><td>{fmt(r.end_to_end_ms)}</td><td>{r.budget_exceeded ? '是' : '否'}</td><td><button aria-label={`查看 ${r.strategy} 编号 ${r.seed}`} onClick={() => setDetail(JSON.stringify([r.strategy, r.seed]))}>指标与原因</button></td></tr>)}</tbody></table></div>
        {!filtered.length && <p>没有符合条件的运行。</p>}<div className="results-controls"><button disabled={!page} onClick={() => setPage(p => p - 1)}>上一页</button><span>{page + 1}/{Math.max(1, Math.ceil(filtered.length / 25))} 页 · {filtered.length} 条</span><button disabled={(page + 1) * 25 >= filtered.length} onClick={() => setPage(p => p + 1)}>下一页</button></div>
      </div>
      {selected && <div className="results-panel"><h2>{selected.strategy} · 编号 {selected.seed}</h2>{selected.error && <p>失败原因：{selected.error}</p>}<p>空值保留为“—”，不折算为零。</p>
        <div className="results-table"><table><thead><tr><th>指标</th><th>值</th><th>单位</th><th>缺失原因</th><th>口径</th></tr></thead><tbody>{metricNames.map(name => { const m = selected.metrics[name]; return <tr key={name}><th>{labels[name] ?? name}</th><td>{fmt(m?.value ?? null)}</td><td>{m?.unit ?? '—'}</td><td>{m ? m.missing_reason ?? '—' : '本次运行未输出该指标'}</td><td>{m ? `${m.source} / ${m.scope_id} / [${m.window_start}, ${m.window_end}) / ${m.definition_version}` : '—'}</td></tr>; })}</tbody></table></div>
      </div>}
      <div className="results-panel"><h2>配对差值</h2><p>差值 = 右侧 − 左侧。失败、超预算、指标缺失或口径不同均不参与计算；不将差值自动解释为收益。</p><div className="results-controls">
        <label>左侧 <select value={left} onChange={e => setLeft(e.target.value)}>{bundle.strategies.map(s => <option key={s}>{s}</option>)}</select></label>
        <label>右侧 <select value={right} onChange={e => setRight(e.target.value)}>{bundle.strategies.map(s => <option key={s}>{s}</option>)}</select></label>
        <label>指标 <select value={metric} onChange={e => setMetric(e.target.value)}>{metricNames.map(m => <option key={m} value={m}>{labels[m] ?? m}</option>)}</select></label></div>
        {left === right ? <p>请选择两个不同策略。</p> : <div className="results-table results-pairs"><table><thead><tr><th>重复编号</th><th>右减左</th><th>单位或排除原因</th></tr></thead><tbody>{bundle.seeds.map(seed => { const d = pairDifference(bundle.runs.find(r => r.seed === seed && r.strategy === left), bundle.runs.find(r => r.seed === seed && r.strategy === right), metric); return <tr key={seed}><td>{seed}</td><td>{fmt(d.value)}</td><td>{d.reason}</td></tr>; })}</tbody></table></div>}
      </div>
    </>}
  </section>;
}
