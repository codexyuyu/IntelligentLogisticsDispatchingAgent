const fs=require('fs'),assert=require('assert'),path=require('path');
const root=path.resolve(__dirname,'..');
const page=fs.readFileSync(path.join(root,'src/features/closedLoop/Page.tsx'),'utf8');
const api=fs.readFileSync(path.join(root,'src/App.tsx'),'utf8');
const twin=fs.readFileSync(path.join(root,'src/lib/warehouseTwin.ts'),'utf8');
const required=[
  ['/r27/workflow','dedicated read-only R27 endpoint'],
  ['/r28/diagnostics','R28 enhanced strict PG readiness and warehouse blockers'],
  ['WarehouseTwin3D','warehouse 3D replay'],
  ['DigitalTwin3D','road fleet 3D replay'],
  ['useSimClock(horizon,false)','shared clock'],
  ['loading_ready','loading events'],
  ['vehicle_departure','vehicle events'],
  ['acknowledge_dry_run_only:true','explicit simulation acknowledgement'],
];
for(const [text,reason] of required)assert(page.includes(text),`missing ${reason}`);
assert(api.includes("key: 'closedLoop'"));
assert(api.includes('closedLoop: ClosedLoopPage'));
assert(twin.includes('sourceOperations.get(op.operation_id)'), '3D tasks must show actual scheduled order mapping');
assert(page.includes("view==='warehouse'?") && page.includes('onClick={()=>setView(\'transport\')}'), 'one WebGL scene at a time');
assert(page.includes('单仓演示') && page.includes('PostgreSQL 核验'));
console.log('R27 UI wiring & shared clock assertions PASS');
