/** Stage B 真实页面验收：只用隔离后端（vite 5199 -> API 8100 -> PG 5434）。 */
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const BASE = process.env.STAGE_B_BASE_URL ?? 'http://localhost:5199';
const API_TOKEN = process.env.STAGE_B_API_TOKEN;
if (!API_TOKEN) { console.error('请先导出 STAGE_B_API_TOKEN（见 env_stage_b.example.sh）'); process.exit(2); }
const SHOTS = new URL('./shots/', import.meta.url).pathname.replace(/^\//, '');
mkdirSync(SHOTS, { recursive: true });

const errors = [];
const failedApi = [];

function note(label) { console.log(`\n===== ${label} =====`); }
function ok(cond, msg, extra = '') { console.log(`${cond ? 'PASS' : 'FAIL'} | ${msg}${extra ? ' | ' + extra : ''}`); return cond; }

const browser = await chromium.launch({
  executablePath: process.env.CHROME_PATH ?? undefined,
  headless: true,
});
const ctx = await browser.newContext({ viewport: { width: 1680, height: 1000 }, acceptDownloads: true });
const page = await ctx.newPage();

page.on('console', m => { if (m.type() === 'error') errors.push(`console: ${m.text()}`); });
page.on('pageerror', e => errors.push(`pageerror: ${e.message}`));
page.on('response', r => {
  const u = r.url();
  if (u.includes('/api/') && r.status() >= 400) failedApi.push(`${r.status()} ${r.request().method()} ${u.replace('http://127.0.0.1:8100', '')}`);
});
page.on('dialog', async d => { console.log(`  [dialog] ${d.type()}: ${d.message().slice(0, 60)}`); await d.accept(); });

async function go(hash) {
  await page.goto(`${BASE}/#/${hash}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1200);
}

// ---------- 1. 登录 ----------
note('1. 登录（真实 token 校验，走 8100 隔离后端）');
await go('dashboard');
await page.fill('#api-key', API_TOKEN);
await page.click('.auth-submit');
await page.waitForSelector('.app-shell', { timeout: 20000 });
ok(true, '登录后进入调度台 Shell');
await page.waitForTimeout(2500);
const conn = await page.textContent('.connection-line').catch(() => '');
ok(/后端已连接/.test(conn ?? ''), '侧栏显示后端已连接', conn?.trim().slice(0, 40));

// ---------- 2. 联合调度 ----------
note('2. 联合调度：计算并协商 -> checked -> 启动数据库驱动模拟');
await go('plans');
await page.waitForTimeout(2000);
const scenarioOptions = await page.$$eval('select option', els => els.map(e => e.textContent.trim()).filter(t => t.includes('十订单')));
ok(scenarioOptions.length > 0, '场景下拉可见 coldchain_chain_10', scenarioOptions[0]?.slice(0, 40));

const selects = await page.$$('select');
// 第一个 select 为「已导入场景」
const opts = await selects[0].$$eval('option', os => os.map(o => ({ v: o.value, t: o.textContent })));
const target = opts.find(o => o.t.includes('十订单'));
ok(Boolean(target), '定位目标场景 option', target?.t?.slice(0, 30));
await selects[0].selectOption(target.v);
await page.waitForTimeout(400);

await page.click('text=计算并协商');
let checked = false;
for (let i = 0; i < 40; i++) {
  await page.waitForTimeout(2000);
  const body = await page.textContent('body');
  if (body.includes('下一步 · 启动数据库驱动的仓运模拟')) { checked = true; break; }
}
ok(checked, '联合调度返回 checked 并出现「下一步 · 启动数据库驱动的仓运模拟」');
await page.screenshot({ path: SHOTS + '01_plans_checked.png', fullPage: true });

const runIdFromUi = await page.inputValue('input[aria-label="联合运行编号"]').catch(() => '');
ok(/^[0-9a-f-]{36}$/i.test(runIdFromUi), 'RunBar 自动获得 run 编号（无需用户复制）', runIdFromUi);

await page.click('text=启动本次模拟');
await page.waitForTimeout(6000);
const simBanner = await page.textContent('.stageb-run-bar').catch(() => '');
ok(/数据库模拟已载入/.test(simBanner ?? ''), '模拟已建立并载入', (simBanner ?? '').replace(/\s+/g, ' ').slice(0, 120));
await page.screenshot({ path: SHOTS + '02_plans_simulation.png', fullPage: true });

const storedRun = await page.evaluate(() => localStorage.getItem('integration_last_run'));
ok(storedRun === runIdFromUi, 'integration_last_run 已持久化，供跨页传递', storedRun);
const RUN = runIdFromUi;

// ---------- 3. 仓储运营 ----------
note('3. 仓储运营：联合排程甘特图(30工序) + 实际库存台账');
await go('warehouseOps');
await page.waitForTimeout(2500);
await page.click('text=联合排程甘特图');
await page.waitForTimeout(4000);
const ganttText = await page.textContent('body');
await page.screenshot({ path: SHOTS + '03_warehouse_gantt.png', fullPage: true });
const hasGantt = /甘特|工序|收货|分拣|装车/.test(ganttText);
ok(hasGantt, '甘特图区域渲染出工序内容');
await page.click('text=实际库存台账');
await page.waitForTimeout(4000);
const ledgerText = await page.textContent('body');
await page.screenshot({ path: SHOTS + '04_warehouse_ledger.png', fullPage: true });
ok(/台账|库存/.test(ledgerText), '实际库存台账视图可切换渲染');

// ---------- 4. 运输计划 3D ----------
note('4. 运输计划：3D 持久化路线 + state-at 拖动');
await go('vehicles');
await page.waitForTimeout(5000);
const canvasCount = await page.$$eval('canvas', cs => cs.length);
ok(canvasCount > 0, 'DigitalTwin3D canvas 已渲染', `canvas=${canvasCount}`);
const vehicleText = await page.textContent('body');
await page.screenshot({ path: SHOTS + '05_transport_3d.png', fullPage: true });
ok(/路线|车辆|route|vehicle/i.test(vehicleText), '运输计划页出现持久化路线/车辆信息');

// ---------- 5. 异常处置 ----------
note('5. 异常处置：60s 延误 -> 影响分析 -> 人工批准 (v0->v1)');
await go('events');
await page.waitForTimeout(5000);
await page.screenshot({ path: SHOTS + '06_events_before.png', fullPage: true });
const incidentBefore = await page.textContent('body');
console.log('  页面摘要:', incidentBefore.replace(/\s+/g, ' ').match(/联合运行编号.{0,160}/)?.[0] ?? '(未显示 run bar)');

const delayInput = page.locator('input[type=number]').nth(1);
await delayInput.fill('60');
await page.waitForTimeout(300);
await page.click('text=触发模拟延误并分析');
await page.waitForTimeout(9000);
const afterInject = await page.textContent('body');
await page.screenshot({ path: SHOTS + '07_events_delayed.png', fullPage: true });
ok(/候选独立校验/.test(afterInject), '延误已登记并展示候选校验结论');
const impactLine = afterInject.replace(/\s+/g, ' ').match(/受影响订单：.{0,80}/)?.[0] ?? '';
ok(/\d/.test(impactLine), '显示受影响订单与顺延', impactLine);

await page.click('text=人工批准模拟方案');
await page.waitForTimeout(8000);
const afterApprove = await page.textContent('body');
await page.screenshot({ path: SHOTS + '08_events_approved.png', fullPage: true });
ok(/已批准/.test(afterApprove), '批准成功');
const statusLine = afterApprove.replace(/\s+/g, ' ').match(/异常：.{0,90}/)?.[0] ?? '';
console.log('  审批状态:', statusLine);

// 刷新后恢复
await page.reload({ waitUntil: 'domcontentloaded' });
await page.waitForTimeout(8000);
const afterReload = await page.textContent('body');
ok(/已批准|approved/.test(afterReload), '刷新页面后审批记录可从数据库恢复');
await page.screenshot({ path: SHOTS + '09_events_reloaded.png', fullPage: true });

// ---------- 6. 仿真回放 ----------
note('6. 仿真回放：统一时钟 / 车辆位置 / 事件 / 原方案-候选方案切换');
await go('simulations');
await page.waitForTimeout(6000);
await page.screenshot({ path: SHOTS + '10_replay.png', fullPage: true });
const replayBefore = await page.textContent('body');
console.log('  回放页摘要:', replayBefore.replace(/\s+/g, ' ').slice(0, 300));

// 拖动时间轴（range input）
const ranges = await page.$$('input[type=range]');
console.log(`  发现 range 滑块 ${ranges.length} 个`);
if (ranges.length) {
  await ranges[0].fill('1200');
  await page.waitForTimeout(4000);
  await page.screenshot({ path: SHOTS + '11_replay_t1200.png', fullPage: true });
  const t = await page.textContent('body');
  ok(t.length > 0, '时间拖动后页面仍有内容');
  await ranges[0].fill('0');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: SHOTS + '12_replay_t0.png', fullPage: true });
  console.log('  已回到起点重播');
}

note('结果汇总');
console.log('RUN_ID =', RUN);
console.log('console/page errors =', errors.length);
errors.slice(0, 20).forEach(e => console.log('  -', e));
console.log('failed API (>=400) =', failedApi.length);
[...new Set(failedApi)].slice(0, 20).forEach(e => console.log('  -', e));

await browser.close();
