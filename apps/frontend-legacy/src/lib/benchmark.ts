import type { CandidatePlan, Snapshot } from '../appTypes';

/** R15: explicitly separate plan feasibility from comparative performance. */
export type BenchmarkMetrics = {
  servedOrders: number;
  totalOrders: number;
  satisfactionRate: number;
  onTimeRate: number | null;
  unservedOrders: number;
  distanceM: number;
  routeDurationS: number;
  vehiclesUsed: number;
  vehicleUtilization: number | null;
  makespanS: number | null;
};

export type BenchmarkResult = {
  baseline: BenchmarkMetrics;
  optimized: BenchmarkMetrics;
  generatedAt: string;
  scenario: string;
  note: string;
};

type Order = Snapshot['orders'][number];
type Vehicle = Snapshot['vehicles'][number];
type Handoff = CandidatePlan['warehouse']['warehouse_handoffs'][number];
const EPS = 1e-6;

function arc(snapshot: Snapshot, from: string, to: string): { distanceM: number; durationS: number } | null {
  const ids = snapshot.matrix.node_ids;
  const i = ids.indexOf(from);
  const j = ids.indexOf(to);
  if (i < 0 || j < 0) return null;
  const distanceM = snapshot.matrix.distance_m[i]?.[j];
  const durationS = snapshot.matrix.duration_s[i]?.[j];
  if (distanceM == null || durationS == null || !Number.isFinite(distanceM) || !Number.isFinite(durationS) || distanceM < 0 || durationS < 0) return null;
  return { distanceM, durationS };
}

function handoffMap(plan?: CandidatePlan) {
  return new Map((plan?.warehouse.warehouse_handoffs ?? []).map(h => [h.order_id, h]));
}

function compatible(vehicle: Vehicle, order: Order) {
  return vehicle.warehouse_id === order.warehouse_id && vehicle.temperature_zone === order.temperature_zone;
}

type RouteAttempt = { distanceM: number; durationS: number; makespanS: number; served: number; weight: number; volume: number };
function attemptRoute(snapshot: Snapshot, vehicle: Vehicle, orders: Order[], handoffs: Map<string, Handoff>): RouteAttempt | null {
  if (!orders.length) return { distanceM: 0, durationS: 0, makespanS: 0, served: 0, weight: 0, volume: 0 };
  const weight = orders.reduce((s, o) => s + o.weight_kg, 0);
  const volume = orders.reduce((s, o) => s + o.volume_l, 0);
  if (weight > vehicle.remaining_weight_kg || volume > vehicle.remaining_volume_l) return null;
  if (orders.some(o => !compatible(vehicle, o))) return null;
  let startAt = Math.max(snapshot.simulation_time_s, vehicle.shift_window.start_s, vehicle.available_at_s);
  for (const order of orders) {
    const handoff = handoffs.get(order.order_id);
    if (handoff) {
      if (handoff.warehouse_id !== vehicle.warehouse_id) return null;
      startAt = Math.max(startAt, handoff.ready_at_s, handoff.loading_window.start_s);
    }
  }
  if (orders.some(o => { const h = handoffs.get(o.order_id); return h && startAt > h.loading_window.end_s; })) return null;
  if (startAt > vehicle.shift_window.end_s) return null;
  let now = startAt;
  let node = vehicle.start_node_id;
  let distanceM = 0;
  for (const order of orders) {
    const leg = arc(snapshot, node, order.delivery_node_id);
    if (!leg) return null; // Missing/unreachable nodes are never zero-distance arcs.
    const arrival = now + leg.durationS;
    const serviceAt = Math.max(arrival, order.service_window.start_s);
    const doneAt = serviceAt + order.service_duration_s;
    if (serviceAt > order.service_window.end_s || doneAt > order.freshness_deadline_s || doneAt > vehicle.shift_window.end_s) return null;
    now = doneAt;
    node = order.delivery_node_id;
    distanceM += leg.distanceM;
  }
  const back = arc(snapshot, node, vehicle.end_node_id);
  if (!back || now + back.durationS > vehicle.shift_window.end_s) return null;
  return { distanceM: distanceM + back.distanceM, durationS: now + back.durationS - startAt, makespanS: now + back.durationS, served: orders.length, weight, volume };
}

/** Deterministic, conservative one-trip rule baseline. Handoff constraints come from the same warehouse schedule as the optimized route. */
export function buildRuleBaseline(snapshot: Snapshot, plan?: CandidatePlan): BenchmarkMetrics {
  const orders = [...snapshot.orders].sort((a, b) => a.order_id.localeCompare(b.order_id));
  const handoffs = handoffMap(plan);
  const routes = snapshot.vehicles.map(vehicle => ({ vehicle, orders: [] as Order[], attempt: null as RouteAttempt | null }));
  for (const order of orders) {
    const candidates = routes.map((s, index) => {
      if (!compatible(s.vehicle, order)) return null;
      const attempt = attemptRoute(snapshot, s.vehicle, [...s.orders, order], handoffs);
      if (!attempt) return null;
      return { index, attempt, increment: attempt.distanceM - (s.attempt?.distanceM ?? 0) };
    }).filter((v): v is NonNullable<typeof v> => v !== null)
      .sort((a, b) => a.increment - b.increment || a.index - b.index);
    if (!candidates.length) continue;
    const pick = candidates[0];
    routes[pick.index].orders.push(order);
    routes[pick.index].attempt = pick.attempt;
  }
  const used = routes.filter(r => r.orders.length);
  const served = used.reduce((s, r) => s + r.orders.length, 0);
  const onTimeRate = served ? 1 : null; // accepted only if freshness and service windows were checked
  const utility = used.map(r => ((r.attempt!.weight / Math.max(1, r.vehicle.remaining_weight_kg)) + (r.attempt!.volume / Math.max(1, r.vehicle.remaining_volume_l))) / 2);
  return {
    servedOrders: served, totalOrders: orders.length,
    satisfactionRate: orders.length ? served / orders.length : 0, onTimeRate,
    unservedOrders: orders.length - served,
    distanceM: used.reduce((s, r) => s + r.attempt!.distanceM, 0),
    routeDurationS: used.reduce((s, r) => s + r.attempt!.durationS, 0),
    vehiclesUsed: used.length,
    vehicleUtilization: utility.length ? utility.reduce((s, u) => s + u, 0) / utility.length : null,
    makespanS: used.length ? Math.max(...used.map(r => r.attempt!.makespanS)) : null,
  };
}

/** Frontend evidence cross-check in addition to the backend's independent validation. */
export function inspectOptimizedPlan(plan: CandidatePlan, snapshot: Snapshot): string[] {
  const issues: string[] = [];
  const orders = new Map(snapshot.orders.map(o => [o.order_id, o]));
  const vehicles = new Map(snapshot.vehicles.map(v => [v.vehicle_id, v]));
  const handoffs = handoffMap(plan);
  const seenOrder = new Map<string, number>();
  const seenVehicles = new Set<string>();
  if (plan.validation.status !== 'passed' || plan.validation.violations.length) issues.push('后端独立校验未通过');
  if (!plan.routing.metadata.has_solution) issues.push('Routing 未报告可行解');
  if (!plan.warehouse.metadata.has_solution) issues.push('CP-SAT 未报告可行解');
  if (plan.snapshot_id !== snapshot.snapshot_id || plan.snapshot_version !== snapshot.version) issues.push('方案与输入快照不一致');
  if (plan.routing.unserved_orders.length) issues.push(`后端报告 ${plan.routing.unserved_orders.length} 个未服务订单`);
  for (const route of plan.routing.routes) {
    if (seenVehicles.has(route.vehicle_id)) issues.push(`车辆重复使用：${route.vehicle_id}`);
    seenVehicles.add(route.vehicle_id);
    const vehicle = vehicles.get(route.vehicle_id);
    if (!vehicle) { issues.push(`未知车辆：${route.vehicle_id}`); continue; }
    const stops = route.stops;
    if (stops.length < 2 || stops[0].stop_kind !== 'depot_start' || stops[stops.length - 1].stop_kind !== 'depot_end') {
      issues.push(`车辆 ${route.vehicle_id} 缺少起终点`); continue;
    }
    if (stops[0].node_id !== vehicle.start_node_id || stops[stops.length - 1].node_id !== vehicle.end_node_id) issues.push(`车辆 ${route.vehicle_id} 起终点不符`);
    const startAt = stops[0].arrival_at_s;
    if (startAt < vehicle.shift_window.start_s || startAt < vehicle.available_at_s) issues.push(`车辆 ${route.vehicle_id} 早于可用时间出发`);
    if (stops[stops.length - 1].arrival_at_s > vehicle.shift_window.end_s) issues.push(`车辆 ${route.vehicle_id} 晚于班次结束`);
    let weight = 0;
    let volume = 0;
    let distanceM = 0;
    for (const stop of stops.slice(1, -1)) {
      if (stop.stop_kind !== 'delivery' || stop.order_ids.length !== 1) { issues.push(`车辆 ${route.vehicle_id} 配送站点订单数异常`); continue; }
      const oid = stop.order_ids[0];
      seenOrder.set(oid, (seenOrder.get(oid) ?? 0) + 1);
      const order = orders.get(oid);
      if (!order) { issues.push(`未知订单：${oid}`); continue; }
      if (vehicle.warehouse_id !== order.warehouse_id || vehicle.temperature_zone !== order.temperature_zone) issues.push(`订单 ${oid} 仓库/温区不匹配`);
      if (stop.node_id !== order.delivery_node_id) issues.push(`订单 ${oid} 配送节点不符`);
      if (stop.service_start_at_s < order.service_window.start_s || stop.service_start_at_s > order.service_window.end_s) issues.push(`订单 ${oid} 时间窗违反`);
      if (stop.service_start_at_s < stop.arrival_at_s ||
          stop.departure_at_s < stop.service_start_at_s + order.service_duration_s) issues.push(`订单 ${oid} 服务时长异常`);
      if (stop.departure_at_s > order.freshness_deadline_s) issues.push(`订单 ${oid} 新鲜度截止时间违反`);
      const handoff = handoffs.get(oid);
      if (!handoff || startAt < handoff.ready_at_s || startAt > handoff.loading_window.end_s) issues.push(`订单 ${oid} 仓运交接违反`);
      weight += order.weight_kg;
      volume += order.volume_l;
    }
    if (weight > vehicle.remaining_weight_kg || volume > vehicle.remaining_volume_l) issues.push(`车辆 ${route.vehicle_id} 超载`);
    for (let i = 1; i < stops.length; i += 1) {
      const prev = stops[i - 1];
      const next = stops[i];
      const leg = arc(snapshot, prev.node_id, next.node_id);
      if (!leg) { issues.push(`车辆 ${route.vehicle_id} 不可达路段`); continue; }
      distanceM += leg.distanceM;
      if (next.arrival_at_s + EPS < prev.departure_at_s + leg.durationS) issues.push(`车辆 ${route.vehicle_id} 行驶时间不连续`);
    }
    if (Math.abs(distanceM - route.distance_m) > EPS) issues.push(`车辆 ${route.vehicle_id} 距离不一致`);
  }
  for (const order of snapshot.orders) {
    const n = seenOrder.get(order.order_id) ?? 0;
    if (order.required && n !== 1) issues.push(`必服务订单 ${order.order_id} 出现 ${n} 次`);
    if (n > 1) issues.push(`订单 ${order.order_id} 重复配送`);
  }
  return [...new Set(issues)];
}

export function optimizedMetrics(plan: CandidatePlan, snapshot: Snapshot): BenchmarkMetrics {
  const issues = inspectOptimizedPlan(plan, snapshot);
  if (issues.length) throw new Error(`R15_PLAN_VALIDATION_FAILED:${issues.slice(0, 8).join('；')}`);
  const servedIds = new Set(plan.routing.routes.flatMap(route => route.stops.filter(s => s.stop_kind === 'delivery').flatMap(s => s.order_ids)));
  const served = servedIds.size;
  const onTime = plan.routing.routes.flatMap(route => route.stops.filter(s => s.stop_kind === 'delivery'))
    .flatMap(stop => stop.order_ids.map(id => ({ stop, order: snapshot.orders.find(o => o.order_id === id) })))
    .filter(({ order }) => order && order.required)
    .filter(({ stop, order }) => stop.departure_at_s <= order!.freshness_deadline_s).length;
  const vehicles = new Map(snapshot.vehicles.map(v => [v.vehicle_id, v]));
  const utilization = plan.routing.routes.map(route => {
    const v = vehicles.get(route.vehicle_id)!;
    const o = route.stops.flatMap(stop => stop.stop_kind === 'delivery' ? stop.order_ids : []).map(id => snapshot.orders.find(x => x.order_id === id)!);
    return ((o.reduce((s, x) => s + x.weight_kg, 0) / Math.max(1, v.remaining_weight_kg)) + (o.reduce((s, x) => s + x.volume_l, 0) / Math.max(1, v.remaining_volume_l))) / 2;
  });
  return {
    servedOrders: served, totalOrders: snapshot.orders.length, satisfactionRate: snapshot.orders.length ? served / snapshot.orders.length : 0,
    onTimeRate: served ? onTime / served : null,
    unservedOrders: snapshot.orders.length - served,
    distanceM: plan.routing.routes.reduce((s, r) => s + r.distance_m, 0),
    routeDurationS: plan.routing.routes.reduce((s, r) => s + r.duration_s, 0),
    vehiclesUsed: plan.routing.routes.length,
    vehicleUtilization: utilization.length ? utilization.reduce((s, u) => s + u, 0) / utilization.length : null,
    makespanS: plan.routing.routes.length ? Math.max(...plan.routing.routes.map(r => r.stops[r.stops.length - 1].arrival_at_s)) : null,
  };
}

/** Never compare distance of two plans unless both serve exactly the same set. */
export function fairDistanceReduction(baseline?: BenchmarkMetrics, optimized?: BenchmarkMetrics): number | null {
  if (!baseline || !optimized || baseline.totalOrders !== optimized.totalOrders ||
      baseline.unservedOrders !== 0 || optimized.unservedOrders !== 0 ||
      baseline.servedOrders !== optimized.servedOrders || baseline.distanceM <= 0) return null;
  return (1 - optimized.distanceM / baseline.distanceM) * 100;
}

export async function runBenchmark(snapshot: Snapshot, optimizedPlan: CandidatePlan): Promise<BenchmarkResult> {
  const baseline = buildRuleBaseline(snapshot, optimizedPlan);
  const optimized = optimizedMetrics(optimizedPlan, snapshot);
  return {
    baseline, optimized, generatedAt: new Date().toISOString(),
    scenario: `${snapshot.orders.length}订单 · ${snapshot.warehouses.length}仓库`,
    note: 'R15：使用同一快照和优化方案的仓储交接时间；两者均检查硬约束。仅在双方全部配送时比较运输距离。此基线为固定仓储方案下的贪心运输规则，非完整仓运联合基线。',
  };
}
