/** Lightweight tests of B-06 quick/standard profile and actual Planning Job request budget. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const root = path.join(__dirname, '..');
const snapshot = JSON.parse(fs.readFileSync(path.join(root,'..','data','scenarios','two_warehouses_20_orders.json'), 'utf8'));
function compile(rel, requireMap, fetchMock) {
  const source = fs.readFileSync(path.join(root,rel),'utf8');
  const output = ts.transpileModule(source, {fileName:rel, reportDiagnostics:true,
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}});
  assert.equal(output.diagnostics.length,0,`Transpile diagnostics in ${rel}`);
  const module = {exports:{}};
  vm.runInNewContext(output.outputText, {
    module, exports:module.exports, require:n => { if(n in requireMap) return requireMap[n]; throw new Error(`Unmocked import: ${n}`); },
    performance, fetch:fetchMock, console, Date, Math, JSON, Map, Set, Number, String, Array, Error,
  }, {filename:rel});
  return module.exports;
}
const core = compile('src/lib/benchmark.ts',{},async()=>{});
const basic = core.buildRuleBaseline(snapshot);
const requests = [];
let failQuick = false;
let count = 0;
const fakeHttp = {
  postApi: async (path,body) => {
    requests.push({path,body});
    if (path.includes('/scenarios/')) return {snapshot_id:body.snapshot.snapshot_id,version:1};
    if (path.includes('/planning-jobs')) return {job_id:`job-${++count}`,status:'accepted'};
    throw new Error(`unexpected request: ${path}`);
  },
  pollJob: async () => failQuick ? {status:'failed',error_code:'routing_solver_failed:wh_1:ROUTING_NO_SOLUTION'}
    : {status:'succeeded',plan_id:'mock-plan'},
};
const fakeMetrics = {...core, optimizedMetrics:()=>basic,buildRuleBaseline:()=>basic};
const plan = {
  plan_id:'mock-plan',validation:{status:'passed'},routing:{metadata:{solve_ms:100}}, warehouse:{metadata:{solve_ms:50}},
};
const batch = compile('src/lib/batchBenchmark.ts', {'./http':fakeHttp,'./benchmark':fakeMetrics},
  async() => ({ok:true,json:async()=>({plan})}));
(async()=>{
  assert.equal(batch.budgetForScale(20,'quick'),8000);
  assert.equal(batch.budgetForScale(50,'quick'),12000);
  assert.equal(batch.budgetForScale(100,'quick'),18000);
  for(const size of [20,50,100]) assert.equal(batch.budgetForScale(size,'standard'),60000);
  assert.throws(()=>batch.budgetForScale(10,'quick'));
  // Existing synchronous back end finishes before the first GET poll. No 1s artificial delay.
  const syncHttp = compile('src/lib/http.ts', {'../client/api': {api: {GET: async()=>({data:{status:'succeeded',plan_id:'p'}})}}}, async()=>{});
  const pollStart = performance.now();
  const syncJob = await syncHttp.pollJob('job-synchronous',undefined,5);
  assert.equal(syncJob.status,'succeeded');
  assert.ok(performance.now() - pollStart < 400, 'First poll must not incur a one-second sleep');
  const checkpoints=[];
  const quick = await batch.runBatchBenchmark(snapshot,[20,50,100],[17],undefined,'quick', r=>checkpoints.push([r.size,r.seed]));
  assert.equal(checkpoints.length,3,'Each finished run emits a checkpoint');
  assert.deepEqual(requests.filter(r=>r.path.includes('planning-jobs')).map(r=>r.body.budget_ms),[8000,12000,18000]);
  assert.ok(quick.every(s=>s.profile==='quick' && s.runs[0].profile==='quick'));
  assert.ok(quick.every(s=>s.runs[0].status==='succeeded' && s.runs[0].validationStatus==='passed'));
  assert.ok(quick.every(s=>s.runs[0].wallMs != null));
  const standard = await batch.runBatchBenchmark(snapshot,[50],[17],undefined,'standard');
  assert.equal(requests.filter(r=>r.path.includes('planning-jobs')).at(-1).body.budget_ms,60000);
  assert.equal(standard[0].profile,'standard');
  const ids = requests.filter(r=>r.path.includes('scenarios/import')).map(r=>r.body.scenario_id);
  assert.notEqual(ids[1],ids[3], 'quick and standard use distinct scenario IDs');
  failQuick = true;
  const unsuccessful = await batch.runBatchBenchmark(snapshot,[100],[42],undefined,'quick');
  const failure = unsuccessful[0].runs[0];
  assert.equal(failure.status,'failed');
  assert.equal(failure.errorCode,'QUICK_BUDGET_NOT_SOLVED');
  assert.match(failure.errorReason,/不能判定不可行/);
  assert.match(failure.error,/ROUTING_NO_SOLUTION/);
  console.log('R16 speed tests: PASS (quick budgets, standard budget, profile separation, short-search diagnosis)');
})().catch(e=>{console.error(e);process.exitCode=1;});
