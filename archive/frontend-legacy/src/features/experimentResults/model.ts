// View models for local evaluation artifacts; no HTTP or business DTO duplication.
export type MetricView = {
  value: number | null; unit: string; missing_reason: string | null;
  source: string; scope_id: string; window_start: number; window_end: number;
  definition_version: string;
};
export type RunView = {
  strategy: string; seed: number; status: string; end_to_end_ms: number;
  budget_exceeded: boolean; error?: string; metrics: Record<string, MetricView>;
};
export type Bundle = {
  strategies: string[]; seeds: number[]; budget: number; snapshotHash: string;
  runs: RunView[]; rawManifest: string; rawRuns: string;
};
function object(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${label} 必须是对象`);
  return value as Record<string, unknown>;
}
function string(value: unknown, label: string): string {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`${label} 缺少有效文本`);
  return value;
}
function number(value: unknown, label: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error(`${label} 不是有限数值`);
  return value;
}
function nonnegative(value: unknown, label: string): number {
  const n = number(value, label);
  if (!Number.isSafeInteger(n) || n < 0) throw new Error(`${label} 必须是非负整数`);
  return n;
}
export function readBundle(rawManifest: string, rawRuns: string): Bundle {
  const manifest = object(JSON.parse(rawManifest.replace(/^\uFEFF/, '')), 'manifest');
  if (!Array.isArray(manifest.strategies) || manifest.strategies.length < 2) throw new Error('至少需要两个策略');
  const strategies = manifest.strategies.map(x => string(x, '策略'));
  if (new Set(strategies).size !== strategies.length) throw new Error('策略重复');
  if (!Array.isArray(manifest.seeds) || !manifest.seeds.length) throw new Error('缺少重复编号');
  const seeds = manifest.seeds.map(x => nonnegative(x, '重复编号'));
  if (new Set(seeds).size !== seeds.length) throw new Error('重复编号不唯一');
  const budget = nonnegative(manifest.budget_ms, '预算');
  if (!budget) throw new Error('预算必须大于零');
  const snapshotHash = string(manifest.snapshot_sha256, '快照哈希');
  if (!/^[a-f0-9]{64}$/i.test(snapshotHash)) throw new Error('快照哈希格式错误');
  const keys = new Set<string>();
  const runs = rawRuns.replace(/^\uFEFF/, '').split(/\r?\n/).flatMap((line, index): RunView[] => {
    if (!line.trim()) return [];
    const label = `runs 第 ${index + 1} 行`;
    const row = object(JSON.parse(line), label);
    const strategy = string(row.strategy, label);
    const seed = nonnegative(row.seed, label);
    if (!strategies.includes(strategy) || !seeds.includes(seed)) throw new Error(`${label} 不在清单中`);
    const key = JSON.stringify([strategy, seed]);
    if (keys.has(key)) throw new Error(`${label} 策略与编号重复`);
    keys.add(key);
    const status = string(row.status, label);
    if (!['succeeded', 'failed', 'invalid'].includes(status)) throw new Error(`${label} 状态未知`);
    const elapsed = number(row.end_to_end_ms, label);
    if (elapsed < 0 || typeof row.budget_exceeded !== 'boolean' || row.budget_exceeded !== (elapsed > budget)) throw new Error(`${label} 耗时或超预算标记矛盾`);
    const metrics: Record<string, MetricView> = Object.create(null);
    for (const [name, entry] of Object.entries(row.metrics === undefined ? {} : object(row.metrics, label))) {
      const m = object(entry, `${label}/${name}`);
      const value = m.value === null ? null : number(m.value, name);
      const start = number(m.window_start, name), end = number(m.window_end, name);
      if (end <= start) throw new Error(`${label}/${name} 观测窗口无效`);
      metrics[name] = { value, unit: string(m.unit, name), source: string(m.source, name),
        scope_id: string(m.scope_id, name), definition_version: string(m.definition_version, name),
        window_start: start, window_end: end,
        missing_reason: value === null ? string(m.missing_reason, `${name} 缺失原因`) : null };
    }
    return [{ strategy, seed, status, end_to_end_ms: elapsed, budget_exceeded: row.budget_exceeded,
      error: typeof row.error === 'string' ? row.error : undefined, metrics }];
  });
  return { strategies, seeds, budget, snapshotHash, runs, rawManifest, rawRuns };
}
export function performance(runs: RunView[]) {
  const times = runs.map(r => r.end_to_end_ms).sort((a, b) => a - b);
  const n = times.length;
  return { count: n, failed: runs.filter(r => r.status !== 'succeeded').length,
    over: runs.filter(r => r.budget_exceeded).length,
    median: n ? (times[Math.floor((n - 1) / 2)] + times[Math.floor(n / 2)]) / 2 : null,
    p95: n ? times[Math.ceil(n * .95) - 1] : null };
}
export function pairDifference(a: RunView | undefined, b: RunView | undefined, metric: string) {
  if (!a || !b) return { reason: '缺少一侧运行', value: null };
  if (a.status !== 'succeeded' || b.status !== 'succeeded') return { reason: '存在失败或无效运行', value: null };
  if (a.budget_exceeded || b.budget_exceeded) return { reason: '存在超预算运行', value: null };
  const x = a.metrics[metric], y = b.metrics[metric];
  if (!x || !y || x.value === null || y.value === null) return { reason: '指标缺失', value: null };
  const fields = ['unit', 'source', 'scope_id', 'window_start', 'window_end', 'definition_version'] as const;
  if (fields.some(f => x[f] !== y[f])) return { reason: '指标口径不同', value: null };
  const difference = y.value - x.value;
  if (!Number.isFinite(difference)) return { reason: '差值超出数值范围', value: null };
  return { reason: x.unit, value: difference };
}
