const fs=require('fs'),assert=require('assert'),path=require('path');
const root=path.resolve(__dirname,'..');
const page=fs.readFileSync(path.join(root,'src/features/closedLoop/Page.tsx'),'utf8');
const nav=fs.readFileSync(path.join(root,'src/App.tsx'),'utf8');
const css=fs.readFileSync(path.join(root,'src/styles.css'),'utf8');
for(const key of ['reconciliation?.status','全程计划配送','当前已回放配送','后续仍待回放','order_statuses.map','r28/diagnostics','跳至回放结尾','单仓迁移预检','当前进度条']){
 assert(page.includes(key),`R28 missing ${key}`);
}
assert(page.includes("delivered=occurred.filter"),'progress-dependent delivered count must remain clock-based');
assert(page.includes('totalPlanned=workflow?.reconciliation?.planned_delivery_order_count'),'full plan must come from backend reconciliation');
assert(page.includes('pendingPlanned=Math.max(0,totalPlanned-delivered)'),'pending replay deliveries must reconcile');
assert(page.includes("view==='warehouse'?"),'only render one WebGL scene at a time');
assert(nav.includes("key: 'closedLoop', title: '仓运闭环'"));
assert(css.includes('.r28-order-scroll') && css.includes('.r28-diagnostic-stages'));
console.log('R28 frontend order-accounting / workflow / read-only PG diagnostics wiring PASS');
