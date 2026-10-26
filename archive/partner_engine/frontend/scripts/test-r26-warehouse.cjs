// R26 deterministic single-warehouse tests; no browser/React/Three.js required.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const cp=require('node:child_process');
let ts;
try{ts=require('typescript');}catch{ts=require(path.join(cp.execFileSync('npm',['root','-g'],{encoding:'utf8'}).trim(),'typescript'));}
const root=path.resolve(__dirname,'..');
function read(p){return fs.readFileSync(path.join(root,p),'utf8');}
function loadPure(file){const {outputText,diagnostics}=ts.transpileModule(read(file),{fileName:file,compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022},reportDiagnostics:true});
  assert.deepEqual((diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error),[]);
  const mod={exports:{}};new Function('module','exports','require',outputText)(mod,mod.exports,()=>{throw Error('unexpected dependency');});return mod.exports;}
const core=loadPure('src/lib/warehouseTwin.ts');
const snap=require(path.join(root,'public/scenarios/single_warehouse_20_orders.json'));
assert.equal(snap.warehouses.length,1);
assert.equal(snap.vehicles.length,4);
for(const type of ['orders','vehicles','resources','operations','stock_lots'])assert.ok(snap[type].every(x=>x.warehouse_id==='wh_1'),`unified ${type}`);
for(const v of snap.vehicles)assert.equal(v.start_node_id,snap.warehouses[0].node_id);
const jobs=core.warehouseTwinData(snap,null,'showcase');
assert.equal(jobs.warehouseId,'wh_1');assert.equal(jobs.zones.length,8);assert.equal(jobs.racks.length,24);
assert.equal(new Set(jobs.jobs.map(j=>j.forkliftId)).size,3);
const {buildFourVehicleShowcase}=loadPure('src/lib/fleetDemo.ts');
const routes=buildFourVehicleShowcase(snap.orders,snap.vehicles,snap.warehouses);
assert.equal(routes.length,4);
assert.ok(routes.every(route=>route.stops[0].nodeId==='node_wh1'&&route.stops[route.stops.length-1].nodeId==='node_wh1'));
for(const route of routes){
 const assigned=route.stops.flatMap(stop=>stop.orderIds).map(id=>snap.orders.find(order=>order.order_id===id));
 assert.ok(assigned.every(order=>order.temperature_zone===route.zone),'no chilled/frozen mix');
}

assert.equal(jobs.jobs.length,9);assert.equal(jobs.warehouseWarning,null);
assert.ok(jobs.racks.some(r=>r.zone==='chilled')&&jobs.racks.some(r=>r.zone==='frozen'));
const task=jobs.jobs[0],start=task.startS,end=task.endS;const id=task.forkliftId;
const poses=[0.05,0.32,0.45,0.8,0.93].map(n=>core.forkliftPose(id,start+n*(end-start),jobs.jobs,jobs.racks));
assert.deepEqual(poses.map(x=>x.stage),['to_rack','pickup','to_dock','dropoff','returning']);
assert.equal(poses[2].carrying,true);assert.equal(poses[4].carrying,false);
const rewind=core.forkliftPose(id,0,jobs.jobs,jobs.racks);
assert.equal(rewind.stage,'to_rack');
const projected=core.warehouseTwinData(snap,{warehouse:{operations:[{operation_id:'job_1',resource_id:'res_dock1',start_s:5,end_s:200}],warehouse_handoffs:[]}},'plan');
assert.equal(projected.jobs.length,1);assert.equal(projected.jobs[0].source,'planned_timing');
assert.equal(core.warehouseTwinData(snap,null,'plan').jobs.length,0,'no fabricated solver output');
const old={...snap,warehouses:[...snap.warehouses,{warehouse_id:'wh_2',node_id:'node_wh2'}]};
assert.match(core.warehouseTwinData(old,null,'showcase').warehouseWarning,/旧快照/);
for(const file of ['src/components/WarehouseTwin3D.tsx','src/features/warehouseTwin/Page.tsx','src/components/DigitalTwin3D.tsx','src/App.tsx','src/features/dashboard/Page.tsx','src/features/postgres/Page.tsx','src/lib/warehouseTwin.ts']){
  const parse=ts.createSourceFile(file,read(file),ts.ScriptTarget.Latest,true,file.endsWith('tsx')?ts.ScriptKind.TSX:ts.ScriptKind.TS);
  assert.equal(parse.parseDiagnostics.length,0,`TypeScript parse: ${file}`);
}
assert.match(read('src/App.tsx'),/warehouseTwin: WarehouseTwinPage/);
assert.match(read('src/appContext.tsx'),/single_warehouse_20_orders\.json/);
assert.match(read('src/components/WarehouseTwin3D.tsx'),/raycaster\.intersectObjects/);
assert.match(read('src/components/WarehouseTwin3D.tsx'),/timeRef\.current\(\)/);
assert.match(read('src/components/WarehouseTwin3D.tsx'),/\[data,height\]/);
assert.match(read('src/features/dashboard/Page.tsx'),/navigate\('warehouseTwin'\)/);
assert.match(read('src/features/postgres/Page.tsx'),/r26_single_warehouse_ready/);
console.log('R26 tests PASS: one depot, 24 racks, 8 zones, 3 forklifts, task phases, plan projection, TS syntax, navigation');
