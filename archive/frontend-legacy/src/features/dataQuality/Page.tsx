import { useRef, useState } from 'react';
import bundledText from '../../../../data/scenarios/prep_import_report.json?raw';
import { parseReport } from './report';
import './quality.css';

export default function DataQualityPage() {
  const [text, setText] = useState(bundledText);
  const [source, setSource] = useState('随构建附带的 prep_import_report.json');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState('');
  const [scenario, setScenario] = useState('全部');
  const generation = useRef(0);
  const rows = parseReport(JSON.parse(text));
  const visible = rows.filter(r => scenario === '全部' || scenario === r.scenario);
  async function load(file?: File) {
    if (!file) return;
    const id = ++generation.current;
    setBusy(true); setError('');
    try {
      if (file.size > 2 * 1024 * 1024) throw new Error('报告不能超过 2 MB');
      const next = await file.text();
      parseReport(JSON.parse(next));
      if (id !== generation.current) return;
      setText(next); setSource(file.name); setScenario('全部'); setQuery('');
    } catch (e) {
      if (id === generation.current) setError(`未载入新报告，仍显示上一份：${e instanceof Error ? e.message : String(e)}`);
    } finally { if (id === generation.current) setBusy(false); }
  }
  return <section className="quality-page" aria-label="数据导入质量报告">
    <p>检查转换后的数据数量与语义损失。此页不导入数据库，也不执行求解。</p>
    <div className="quality-toolbar">
      <label>读取本地报告 <input type="file" accept=".json,application/json" disabled={busy} onChange={e => { void load(e.target.files?.[0]); e.target.value = ''; }} /></label>
      <button onClick={() => { generation.current++; setBusy(false); setText(bundledText); setSource('随构建附带的 prep_import_report.json'); setScenario('全部'); setQuery(''); setError(''); }}>恢复随附报告</button>
    </div>
    <p className="quality-source">来源：{source}。本地文件仅在浏览器读取；随附报告不是运行中数据库的实时状态。</p>
    {busy && <p role="status">正在读取报告…</p>}
    {error && <p role="alert">{error}</p>}
    <div className="quality-note"><strong>校验边界</strong><p>报告格式已检查。源报告不包含求解、完整冷链约束或数据库验收结果，这些状态均为未验证；损失条目为零也不代表业务验收通过。</p></div>
    <details><summary>随附转换器的单位规则</summary><p>重量：克转千克；体积：立方厘米转升。需求向上取整且最小为 1，车辆容量向下取整，取整为零则拒绝。规则来自 scripts/import_preparation_bundle.py（prep-v1）；自选报告的生成规则需另行核实。</p></details>
    <div className="quality-toolbar">
      <label>场景 <select aria-label="场景" value={scenario} onChange={e => setScenario(e.target.value)}><option>全部</option>{rows.map(r => <option key={r.scenario}>{r.scenario}</option>)}</select></label>
      <label>搜索损失 <input value={query} onChange={e => setQuery(e.target.value)} placeholder="字段或实体 ID" /></label>
    </div>
    {rows.length === 0 && <p>报告没有场景记录。</p>}
    {visible.map(r => {
      const losses = r.losses.filter(x => x.toLowerCase().includes(query.toLowerCase()));
      return <article key={r.scenario} className="quality-scene"><h2>{r.scenario}</h2>
        <p>订单 {r.orders} · 车辆 {r.vehicles} · 工序 {r.operations} · 资源 {r.resources} · 损失记录 {r.losses.length}</p>
        <p>显示 {losses.length} / {r.losses.length} 条原始记录，保留转换器原文。</p>
        {losses.length ? <ol>{losses.map((loss, i) => <li key={i}>{loss}</li>)}</ol> : <p>{r.losses.length ? '没有匹配的损失记录。' : '该场景未记录字段损失；业务约束仍需独立校验。'}</p>}
      </article>;
    })}
  </section>;
}

