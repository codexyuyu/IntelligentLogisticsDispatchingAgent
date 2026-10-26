import { useEffect, useMemo, useState } from 'react';
import SectionHeader from '../../components/SectionHeader';
import { KpiCard } from '../../components/KpiCard';
import { StatusPill } from '../../components/StatusPill';
import { useApp } from '../../appContext';
import { fmtDur, fmtKM } from '../../lib/format';
import { runBenchmark, fairDistanceReduction, type BenchmarkMetrics, type BenchmarkResult } from '../../lib/benchmark';
import { runBatchBenchmark, summarizeBatch, budgetForScale, type BenchmarkProfile, type BatchBenchmarkSummary, type BatchSeedRun } from '../../lib/batchBenchmark';

type MetricRow = { name: string; baseline: string; optimized: string; note: string };

type PersistedBatch = { savedAt: string; summaries: BatchBenchmarkSummary[] };

const STORAGE_KEY = 'b06-benchmark-history-r16-speed-v1';
const PREVIOUS_STORAGE_KEY = 'b06-benchmark-history-r15-v2';
const MAX_SAVED_RUNS = 40;

const STAGE_LABELS: Record<string, string> = {
  scenario_import: '场景导入',
  planning_submit: 'Planning Job 提交',
  planning_solve: 'CP-SAT + Routing 求解',
  plan_fetch: '方案读取',
  metric_calculation: '指标计算',
  unknown: '未知阶段',
};

function delta(a: number, b: number, unit = '') {
  const d = b - a;
  const prefix = d > 0 ? '+' : '';
  return `${prefix}${d.toFixed(unit === 'km' ? 1 : 0)}${unit ? ` ${unit}` : ''}`;
}

function renderMetric(metric: BenchmarkMetrics) {
  return {
    satisfaction: `${Math.round(metric.satisfactionRate * 100)}%`,
    onTime: metric.onTimeRate == null ? '—' : `${Math.round(metric.onTimeRate * 100)}%`,
    distance: fmtKM(metric.distanceM),
    duration: fmtDur(metric.routeDurationS),
    vehicles: Number.isInteger(metric.vehiclesUsed) ? `${metric.vehiclesUsed}` : metric.vehiclesUsed.toFixed(1),
    utilization: metric.vehicleUtilization == null ? '—' : `${Math.round(metric.vehicleUtilization * 100)}%`,
    makespan: metric.makespanS == null ? '—' : fmtDur(metric.makespanS),
  };
}

function mean(values: number[]) {
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
}

function stdev(values: number[]) {
  if (values.length < 2) return 0;
  const m = mean(values);
  return Math.sqrt(values.reduce((s, v) => s + (v - m) ** 2, 0) / (values.length - 1));
}

function csvCell(value: unknown) {
  const text = String(value ?? '');
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function exportBatchCsv(batch: BatchBenchmarkSummary[]) {
  const rows: unknown[][] = [[
    '规模', 'Seed', '模式', '状态', '失败阶段', '错误码', '失败原因', '方案ID',
    'Baseline距离(km)', '优化距离(km)', '距离下降(%)', 'Baseline准时率(%)', '优化准时率(%)',
    'Baseline完工(h)', '优化完工(h)', '阶段报告耗时(ms)', '实际端到端耗时(ms)', 'CP-SAT(ms)', 'Routing(ms)', '预算(ms)', '方案校验', '基线满足率(%)', '优化满足率(%)', '基线未服务数', '优化未服务数', '场景指纹', '场景版本', '任务ID', '运行时间',
  ]];
  for (const group of batch) {
    for (const run of group.runs) {
      rows.push([
        `S${run.size}`,
        run.seed,
        run.profile === 'quick' ? '快速排错' : '标准评测',
        run.status === 'succeeded' ? '成功' : '失败',
        run.failureStage ? STAGE_LABELS[run.failureStage] ?? run.failureStage : '',
        run.errorCode ?? '',
        run.errorReason ?? run.error ?? '',
        run.planId ?? '',
        run.baseline ? (run.baseline.distanceM / 1000).toFixed(2) : '',
        run.optimized ? (run.optimized.distanceM / 1000).toFixed(2) : '',
        run.comparisonPct == null ? '' : run.comparisonPct.toFixed(2),
        run.baseline?.onTimeRate == null ? '' : (run.baseline.onTimeRate * 100).toFixed(2),
        run.optimized?.onTimeRate == null ? '' : (run.optimized.onTimeRate * 100).toFixed(2),
        run.baseline?.makespanS == null ? '' : (run.baseline.makespanS / 3600).toFixed(2),
        run.optimized?.makespanS == null ? '' : (run.optimized.makespanS / 3600).toFixed(2),
        run.solveMs ?? '', run.wallMs ?? '', run.warehouseMs ?? '', run.routingMs ?? '', run.budgetMs ?? '', run.validationStatus ?? '',
        run.baseline ? (run.baseline.satisfactionRate * 100).toFixed(2) : '',
        run.optimized ? (run.optimized.satisfactionRate * 100).toFixed(2) : '',
        run.baseline?.unservedOrders ?? '', run.optimized?.unservedOrders ?? '',
        run.scenarioFingerprint ?? '', run.scenarioVersion ?? 'R14 legacy', run.planningJobId, run.runAt ?? '',
      ]);
    }
  }
  const csv = '\ufeff' + rows.map((r) => r.map(csvCell).join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `benchmark_batch_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function downloadBlob(text: string, mime: string, filename: string) {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function exportEvidenceJson(summaries: BatchBenchmarkSummary[]) {
  downloadBlob(JSON.stringify({ evidence_version: 'R16-speed-v1', exported_at: new Date().toISOString(),
    caveats: ['合成场景，非企业生产数据', '快速排错为短预算探索，未找到方案不等于不可行；不可与60秒标准评测混合统计', 'baseline 为使用相同仓储交接安排的贪心路径规则', '端到端墙钟时间包含 HTTP 和轮询'],
    summaries }, null, 2), 'application/json;charset=utf-8', `benchmark_r16_speed_evidence_${new Date().toISOString().slice(0, 10)}.json`);
}

function mergeHistory(oldSummaries: BatchBenchmarkSummary[], incoming: BatchBenchmarkSummary[]) {
  const map = new Map<string, BatchSeedRun>();
  // Keep the most recent result for each size+seed+generator version, do not silently duplicate runs.
  for (const s of [...oldSummaries, ...incoming]) for (const run of s.runs) {
    map.set(`${run.scenarioVersion ?? 'legacy'}:${run.profile ?? 'standard'}:${run.size}:${run.seed}`, run);
  }
  const kept = [...map.values()].slice(-MAX_SAVED_RUNS);
  const byProfileAndSize = new Map<string, BatchSeedRun[]>();
  for (const run of kept) {
    const key = `${run.profile ?? 'standard'}:${run.size}`;
    byProfileAndSize.set(key, [...(byProfileAndSize.get(key) ?? []), run]);
  }
  return [...byProfileAndSize.entries()].sort((a, b) => a[0].localeCompare(b[0]))
    .map(([key, runs]) => summarizeBatch(runs[0].size, runs, key.split(':')[0] as BenchmarkProfile));
}

function loadHistory(): PersistedBatch | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as PersistedBatch;
    // One-time read of R15 records; they used 60s and therefore belong to standard mode.
    const historical = localStorage.getItem(PREVIOUS_STORAGE_KEY);
    return historical ? JSON.parse(historical) as PersistedBatch : null;
  } catch {
    return null;
  }
}

function saveHistory(summaries: BatchBenchmarkSummary[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ savedAt: new Date().toISOString(), summaries } satisfies PersistedBatch));
  } catch {
    // History is useful but must never break the experiment page.
  }
}

function parseSeeds(text: string): number[] {
  // Blank entries must not silently turn into seed 0; preview and execution
  // must apply identical validation and de-duplication rules.
  return Array.from(new Set(text.split(',').map((s) => s.trim()).filter(Boolean)
    .map(Number).filter((n) => Number.isSafeInteger(n) && n >= 0))).slice(0, 8);
}

function failureSummary(runs: BatchSeedRun[]) {
  const failed = runs.filter((r) => r.status === 'failed');
  const byStage = new Map<string, number>();
  for (const run of failed) {
    const stage = run.failureStage ?? 'unknown';
    byStage.set(stage, (byStage.get(stage) ?? 0) + 1);
  }
  return { failed, byStage: [...byStage.entries()].sort((a, b) => b[1] - a[1]) };
}

type AcceptedAudit = {
  source_benchmark_version: string;
  scenario_sha256: string;
  per_arm_budget_ms: number;
  handoff_wait_saved_s: number;
  handoff_wait_reduction_pct: number;
  additional_deep_wall_ms: number;
  modes: { mode: string; order_count: number; distance_m: number; handoff_wait_s: number; wall_ms: number; selected_round: number; validation_record: string }[];
};

export default function Page() {
  const { snapshot, baselinePlan, runBaseline } = useApp();
  const [r17Accepted, setR17Accepted] = useState<AcceptedAudit | null>(null);
  const [r17EvidenceError, setR17EvidenceError] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/evidence/r17_arithmetic_audit.json', { signal: controller.signal })
      .then((res) => { if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.json() as Promise<AcceptedAudit>; })
      .then(setR17Accepted)
      .catch((err: unknown) => { if ((err as { name?: string })?.name !== 'AbortError') setR17EvidenceError(true); });
    return () => controller.abort();
  }, []);
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState('未运行');
  const [benchmark, setBenchmark] = useState<BenchmarkResult | null>(null);
  const [selectedSizes, setSelectedSizes] = useState<number[]>([50]);
  const [seedText, setSeedText] = useState('17');
  const [profile, setProfile] = useState<BenchmarkProfile>('quick');
  const [batchProgress, setBatchProgress] = useState({ completed: 0, total: 0, message: '尚未运行批量实验' });
  const [batch, setBatch] = useState<BatchBenchmarkSummary[]>([]);
  const [historySavedAt, setHistorySavedAt] = useState<string | null>(null);

  useEffect(() => {
    const history = loadHistory();
    if (history?.summaries?.length) {
      setBatch(history.summaries);
      setHistorySavedAt(history.savedAt);
      setBatchProgress({
        completed: history.summaries.reduce((n, s) => n + s.runs.length, 0),
        total: history.summaries.reduce((n, s) => n + s.runs.length, 0),
        message: '已恢复上次批量实验记录',
      });
    }
  }, []);

  async function runExperiment() {
    if (!snapshot || busy) return;
    setBusy(true);
    setBenchmark(null);
    try {
      setPhase('正在准备当前优化方案…');
      let plan = baselinePlan;
      if (!plan) plan = await runBaseline();
      if (!plan) throw new Error('优化方案未生成');
      setPhase('正在计算规则基线与优化方案指标…');
      const result = await runBenchmark(snapshot, plan);
      setBenchmark(result);
      setPhase('实验完成');
    } catch (e) {
      setPhase(`实验失败：${e instanceof Error ? e.message : '实验失败'}`);
    } finally {
      setBusy(false);
    }
  }

  async function runBatch() {
    if (!snapshot || busy) return;
    const seeds = parseSeeds(seedText);
    if (!seeds.length || !selectedSizes.length) {
      setBatchProgress({ completed: 0, total: 0, message: '请至少选择一个订单规模和一个有效 seed' });
      return;
    }
    setBusy(true);
    setBenchmark(null);
    setBatchProgress({ completed: 0, total: selectedSizes.length * seeds.length, message: '准备批量实验…' });
    try {
      const result = await runBatchBenchmark(snapshot, selectedSizes, seeds, (message, completed, total) => {
        setBatchProgress({ completed, total, message });
      }, profile, (run) => {
        // Commit each finished run immediately, not just after the whole batch.
        const current = loadHistory()?.summaries ?? batch;
        const checkpoint = mergeHistory(current, [summarizeBatch(run.size, [run], run.profile ?? profile)]);
        saveHistory(checkpoint);
        setBatch(checkpoint);
        setHistorySavedAt(new Date().toISOString());
      });
      const merged = mergeHistory(batch, result);
      setBatch(merged);
      const savedAt = new Date().toISOString();
      saveHistory(merged);
      setHistorySavedAt(savedAt);
      setBatchProgress((p) => ({ ...p, message: '批量实验完成，结果已合并保存；请及时导出 JSON 证据包' }));
    } catch (e) {
      setBatchProgress((p) => ({ ...p, message: `批量实验失败：${e instanceof Error ? e.message : '实验失败'}` }));
    } finally {
      setBusy(false);
    }
  }

  function clearHistory() {
    try { localStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
    setBatch([]);
    setHistorySavedAt(null);
    setBatchProgress({ completed: 0, total: 0, message: '历史记录已清除' });
  }

  const previewSeeds = parseSeeds(seedText);
  const b = benchmark ? renderMetric(benchmark.baseline) : null;
  const o = benchmark ? renderMetric(benchmark.optimized) : null;
  const rows: MetricRow[] = benchmark ? [
    { name: '需求满足率', baseline: b!.satisfaction, optimized: o!.satisfaction, note: '服务订单数 / 总订单数' },
    { name: '准时率', baseline: b!.onTime, optimized: o!.onTime, note: '配送到达时间 ≤ freshness deadline' },
    { name: '未服务订单', baseline: `${benchmark.baseline.unservedOrders}`, optimized: `${benchmark.optimized.unservedOrders}`, note: '越少越好' },
    { name: '总运输距离', baseline: b!.distance, optimized: o!.distance, note: '所有车辆配送路线距离之和' },
    { name: '路线总时长', baseline: b!.duration, optimized: o!.duration, note: '所有车辆路线行驶时长之和' },
    { name: '车辆使用数', baseline: b!.vehicles, optimized: o!.vehicles, note: '生成配送路线的车辆数量' },
    { name: '平均车辆利用率', baseline: b!.utilization, optimized: o!.utilization, note: '载重利用率与体积利用率平均值' },
    { name: '最大完工时间', baseline: b!.makespan, optimized: o!.makespan, note: '最后一辆车完成配送/返回前的时间' },
  ] : [];

  const allRuns = useMemo(() => batch.flatMap((s) => s.runs), [batch]);
  const failedRuns = useMemo(() => failureSummary(allRuns), [allRuns]);
  const successCount = allRuns.filter((r) => r.status === 'succeeded').length;

  return <div>
    <SectionHeader
     
      title="基准实验"
      desc="固定场景与控制变量，对比确定性规则基线与当前 CP-SAT + Routing 优化方案，并支持 S20 / S50 / S100 多 seed 批量实验。"
      actions={<div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}><button className="btn" disabled={busy || !snapshot} onClick={() => { void runExperiment(); }}>单次 S20 实验</button><button className="btn btn-primary" disabled={busy || !snapshot} onClick={() => { void runBatch(); }}>{busy ? '实验运行中…' : '运行批量实验'}</button></div>}
    />

    <div className="panel" style={{ marginTop: 16, marginBottom: 16 }}>
      <div className="panel-title-row">
        <div><h3>R17 已验收 · 正式同快照同预算 A/B</h3><p>这是从已验收 JSON 独立复算并归档的历史证据，不是本页按钮实时求解，也不是 R18 多场景新成绩。</p></div>
        <StatusPill tone={r17Accepted ? 'success' : 'info'}>{r17Accepted ? '历史证据已核算' : r17EvidenceError ? '证据文件不可用' : '读取归档证据…'}</StatusPill>
      </div>
      {r17Accepted ? <>
        <div className="validation" style={{ marginTop: 14, marginBottom: 14 }}>
          <div><span>场景/每组预算</span><b>{r17Accepted.modes[0]?.order_count} 单 / {r17Accepted.per_arm_budget_ms / 1000}s</b></div>
          <div><span>订单级交接等待</span><b>{(r17Accepted.modes[0]?.handoff_wait_s ?? 0) / 60} → {(r17Accepted.modes[1]?.handoff_wait_s ?? 0) / 60} 分钟</b></div>
          <div><span>累计等待下降</span><b>{r17Accepted.handoff_wait_reduction_pct.toFixed(1)}%</b></div>
          <div><span>额外求解耗时</span><b>+{(r17Accepted.additional_deep_wall_ms / 1000).toFixed(3)} 秒</b></div>
        </div>
        <div className="table-wrap"><table><thead><tr><th>求解模式</th><th>订单覆盖</th><th>运输距离</th><th>累计订单等待</th><th>实际耗时</th><th>校验记录</th><th>入选轮次</th></tr></thead>
          <tbody>{r17Accepted.modes.map((m) => <tr key={m.mode}><td>{m.mode === 'deep' ? '深度双向协同' : '单轮顺序衔接'}</td><td>{m.order_count}/{m.order_count}</td><td>{fmtKM(m.distance_m)}</td><td>{(m.handoff_wait_s / 60).toFixed(0)} 分钟</td><td>{(m.wall_ms / 1000).toFixed(3)} 秒</td><td>{m.validation_record}</td><td>第 {m.selected_round} 轮</td></tr>)}</tbody></table></div>
        <p className="scope-note" style={{ overflowWrap: 'anywhere', marginTop: 12 }}>场景 SHA256：{r17Accepted.scenario_sha256}。交接等待按每订单 ready_at 到车辆仓库出发时刻累计；不是车辆排队、货损率或成本节约。仅单组双仓合成样本，不推断其他业务场景。</p>
      </> : <p className="scope-note" style={{ marginTop: 12 }}>如未显示数字，可在完整工程的 benchmarks/b03/r17_accepted 文件夹查看离线核算及原始资料。</p>}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
        <a className="btn btn-secondary btn-sm" href="/evidence/r17_accepted_original.json" download="r17_accepted_original.json">下载 R17 原始证据</a>
        <a className="btn btn-secondary btn-sm" href="/evidence/r17_arithmetic_audit.json" download="r17_arithmetic_audit.json">下载独立指标复算</a>
      </div>
    </div>

    <div className="kpi-grid">
      <KpiCard label="实验状态" value={busy ? '运行中' : phase} sub={snapshot ? `${snapshot.orders.length} 订单 · ${snapshot.warehouses.length} 仓库` : '场景初始化中'} icon="chart" tone={phase === '实验完成' ? 'green' : 'neutral'} />
      <KpiCard label="优化方案" value={baselinePlan ? '可用' : '待生成'} sub={baselinePlan ? `${baselinePlan.plan_id} · v${baselinePlan.version}` : '单次实验自动生成'} icon="route" tone="green" />
      <KpiCard label="批量进度" value={`${batchProgress.completed}/${batchProgress.total || 0}`} sub={batchProgress.message} icon="play" tone="orange" />
      <KpiCard label="记录留存" value={`${successCount} 成功 / ${allRuns.length} 次`} sub={historySavedAt ? `最近保存 ${new Date(historySavedAt).toLocaleString()}` : '结果保存在当前浏览器'} icon="list" tone="neutral" />
    </div>

    <div className="panel" style={{ marginTop: 16 }}>
      <div className="panel-title-row"><div><h3>批量实验配置</h3><p>逐个生成 S20 / S50 / S100 场景，使用同一套规则基线与现有 Planning Job，不修改后端算法。</p></div><StatusPill tone={batch.length ? 'success' : 'info'}>{batch.length ? '已有结果' : '待运行'}</StatusPill></div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 14 }}>
        <div><div className="scope-note" style={{ marginBottom: 8 }}>订单规模</div><div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>{[20, 50, 100].map((size) => <button key={size} className={`btn ${selectedSizes.includes(size) ? 'btn-primary' : ''}`} type="button" disabled={busy} onClick={() => setSelectedSizes((prev) => prev.includes(size) ? prev.filter((x) => x !== size) : [...prev, size])} aria-pressed={selectedSizes.includes(size)}>S{size} {selectedSizes.includes(size) ? '✓ 已选' : '未选'}</button>)}</div><div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10 }}><button className="btn" type="button" disabled={busy} onClick={() => { setSelectedSizes([50]); setSeedText('17'); setProfile('quick'); }}>定点快检：S50 / 17</button><button className="btn" type="button" disabled={busy} onClick={() => { setSelectedSizes([20]); setSeedText('17,42,66,88,101'); setProfile('quick'); }}>快速检查：S20 × 5</button><button className="btn" type="button" disabled={busy} onClick={() => { setSelectedSizes([20, 50, 100]); setSeedText('17,42,66,88,101'); setProfile('standard'); }}>完整验证：3规模 × 5</button></div></div>
        <div><label className="scope-note" htmlFor="seed-list">Seeds（逗号分隔，最多 8 个）</label><input id="seed-list" value={seedText} disabled={busy} onChange={(e) => setSeedText(e.target.value)} style={{ width: '100%', marginTop: 8 }} /><div className="scope-note" style={{ marginTop: 8 }}>当前将运行 {selectedSizes.length * previewSeeds.length} 组实验。</div></div>
      </div>
      <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <label className="scope-note" htmlFor="benchmark-profile">求解模式</label>
        <select id="benchmark-profile" value={profile} disabled={busy} onChange={(e) => setProfile(e.target.value as BenchmarkProfile)} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--line)', background: 'var(--panel2)', color: 'var(--text)' }}>
          <option value="quick">快速排错（S20=8秒 / S50=12秒 / S100=18秒）</option>
          <option value="standard">标准评测（每组60秒，比赛数据）</option>
        </select>
        <span className="scope-note">{profile === 'quick' ? '当前是短预算验证：失败不代表无解，距离改善只供预览。' : '标准评测：保留既有60秒预算，可用于正式对照。'} {selectedSizes.map(s => `S${s}：${budgetForScale(s, profile) / 1000}s`).join(' · ')}</span>
      </div>
      {busy && <div style={{ marginTop: 14 }}><div style={{ height: 8, background: 'var(--viz-panel)', borderRadius: 999, overflow: 'hidden' }}><div style={{ height: '100%', width: `${batchProgress.total ? Math.round(batchProgress.completed / batchProgress.total * 100) : 0}%`, background: 'var(--viz-accent)', transition: 'width .2s ease' }} /></div><p className="scope-note" style={{ marginTop: 8 }}>{batchProgress.message}</p></div>}
    </div>

    {batch.length > 0 && <div className="panel" style={{ marginTop: 16 }}>
      <div className="panel-title-row"><div><h3>批量实验结果</h3><p>同版本同规模同 Seed 同求解模式保留最近一次；快检与标准结果分开统计。仅双方全部服务时显示距离优化率；CSV/JSON 支持追溯输入、耗时和校验。</p></div><div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}><StatusPill tone="success">共 {allRuns.length} 次</StatusPill><button className="btn" type="button" onClick={() => exportBatchCsv(batch)}>导出 CSV</button><button className="btn" type="button" onClick={() => exportEvidenceJson(batch)}>导出 JSON 证据包</button><button className="btn" type="button" onClick={clearHistory}>清除历史</button></div></div>
      <div className="table-wrap"><table><thead><tr><th>规模</th><th>实验模式</th><th>成功 / 总数</th><th>Baseline 距离</th><th>优化距离</th><th>距离下降</th><th>Baseline 准时率</th><th>优化准时率</th><th>平均端到端耗时</th><th>订单覆盖/校验</th></tr></thead><tbody>{batch.map((s) => { const ok = s.runs.filter((r) => r.status === 'succeeded'); const ab = s.averages.baseline; const ao = s.averages.optimized; const reductions = ok.filter((r) => r.comparisonPct != null).map((r) => r.comparisonPct!); const solve = ok.map((r) => r.wallMs ?? 0).filter((v) => v > 0); return <tr key={`${s.profile ?? 'standard'}-${s.size}`}><td><strong>S{s.size}</strong></td><td>{s.profile === 'quick' ? '快检' : '标准'}</td><td>{ok.length} / {s.runs.length}</td><td>{ok.length ? fmtKM(ab.distanceM) : '—'}</td><td>{ok.length ? fmtKM(ao.distanceM) : '—'}</td><td>{s.averages.distanceReductionPct == null ? '—' : `${s.averages.distanceReductionPct.toFixed(1)}% ± ${stdev(reductions).toFixed(1)}`}</td><td>{ok.length && ab.onTimeRate != null ? `${Math.round(ab.onTimeRate * 100)}%` : '—'}</td><td>{ok.length && ao.onTimeRate != null ? `${Math.round(ao.onTimeRate * 100)}%` : '—'}</td><td>{solve.length ? `${Math.round(mean(solve))} ms` : '—'}</td><td>{ok.length ? `${Math.round(ao.satisfactionRate * 100)}% / ${ok.every(r => r.validationStatus === 'passed') ? '通过' : '待核验'}` : '—'}</td></tr>; })}</tbody></table></div>

      {failedRuns.failed.length > 0 && <div style={{ marginTop: 16 }}><div className="panel-title-row"><div><h3>失败诊断</h3><p>这里专门回答“为什么 S50 / S100 没跑通”，不要把失败当成空白数据。</p></div><StatusPill tone="danger">失败 {failedRuns.failed.length} 次</StatusPill></div><div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', margin: '10px 0 12px' }}>{failedRuns.byStage.map(([stage, count]) => <StatusPill key={stage} tone="warning">{STAGE_LABELS[stage] ?? stage}：{count}</StatusPill>)}</div><div className="table-wrap"><table><thead><tr><th>规模</th><th>模式</th><th>Seed</th><th>失败阶段</th><th>错误码</th><th>具体原因</th><th>任务ID</th></tr></thead><tbody>{failedRuns.failed.map((r) => <tr key={`${r.profile ?? 'standard'}-${r.size}-${r.seed}`}><td>S{r.size}</td><td>{r.profile === 'quick' ? '快检' : '标准'}</td><td>{r.seed}</td><td>{STAGE_LABELS[r.failureStage ?? 'unknown'] ?? r.failureStage ?? '未知阶段'}</td><td><code>{r.errorCode ?? '—'}</code></td><td className="muted-cell">{r.errorReason ?? r.error ?? '—'}{r.errorReason && r.error && r.error !== r.errorReason ? <div style={{ marginTop: 4, opacity: .8 }}>原始错误：{r.error}</div> : null}</td><td>{r.planningJobId || '—'}</td></tr>)}</tbody></table></div></div>}

      <div className="table-wrap" style={{ marginTop: 14 }}><table><thead><tr><th>规模</th><th>模式</th><th>Seed</th><th>状态</th><th>方案</th><th>距离</th><th>准时率</th><th>端到端耗时</th><th>方案校验</th><th>对比口径</th></tr></thead><tbody>{allRuns.map((r) => <tr key={`${r.profile ?? 'standard'}-${r.size}-${r.seed}`}><td>S{r.size}</td><td>{r.profile === 'quick' ? '快检' : '标准'}</td><td>{r.seed}</td><td>{r.status === 'succeeded' ? <StatusPill tone="success">成功</StatusPill> : <StatusPill tone="danger">失败</StatusPill>}</td><td>{r.planId ?? '—'}</td><td>{r.optimized ? fmtKM(r.optimized.distanceM) : '—'}</td><td>{r.optimized?.onTimeRate == null ? '—' : `${Math.round(r.optimized.onTimeRate * 100)}%`}</td><td>{r.wallMs == null ? '—' : `${r.wallMs} ms`}</td><td>{r.validationStatus ?? '—'}</td><td>{r.comparisonPct == null ? '不可比' : `${r.comparisonPct.toFixed(1)}%`}</td></tr>)}</tbody></table></div>
    </div>}

    <div className="panel" style={{ marginTop: 16 }}>
      <div className="panel-title-row"><div><h3>单次 S20 实验</h3><p>用于快速查看当前场景的 Baseline 与优化方案对比。</p></div><StatusPill tone={benchmark ? 'success' : 'info'}>{benchmark ? '已完成' : '待运行'}</StatusPill></div>
      {benchmark ? <>
        <div className="validation" style={{ marginTop: 14, marginBottom: 14 }}><div><span>满足率变化</span><b>{Math.round((benchmark.optimized.satisfactionRate - benchmark.baseline.satisfactionRate) * 100)} 个百分点</b></div><div><span>准时率变化</span><b>{benchmark.baseline.onTimeRate != null && benchmark.optimized.onTimeRate != null ? `${Math.round((benchmark.optimized.onTimeRate - benchmark.baseline.onTimeRate) * 100)} 个百分点` : '—'}</b></div><div><span>运输距离变化</span><b>{fairDistanceReduction(benchmark.baseline, benchmark.optimized) == null ? '不可比（有未服务订单）' : delta(benchmark.baseline.distanceM / 1000, benchmark.optimized.distanceM / 1000, 'km')}</b></div><div><span>车辆数变化</span><b>{benchmark.optimized.vehiclesUsed - benchmark.baseline.vehiclesUsed}</b></div></div>
        <div className="table-wrap"><table><thead><tr><th>指标</th><th>规则基线</th><th>优化方案</th><th>口径</th></tr></thead><tbody>{rows.map((r) => <tr key={r.name}><td><strong>{r.name}</strong></td><td>{r.baseline}</td><td>{r.optimized}</td><td className="muted-cell">{r.note}</td></tr>)}</tbody></table></div>
      </> : <div className="empty-state"><strong>还没有单次实验结果</strong><span>可以运行“单次 S20 实验”，或者直接运行上面的批量实验。</span></div>}
    </div>

    <div className="card-grid two" style={{ marginTop: 16 }}><div className="panel evidence-card"><div className="panel-title-row"><div><h3>怎么做实验</h3><p>自动化流程</p></div></div><div className="evidence-list"><span>① 生成固定规模 + seed 的可复现场景。</span><span>② 导入场景并调用现有 Planning Job：CP-SAT + Routing。</span><span>③ 用确定性规则基线计算同场景指标。</span><span>④ 自动保存每个 seed 的成功/失败结果，并汇总平均值。</span><span>⑤ 失败实验保留阶段、错误码和诊断原因，便于定位规模扩展瓶颈。</span></div></div><div className="panel evidence-card"><div className="panel-title-row"><div><h3>实验边界</h3><p>保持后端架构冻结</p></div></div><p className="scope-note">R16 快速排错 / 标准评测双模式：合成实验 v2，以 S20 为模板，按 Seed 调整订单需求/时间窗，并在同仓、同温区的既有节点中分配配送点；复用真实输入矩阵，不伪造路段。优化后路线必须逐单核验通过才计为成功。规则基线是固定优化仓储交接方案后的运输贪心法（并非独立的完整仓运方案）；两方有漏单时，距离优化率显示不可比。快检失败仅代表短预算未求得方案；快检与标准不混合统计。不同生成器版本也不能混为一组统计。</p></div></div>
  </div>;
}
