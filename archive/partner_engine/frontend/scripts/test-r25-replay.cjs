// R25 pure animation/route tests; runs without React, Three.js, browsers or OSRM.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const cp = require('node:child_process');
let ts;
try { ts = require('typescript'); }
catch { ts = require(path.join(cp.execFileSync('npm', ['root', '-g'], { encoding: 'utf8' }).trim(), 'typescript')); }
const root = path.join(__dirname, '..');
function transpiledModule(file) {
  const content = fs.readFileSync(path.join(root, file), 'utf8');
  const compiled = ts.transpileModule(content, {
    fileName: file, compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }, reportDiagnostics: true,
  });
  const diagnostics = (compiled.diagnostics || []).filter((item) => item.category === ts.DiagnosticCategory.Error);
  assert.equal(diagnostics.length, 0, `${file}: ${diagnostics.map((item) => ts.flattenDiagnosticMessageText(item.messageText, '\n'))}`);
  const module = { exports: {} };
  const execute = new Function('module', 'exports', 'require', compiled.outputText);
  execute(module, module.exports, (id) => { throw new Error(`Unexpected runtime import in pure module: ${id}`); });
  return module.exports;
}
const { buildFourVehicleShowcase } = transpiledModule('src/lib/fleetDemo.ts');
const { roadLikeLeg, buildRouteMotion, sampleMotion, geoProjection } = transpiledModule('src/lib/replayPaths.ts');
const warehouses = [
  { warehouse_id: 'wh_1', node_id: 'node_wh_1' },
  { warehouse_id: 'wh_2', node_id: 'node_wh_2' },
];
const vehicles = Array.from({ length: 4 }, (_, i) => ({
  vehicle_id: `veh_${i + 1}`, warehouse_id: i < 2 ? 'wh_1' : 'wh_2', temperature_zone: i < 2 ? 'chilled' : 'frozen',
}));
const orders = Array.from({ length: 20 }, (_, i) => ({ order_id: `ord_${i + 1}`, delivery_node_id: `node_ord_${i + 1}` }));
const routes = buildFourVehicleShowcase(orders, vehicles, warehouses);
assert.equal(routes.length, 4, 'four trucks must run independently');
assert.equal(new Set(routes.map((r) => r.vehicleId)).size, 4);
assert.equal(routes.reduce((n, r) => n + r.stops.filter((s) => s.kind === 'delivery').length, 0), 20);
assert.equal(new Set(routes.map((r) => r.stops[0].departureS)).size, 4, 'departures must be staggered');
assert.equal(new Set(routes.map((r) => r.stops.map((s) => s.nodeId).join('|'))).size, 4, 'routes must be distinct');
assert.equal(buildFourVehicleShowcase(orders, vehicles.slice(0, 3), warehouses).length, 0, 'no fabricated missing fourth truck');
assert.equal(roadLikeLeg({ x: 0, z: 0 }, { x: 5, z: 7 }).length, 3);
const schematic = buildRouteMotion(routes[0], Object.fromEntries([
  ['node_wh_1', { x: -16, z: 0 }],
  ...orders.map((order, i) => [order.delivery_node_id, { x: i * 2, z: (i % 3) * 3 }]),
]));
assert.ok(schematic && schematic.legs.length > 0);
assert.equal(sampleMotion(schematic, -1).moving, false);
assert.equal(sampleMotion(schematic, 0).moving, false);
assert.equal(sampleMotion(schematic, 90).moving, true);
const firstArrival = routes[0].stops[1].arrivalS;
assert.equal(sampleMotion(schematic, firstArrival + 20).moving, false, 'service dwell must stop movement');
const projection = geoProjection([{ roadCoordinates: [[116.4,39.9],[116.41,39.9],[116.42,39.91]], stops: [] }]);
assert.ok(projection && Number.isFinite(projection(116.42, 39.91).x));
const geoRoute = {
  vehicleId: 'v', roadCoordinates: [[116.4,39.9],[116.41,39.9],[116.42,39.91]],
  stopCoordinates: [[116.4,39.9],[116.42,39.91]],
  stops: [{nodeId:'a',departureS:0,arrivalS:0},{nodeId:'b',arrivalS:100,departureS:100}],
};
const motion = buildRouteMotion(geoRoute, {a:projection(116.4,39.9), b:projection(116.42,39.91)}, geoRoute.roadCoordinates.map((p) => projection(...p)));
assert.equal(motion.legs[0].points.length, 3, 'OSRM polyline must be preserved, not replaced with straight line');
assert.equal(sampleMotion(motion, 100).moving, false);
for (const file of ['src/components/DigitalTwin3D.tsx','src/features/dashboard/Page.tsx','src/features/simulations/Page.tsx','src/features/postgres/Page.tsx','src/hooks/useSimClock.ts']) {
  const content = fs.readFileSync(path.join(root, file), 'utf8');
  const compiled = ts.transpileModule(content, { fileName: file, compilerOptions: { jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 }, reportDiagnostics: true });
  assert.equal((compiled.diagnostics || []).filter((d) => d.category === ts.DiagnosticCategory.Error).length, 0, `TS syntax: ${file}`);
}
const twin = fs.readFileSync(path.join(root, 'src/components/DigitalTwin3D.tsx'), 'utf8');
assert.match(twin, /getTimeRef\.current\?\.\(\)/, 'frame renderer reads high-resolution clock');
assert.match(twin, /\[sceneKey, height\]/, 'WebGL lifecycle independent from sim ticks and selection');
const clock = fs.readFileSync(path.join(root, 'src/hooks/useSimClock.ts'), 'utf8');
assert.match(clock, /now - lastUi >= 80/, 'UI renders throttled, not on every animation frame');
console.log('R25 replay smoke tests: PASS (four trucks, timing, dwell, OSRM shape, static wiring, TS syntax)');
