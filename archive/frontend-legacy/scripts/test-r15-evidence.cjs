/** Runs after npm ci: node scripts/test-r15-evidence.cjs. No API calls or OR-Tools required. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function compile(rel, requireMap = {}) {
  const src = fs.readFileSync(path.join(__dirname, '..', rel), 'utf8');
  const code = ts.transpileModule(src, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(code, {
    module, exports: module.exports,
    require: name => { if (name in requireMap) return requireMap[name]; throw new Error(`Unmocked dependency: ${name}`); },
    performance, fetch, console, Date, Math, JSON, Map, Set, Number, String, Array, Error,
  }, { filename: rel });
  return module.exports;
}

const core = compile('src/lib/benchmark.ts');
const batch = compile('src/lib/batchBenchmark.ts', {
  './http': { pollJob: async () => {}, postApi: async () => {} },
  './benchmark': core,
});
const snapshot = JSON.parse(fs.readFileSync(path.join(__dirname, '..', '..', 'data', 'scenarios', 'two_warehouses_20_orders.json'), 'utf8'));
let m = core.buildRuleBaseline(snapshot);
assert.equal(m.servedOrders, 20, 'Known S20 baseline coverage');
assert.equal(m.distanceM, 68000, 'Known S20 baseline distance');
assert.equal(core.fairDistanceReduction({ ...m, unservedOrders: 1 }, m), null, 'No distance comparison with omitted orders');
const missing = JSON.parse(JSON.stringify(snapshot));
missing.matrix.distance_m = missing.matrix.distance_m.map(row => [...row]);
missing.matrix.distance_m[0][2] = null;
assert.ok(core.buildRuleBaseline(missing).servedOrders < 20, 'Missing arc must not silently become 0');
const tooTight = JSON.parse(JSON.stringify(snapshot));
tooTight.orders[0].service_window.end_s = 0;
assert.ok(core.buildRuleBaseline(tooTight).servedOrders < 20, 'Impossible time window must be rejected');
const v17 = batch.buildBatchSnapshot(snapshot, 50, 17);
const v42 = batch.buildBatchSnapshot(snapshot, 50, 42);
assert.equal(v17.orders.length, 50);
assert.equal(v42.orders.length, 50);
assert.notEqual(batch.scenarioFingerprint(v17), batch.scenarioFingerprint(v42), 'Seeds must affect effective scenario inputs');
assert.equal(batch.scenarioFingerprint(v17), batch.scenarioFingerprint(batch.buildBatchSnapshot(snapshot, 50, 17)), 'Same seed is reproducible');
for (const o of v17.orders) assert.ok(snapshot.matrix.node_ids.includes(o.delivery_node_id), 'No invented matrix nodes');
const mockPlan = {
  snapshot_id: snapshot.snapshot_id, snapshot_version: snapshot.version,
  validation: { status: 'passed', violations: [] },
  warehouse: { metadata: { has_solution: true }, warehouse_handoffs: [] },
  routing: { metadata: { has_solution: true }, unserved_orders: [], routes: [] },
};
assert.ok(core.inspectOptimizedPlan(mockPlan, snapshot).length > 0, 'Empty plan may not pass order coverage');
// Construct a tiny feasible candidate plan; the independent checker must accept it.
const tiny = JSON.parse(JSON.stringify(snapshot));
tiny.orders = [snapshot.orders[0]];
tiny.vehicles = [snapshot.vehicles[0]];
const order = tiny.orders[0], vehicle = tiny.vehicles[0];
const ids = tiny.matrix.node_ids;
const dep = ids.indexOf(vehicle.start_node_id), dst = ids.indexOf(order.delivery_node_id);
const travel = tiny.matrix.duration_s[dep][dst], back = tiny.matrix.duration_s[dst][dep];
const t0 = Math.max(vehicle.available_at_s, vehicle.shift_window.start_s);
const arrival = t0 + travel, done = arrival + order.service_duration_s;
const route = {
  vehicle_id: vehicle.vehicle_id,
  distance_m: tiny.matrix.distance_m[dep][dst] + tiny.matrix.distance_m[dst][dep],
  duration_s: done + back - t0,
  stops: [
    { stop_kind: 'depot_start', node_id: vehicle.start_node_id, arrival_at_s: t0, service_start_at_s: t0, departure_at_s: t0, order_ids: [] },
    { stop_kind: 'delivery', node_id: order.delivery_node_id, arrival_at_s: arrival, service_start_at_s: arrival, departure_at_s: done, order_ids: [order.order_id] },
    { stop_kind: 'depot_end', node_id: vehicle.end_node_id, arrival_at_s: done + back, service_start_at_s: done + back, departure_at_s: done + back, order_ids: [] },
  ],
};
const tinyPlan = {
  ...mockPlan, routing: { ...mockPlan.routing, routes: [route] },
  warehouse: { ...mockPlan.warehouse, warehouse_handoffs: [{ order_id: order.order_id, warehouse_id: order.warehouse_id, ready_at_s: 0, loading_window: {start_s: 0, end_s: 28800} }] },
};
assert.deepEqual(Array.from(core.inspectOptimizedPlan(tinyPlan, tiny)), [], 'Valid one-order plan must pass');
assert.equal(core.optimizedMetrics(tinyPlan, tiny).servedOrders, 1);
const duplicate = JSON.parse(JSON.stringify(tinyPlan));
duplicate.routing.routes.push(JSON.parse(JSON.stringify(route)));
assert.ok(core.inspectOptimizedPlan(duplicate, tiny).length, 'Repeated vehicle/order must fail');
const group = batch.summarizeBatch(50, [{status:'succeeded',size:50,seed:17,baseline:{...m, unservedOrders:1},optimized:m,comparisonPct:null}]);
assert.equal(group.averages.distanceReductionPct, null, 'Invalid comparison must not be averaged into reported gains');
console.log('R15 frontend core evidence tests: PASS (baseline, matrix, windows, coverage, seeds, fairness)');
