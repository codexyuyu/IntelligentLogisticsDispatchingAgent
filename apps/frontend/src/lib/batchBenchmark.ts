import type { CandidatePlan, Snapshot } from '../appTypes';
import { getJson, pollJob, postApi } from './http';
import { buildRuleBaseline, fairDistanceReduction, optimizedMetrics, type BenchmarkMetrics } from './benchmark';

/** Quick checks reduce the solver time limit; use standard for publishable comparisons. */
export type BenchmarkProfile = 'quick' | 'standard';
export const FAST_BUDGET_MS: Record<number, number> = { 20: 8000, 50: 12000, 100: 18000 };
export const STANDARD_BUDGET_MS = 60000;
export function budgetForScale(size: number, profile: BenchmarkProfile): number {
  if (![20, 50, 100].includes(size)) throw new Error(`unsupported_benchmark_size:${size}`);
  return profile === 'standard' ? STANDARD_BUDGET_MS : FAST_BUDGET_MS[size];
}

export type BatchSeedRun = {
  size: number;
  seed: number;
  profile?: BenchmarkProfile; // Historical R15 runs have no profile; treat as standard.
  scenarioId: string;
  planningJobId: string;
  status: 'succeeded' | 'failed';
  failureStage?: 'scenario_import' | 'planning_submit' | 'planning_solve' | 'plan_fetch' | 'metric_calculation' | 'unknown';
  errorCode?: string;
  errorReason?: string;
  error?: string;
  baseline?: BenchmarkMetrics;
  optimized?: BenchmarkMetrics;
  planId?: string;
  solveMs?: number; // Legacy: sum of reported stage times (NOT wall-clock)
  wallMs?: number; // Measured browser end-to-end Planning Job + retrieval
  warehouseMs?: number;
  routingMs?: number;
  budgetMs?: number;
  validationStatus?: 'passed' | 'failed' | 'not_checked';
  comparisonPct?: number | null;
  scenarioFingerprint?: string;
  scenarioVersion?: string;
  snapshot?: Snapshot; // Preserve exact experiment input in export
  runAt?: string;
};

export type BatchBenchmarkSummary = {
  size: number;
  profile?: BenchmarkProfile;
  runs: BatchSeedRun[];
  averages: {
    baseline: BenchmarkMetrics;
    optimized: BenchmarkMetrics;
    distanceReductionPct: number | null;
    makespanReductionPct: number | null;
  };
};

type AnySnapshot = Snapshot & {
  [key: string]: any;
};

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function hash(seed: number, n: number) {
  let x = (seed * 9301 + 49297 + n * 233) % 233280;
  x = (x * 9301 + 49297) % 233280;
  return x / 233280;
}

function pad(n: number) {
  return String(n).padStart(3, '0');
}

/**
 * Build a deterministic stress scenario from the existing S20 template.
 * This is intentionally frontend-owned so the current backend contract is untouched.
 * The generator reuses the existing warehouses, resources and travel matrix, and
 * expands orders/vehicles/resources only through the already supported snapshot schema.
 */
export function buildBatchSnapshot(base: Snapshot, size: number, seed: number): Snapshot {
  if (![20, 50, 100].includes(size)) throw new Error('实验规模只支持 20 / 50 / 100');

  const out = clone(base) as AnySnapshot;
  const templates = clone(base.orders) as any[];
  const templateVehicles = clone(base.vehicles) as any[];
  const whIds = out.warehouses.map((w: any) => w.warehouse_id);
  const byWh = new Map<string, any[]>();
  for (const o of templates) {
    const arr = byWh.get(o.warehouse_id) ?? [];
    arr.push(o);
    byWh.set(o.warehouse_id, arr);
  }

  // Seed v2: deterministic destination rotation within the SAME warehouse + temperature
  // group, using only existing matrix nodes. No synthetic geography is invented.
  const destinationGroups = new Map<string, string[]>();
  for (const template of templates) {
    const key = `${template.warehouse_id}:${template.temperature_zone}`;
    const nodes = destinationGroups.get(key) ?? [];
    if (!nodes.includes(template.delivery_node_id)) nodes.push(template.delivery_node_id);
    destinationGroups.set(key, nodes);
  }
  const orders: any[] = [];
  const stockLots: any[] = [];
  const operations: any[] = [];

  for (let i = 0; i < size; i += 1) {
    const template = templates[i % templates.length];
    const o = clone(template);
    const jitter = Math.floor(hash(seed, i) * 900);
    const qtyFactor = 0.92 + hash(seed + 11, i) * 0.12;
    const qty = Math.max(1, Math.round(template.quantity_units * qtyFactor));
    const ratio = qty / Math.max(1, template.quantity_units);

    o.order_id = `ord_${pad(i + 1)}`;
    const options = destinationGroups.get(`${template.warehouse_id}:${template.temperature_zone}`) ?? [];
    if (options.length > 1) {
      // Spread locations across the original set; distinct seeds change actual route inputs.
      const index = Math.floor(hash(seed + 37, i + 13) * options.length);
      o.delivery_node_id = options[index];
    }
    o.version = 1;
    o.quantity_units = qty;
    o.weight_kg = Math.max(1, Math.round(template.weight_kg * ratio));
    o.volume_l = Math.max(1, Math.round(template.volume_l * ratio));
    o.service_window = {
      start_s: template.service_window.start_s + jitter,
      end_s: template.service_window.end_s + jitter,
    };
    o.freshness_deadline_s = template.freshness_deadline_s + jitter;
    o.source = {
      ...template.source,
      source_ref: `synthetic:benchmark:S${size}:seed${seed}`,
    };

    orders.push(o);

    stockLots.push({
      batch_id: `batch_${pad(i + 1)}`,
      warehouse_id: o.warehouse_id,
      version: 1,
      temperature_zone: o.temperature_zone,
      on_hand_units: qty,
      reserved_units: 0,
      quarantined_units: 0,
      expires_at: new Date(Date.parse(out.origin_at) + (86400 + jitter) * 1000).toISOString(),
    });

    const resourceId = o.warehouse_id === 'wh_1' ? 'res_dock1' : 'res_dock2';
    operations.push({
      operation_id: `op_load${pad(i + 1)}`,
      order_ids: [o.order_id],
      warehouse_id: o.warehouse_id,
      resource_id: resourceId,
      operation_kind: 'loading',
      duration_s: 60,
      release_at_s: o.service_window.start_s,
      deadline_at_s: o.service_window.end_s,
      predecessor_ids: [],
      status: 'pending',
    });
  }

  const vehicleCounts = new Map<string, { chilled: number; frozen: number }>();
  for (const whId of whIds) vehicleCounts.set(whId, { chilled: 0, frozen: 0 });
  for (const o of orders) {
    const c = vehicleCounts.get(o.warehouse_id);
    if (c) c[o.temperature_zone === 'frozen' ? 'frozen' : 'chilled'] += 1;
  }

  const vehicles: any[] = [];
  let vehicleIndex = 1;
  for (const whId of whIds) {
    const baseVehicle = templateVehicles.find((v) => v.warehouse_id === whId);
    const zoneCounts = vehicleCounts.get(whId) ?? { chilled: 1, frozen: 1 };
    for (const zone of ['chilled', 'frozen'] as const) {
      const needed = Math.max(1, Math.ceil(zoneCounts[zone] / 10));
      for (let n = 0; n < needed; n += 1) {
        const source = templateVehicles.find((v) => v.warehouse_id === whId && v.temperature_zone === zone) ?? baseVehicle;
        if (!source) continue;
        const v = clone(source);
        v.vehicle_id = `veh_${vehicleIndex}`;
        v.version = 1;
        v.source = {
          ...source.source,
          source_ref: `synthetic:benchmark:S${size}:seed${seed}`,
        };
        vehicles.push(v);
        vehicleIndex += 1;
      }
    }
  }

  out.snapshot_id = `bench_${size}_${seed}_${Date.now()}`;
  out.version = 1;
  out.rule_version = 'rules-0.1';
  out.orders = orders;
  out.vehicles = vehicles;
  out.stock_lots = stockLots;
  out.operations = operations;
  out.frozen_operations = [];
  return out as Snapshot;
}

export const BENCHMARK_SCENARIO_VERSION = 'r15-synthetic-v2';

export function scenarioFingerprint(snapshot: Snapshot): string {
  // FNV-1a over stable, relevant inputs; suitable for detecting identical seed scenarios, not cryptographic signing.
  const data = JSON.stringify({
    orders: snapshot.orders.map(o => [o.order_id, o.delivery_node_id, o.warehouse_id, o.temperature_zone,
      o.weight_kg, o.volume_l, o.service_window.start_s, o.service_window.end_s, o.freshness_deadline_s]),
    vehicles: snapshot.vehicles.map(v => [v.vehicle_id, v.remaining_weight_kg, v.remaining_volume_l, v.shift_window]),
    matrix: [snapshot.matrix.node_ids, snapshot.matrix.distance_m, snapshot.matrix.duration_s],
    operations: snapshot.operations.map(o => [o.operation_id, o.release_at_s, o.deadline_at_s]),
  });
  let h = 2166136261;
  for (let i = 0; i < data.length; i++) { h ^= data.charCodeAt(i); h = Math.imul(h, 16777619); }
  return `fnv1a-${(h >>> 0).toString(16).padStart(8, '0')}`;
}


function aggregateMetrics(items: BenchmarkMetrics[]): BenchmarkMetrics {
  if (items.length === 0) {
    return { servedOrders: 0, totalOrders: 0, satisfactionRate: 0, onTimeRate: null, unservedOrders: 0, distanceM: 0, routeDurationS: 0, vehiclesUsed: 0, vehicleUtilization: null, makespanS: null };
  }
  const avg = (fn: (m: BenchmarkMetrics) => number) => items.reduce((s, m) => s + fn(m), 0) / items.length;
  const withOnTime = items.filter((m) => m.onTimeRate != null);
  const withUtil = items.filter((m) => m.vehicleUtilization != null);
  const withMakespan = items.filter((m) => m.makespanS != null);
  return {
    servedOrders: Math.round(avg((m) => m.servedOrders)),
    totalOrders: Math.round(avg((m) => m.totalOrders)),
    satisfactionRate: avg((m) => m.satisfactionRate),
    onTimeRate: withOnTime.length ? withOnTime.reduce((s, m) => s + (m.onTimeRate ?? 0), 0) / withOnTime.length : null,
    unservedOrders: Math.round(avg((m) => m.unservedOrders)),
    distanceM: avg((m) => m.distanceM),
    routeDurationS: avg((m) => m.routeDurationS),
    vehiclesUsed: avg((m) => m.vehiclesUsed),
    vehicleUtilization: withUtil.length ? withUtil.reduce((s, m) => s + (m.vehicleUtilization ?? 0), 0) / withUtil.length : null,
    makespanS: withMakespan.length ? withMakespan.reduce((s, m) => s + (m.makespanS ?? 0), 0) / withMakespan.length : null,
  };
}

export function summarizeBatch(size: number, runs: BatchSeedRun[], profile: BenchmarkProfile = 'standard'): BatchBenchmarkSummary {
  const succeeded = runs.filter((r) => r.status === 'succeeded' && r.baseline && r.optimized);
  const baseline = aggregateMetrics(succeeded.map((r) => r.baseline!));
  const optimized = aggregateMetrics(succeeded.map((r) => r.optimized!));
  return {
    size,
    profile,
    runs,
    averages: {
      baseline,
      optimized,
      distanceReductionPct: succeeded.length && succeeded.every(r => r.comparisonPct != null) ? fairDistanceReduction(baseline, optimized) : null,
      makespanReductionPct: baseline.makespanS && optimized.makespanS ? (1 - optimized.makespanS / baseline.makespanS) * 100 : null,
    },
  };
}

function classifyError(errorCode: string | undefined, fallbackMessage: string): { stage: BatchSeedRun['failureStage']; code: string; reason: string } {
  const code = errorCode || 'experiment_failed';
  const normalized = code.toLowerCase();
  if (normalized.includes('snapshot') || normalized.includes('scenario') || normalized.includes('version_conflict')) {
    return { stage: 'scenario_import', code, reason: '场景导入或场景版本校验失败，请检查场景数据是否符合当前契约。' };
  }
  if (normalized.includes('capacity_weight_insufficient') || normalized.includes('capacity_volume_insufficient')) {
    return { stage: 'planning_solve', code, reason: '运输运力总容量不足：该温区订单需求超过所有兼容车辆可提供的剩余容量，属于可提前证明的不可行场景。' };
  }
  if (normalized.includes('no_compatible_vehicle')) {
    return { stage: 'planning_solve', code, reason: '存在必服务订单没有任何兼容车辆，Routing 无法建立可行方案。' };
  }
  if (normalized.includes('warehouse') || normalized.includes('cp_sat') || normalized.includes('cpsat')) {
    return { stage: 'planning_solve', code, reason: '仓储 CP-SAT 排程阶段失败，可能是资源、时间窗或仓储约束导致不可行。' };
  }
  if (normalized.includes('routing') || normalized.includes('route')) {
    return { stage: 'planning_solve', code, reason: '运输 Routing 求解阶段失败，当前请求在限定搜索预算内没有找到可行路线；请结合订单、车辆、时间窗和温区诊断继续分析。' };
  }
  if (normalized.includes('coordination')) {
    return { stage: 'planning_solve', code, reason: '仓运协同阶段失败，可能是仓储与运输衔接约束或协调预算导致失败。' };
  }
  if (normalized.includes('plan') && normalized.includes('http')) {
    return { stage: 'plan_fetch', code, reason: '规划结果读取失败，Planning Job 可能已经完成但方案接口读取失败。' };
  }
  if (normalized.includes('r15_plan_validation_failed')) {
    return { stage: 'metric_calculation', code: 'R15_PLAN_VALIDATION_FAILED', reason: fallbackMessage };
  }
  if (normalized.includes('metric') || normalized.includes('baseline')) {
    return { stage: 'metric_calculation', code, reason: '方案已经生成，但实验指标计算阶段出现异常。' };
  }
  if (normalized.includes('timeout') || normalized.includes('超过')) {
    return { stage: 'planning_solve', code: 'job_timeout', reason: 'Planning Job 在规定等待时间内没有完成。' };
  }
  return { stage: 'unknown', code, reason: fallbackMessage || '未识别的实验失败原因，请查看后端任务日志。' };
}

export async function runBatchBenchmark(
  base: Snapshot,
  sizes: number[],
  seeds: number[],
  onProgress?: (message: string, completed: number, total: number) => void,
  profile: BenchmarkProfile = 'quick',
  onRunComplete?: (run: BatchSeedRun) => void,
): Promise<BatchBenchmarkSummary[]> {
  const uniqueSizes = Array.from(new Set(sizes.filter((n) => [20, 50, 100].includes(n))));
  const uniqueSeeds = Array.from(new Set(seeds)).filter((n) => Number.isFinite(n) && n >= 0).slice(0, 8);
  if (!uniqueSizes.length || !uniqueSeeds.length) throw new Error('请选择至少一个规模和一个 seed');

  const total = uniqueSizes.length * uniqueSeeds.length;
  let completed = 0;
  const grouped = new Map<number, BatchSeedRun[]>();

  for (const size of uniqueSizes) {
    const runs: BatchSeedRun[] = [];
    for (const seed of uniqueSeeds) {
      const budgetMs = budgetForScale(size, profile);
      const snap = buildBatchSnapshot(base, size, seed);
      const scenarioId = `benchmark_s${size}_seed${seed}_${profile}`;
      snap.snapshot_id = scenarioId; // import and local verifier must share the canonical id
      let failureStage: BatchSeedRun['failureStage'] = 'unknown';
      const started = performance.now();
      let planningJobId = '';
      try {
        failureStage = 'scenario_import';
        onProgress?.(`正在运行 S${size} / seed ${seed}：导入场景`, completed, total);
        const imported = await postApi<{ snapshot_id: string; version: number }>('/api/v1/scenarios/import', {
          scenario_id: scenarioId,
          snapshot: { ...snap, snapshot_id: scenarioId },
        }, `ui-benchmark-import-${size}-${seed}-${Date.now()}`);

        failureStage = 'planning_submit';
        onProgress?.(`正在运行 S${size} / seed ${seed}：${profile === 'quick' ? '快速排错' : '标准评测'}，预算 ${budgetMs / 1000} 秒`, completed, total);
        const accepted = await postApi<{ job_id: string; status?: string }>('/api/v1/planning-jobs', {
          snapshot_id: imported.snapshot_id,
          expected_snapshot_version: imported.version,
          order_ids: snap.orders.map((o) => o.order_id),
          budget_ms: budgetMs,
          max_coordination_rounds: 3,
        }, `ui-benchmark-plan-${size}-${seed}-${Date.now()}`);
        planningJobId = accepted.job_id;
        snap.snapshot_id = imported.snapshot_id;
        snap.version = imported.version;

        failureStage = 'planning_solve';
        onProgress?.(`正在运行 S${size} / seed ${seed}：等待 CP-SAT + Routing`, completed, total);
        // Polling deadline includes a margin for CP-SAT, API overhead and HTTP polling.
        const job = await pollJob(accepted.job_id, undefined, Math.ceil(budgetMs / 1000) + 35);
        if (job.status !== 'succeeded' || !job.plan_id) {
          const raw = String(job.error_code ?? accepted.status ?? '规划失败');
          throw new Error(raw);
        }

        failureStage = 'plan_fetch';
        const body = await getJson<{ plan: CandidatePlan }>(`/api/v1/plans/${encodeURIComponent(job.plan_id)}`);

        failureStage = 'metric_calculation';
        const optimized = optimizedMetrics(body.plan, snap); // independently validates before accepting success
        const baseline = buildRuleBaseline(snap, body.plan);
        const routingMs = Number(body.plan.routing.metadata?.solve_ms ?? 0);
        const warehouseMs = Number(body.plan.warehouse.metadata?.solve_ms ?? 0);
        const solveMs = routingMs + warehouseMs;
        const wallMs = Math.round(performance.now() - started);
        runs.push({ size, seed, profile, scenarioId, planningJobId, status: 'succeeded', baseline, optimized,
          planId: body.plan.plan_id, solveMs, wallMs, routingMs, warehouseMs, budgetMs,
          validationStatus: body.plan.validation.status, comparisonPct: fairDistanceReduction(baseline, optimized),
          scenarioFingerprint: scenarioFingerprint(snap), scenarioVersion: BENCHMARK_SCENARIO_VERSION,
          snapshot: snap, runAt: new Date().toISOString() });
      } catch (e) {
        const message = e instanceof Error ? e.message : '实验失败';
        const meta = classifyError(message, message);
        // A short-budget VRPTW search can fail to find its first solution;
        // this is NOT proof the input is impossible. Preserve the raw error.
        const quickUnknown = profile === 'quick' && failureStage === 'planning_solve'
          && /ROUTING_NO_SOLUTION|budget_exhausted|job_timeout/i.test(message);
        if (quickUnknown) {
          meta.code = 'QUICK_BUDGET_NOT_SOLVED';
          meta.reason = `快速排错的 ${budgetMs / 1000} 秒预算内未找到方案，不能判定不可行；请用60秒标准评测复核。`;
        }
        runs.push({
          size,
          seed,
          profile,
          scenarioId,
          planningJobId,
          status: 'failed',
          failureStage,
          errorCode: meta.code,
          errorReason: meta.reason,
          error: message,
          wallMs: Math.round(performance.now() - started), budgetMs,
          scenarioFingerprint: scenarioFingerprint(snap), scenarioVersion: BENCHMARK_SCENARIO_VERSION,
          snapshot: snap, runAt: new Date().toISOString(),
        });
      } finally {
        // Checkpoint after each seed: a refresh during a long batch should not
        // discard results from already completed seeds.
        if (runs.length) onRunComplete?.(runs[runs.length - 1]);
        completed += 1;
        onProgress?.(`已完成 S${size} / seed ${seed}`, completed, total);
      }
    }
    grouped.set(size, runs);
  }

  return uniqueSizes.map((size) => summarizeBatch(size, grouped.get(size) ?? [], profile));
}

