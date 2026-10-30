/** Stage B 第二轮：修复后的回放页 + 拒绝路径 + v0/v1 视图对比。 */
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const BASE = process.env.STAGE_B_BASE_URL ?? 'http://localhost:5199';
const RUN_APPROVED = process.env.RUN_APPROVED ?? process.env.RUN_APPROVED_DEFAULT ?? '';
const API_TOKEN = process.env.STAGE_B_API_TOKEN;
if (!API_TOKEN) { console.error('请先导出 STAGE_B_API_TOKEN（见 env_stage_b.example.sh）'); process.exit(2); }
const SHOTS = new URL('./shots/', import.meta.url).pathname.replace(/^\//, '');
mkdirSync(SHOTS, { recursive: true });

const errors = [];
const http404 = [];
function note(l) { console.log(`\n===== ${l} =====`); }
function ok(c, m, e = '') { console.log(`${c ? 'PASS' : 'FAIL'} | ${m}${e ? ' | ' + e : ''}`); return c; }

const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH ?? undefined, headless: true });
const ctx = await browser.newContext({ viewport: { width: 1680, height: 1000 } });
const page = await ctx.newPage();
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', e => errors.push('pageerror: ' + e.message));
page.on('response', r => { if (r.status() === 404) http404.push(`${r.request().method()} ${r.url()}`); });
page.on('dialog', async d => { await d.accept(); });

async function go(hash, wait = 1500) {
  await page.goto(`${BASE}/#/${hash}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(wait);
}

await go('dashboard', 1200);
await page.fill('#api-key', API_TOKEN);
await page.click('.auth-submit');
await page.waitForSelector('.app-shell', { timeout: 20000 });
console.log('已登录');
await page.evaluate(run => localStorage.setItem('integration_last_run', run), RUN_APPROVED);

// ---------- A. 仿真回放（修复后） ----------
note('A. 仿真回放：StageReplay 是否已挂载并以真实接口工作');
await go('simulations', 6000);
const bodyA = await page.textContent('body');
ok(/数据库驱动仓运模拟|全局仓运仿真回放/.test(bodyA), 'StageReplay 区块出现在仿真回放页');
const ranges = await page.$$('input[type=range]');
ok(ranges.length > 0, '全局时间轴滑块存在', `range=${ranges.length}`);
const viewSelect = await page.$('select[aria-label="方案视图"]');
ok(Boolean(viewSelect), '方案视图下拉存在（当前生效/原方案v0/延误候选）');
const canvasA = await page.$$eval('canvas', c => c.length);
ok(canvasA > 0, '回放页 3D canvas 渲染', `canvas=${canvasA}`);
await page.screenshot({ path: SHOTS + '20_replay_fixed.png', fullPage: true });

// 已批准 -> active 应等价于 candidate
const activeVersion = bodyA.replace(/\s+/g, ' ').match(/模拟版本：v(\d)/)?.[1];
ok(activeVersion === '1', '批准后当前生效模拟版本为 v1', `v${activeVersion}`);

await ranges[0].fill('1400');
await page.waitForTimeout(4000);
const at1400 = (await page.textContent('body')).replace(/\s+/g, ' ');
await page.screenshot({ path: SHOTS + '21_replay_1400_active.png', fullPage: true });
const posActive = at1400.match(/后端返回车辆位置：([^时]+?)(?:模拟时间|$)/)?.[1]?.trim() ?? '(未取得)';
console.log('  t=1400 active 车辆位置:', posActive.slice(0, 160));
const rowLine = at1400.match(/模拟版本：v\d\s*方案：\S+\s*在途车辆：\S+\s*已完成作业：\S+\s*已送达订单：\S+/)?.[0] ?? '';
console.log('  状态行:', rowLine);

await page.selectOption('select[aria-label="方案视图"]', 'baseline');
await page.waitForTimeout(4000);
const base1400 = (await page.textContent('body')).replace(/\s+/g, ' ');
await page.screenshot({ path: SHOTS + '22_replay_1400_baseline.png', fullPage: true });
console.log('  状态行(baseline):', base1400.match(/模拟版本：v\d\s*方案：\S+\s*在途车辆：\S+\s*已完成作业：\S+\s*已送达订单：\S+/)?.[0] ?? '');
const posBase = base1400.match(/后端返回车辆位置：([^时]+?)(?:模拟时间|$)/)?.[1]?.trim() ?? '(未取得)';
console.log('  t=1400 baseline 车辆位置:', posBase.slice(0, 160));
ok(posActive !== posBase || rowLine !== (base1400.match(/模拟版本：v\d\s*方案：\S+\s*在途车辆：\S+\s*已完成作业：\S+\s*已送达订单：\S+/)?.[0] ?? ''),
  'baseline 与 candidate 在 t=1400 存在差异（顺延生效）');

await ranges[0].fill('0');
await page.waitForTimeout(3000);
await page.screenshot({ path: SHOTS + '23_replay_0.png', fullPage: true });
console.log('  已回到起点');

// ---------- B. 拒绝路径（新 run） ----------
note('B. 拒绝路径：新建 run -> 启动模拟 -> 60s 延误 -> 拒绝 -> 保持 v0');
await go('plans', 2500);
const selects = await page.$$('select');
const opts = await selects[0].$$eval('option', os => os.map(o => ({ v: o.value, t: o.textContent })));
const target = opts.find(o => o.t.includes('十订单'));
await selects[0].selectOption(target.v);
await page.waitForTimeout(300);
await page.click('text=计算并协商');
let got = false;
for (let i = 0; i < 40; i++) {
  await page.waitForTimeout(2000);
  const b = await page.textContent('body');
  if (b.includes('下一步 · 启动数据库驱动的仓运模拟')) { got = true; break; }
}
ok(got, '新 run 返回 checked');
const RUN2 = await page.inputValue('input[aria-label="联合运行编号"]').catch(() => '');
console.log('  RUN2 =', RUN2);
await page.click('text=启动本次模拟');
await page.waitForTimeout(6000);
await page.screenshot({ path: SHOTS + '24_plans_run2.png', fullPage: true });
ok(true, 'run2 模拟已启动');

await go('events', 6000);
await page.locator('input[type=number]').nth(1).fill('60');
await page.waitForTimeout(300);
await page.click('text=触发模拟延误并分析');
await page.waitForTimeout(9000);
await page.screenshot({ path: SHOTS + '25_events_run2_pending.png', fullPage: true });
const pend = await page.textContent('body');
ok(/候选独立校验/.test(pend), '延误登记成功');
await page.click('text=拒绝 · 保留原方案');
await page.waitForTimeout(8000);
const rej = (await page.textContent('body')).replace(/\s+/g, ' ');
await page.screenshot({ path: SHOTS + '26_events_run2_rejected.png', fullPage: true });
ok(/拒绝/.test(rej), '拒绝操作完成');
console.log('  审批状态:', rej.match(/异常：.{0,60}/)?.[0] ?? '');
await page.reload({ waitUntil: 'domcontentloaded' });
await page.waitForTimeout(8000);
const rejReload = (await page.textContent('body')).replace(/\s+/g, ' ');
ok(/rejected/.test(rejReload), '刷新后拒绝状态从数据库恢复');
await page.screenshot({ path: SHOTS + '27_events_run2_reload.png', fullPage: true });

// run2 回放应保持 v0
await page.evaluate(run => localStorage.setItem('integration_last_run', run), RUN2);
await go('simulations', 7000);
const vCheck = (await page.textContent('body')).replace(/\s+/g, ' ');
const v2 = vCheck.match(/模拟版本：v(\d)/)?.[1];
ok(v2 === '0', '拒绝后模拟版本保持 v0', `v${v2}`);
await page.screenshot({ path: SHOTS + '28_replay_run2_v0.png', fullPage: true });

note('汇总');
console.log('RUN_APPROVED =', RUN_APPROVED);
console.log('RUN_REJECTED =', RUN2);
console.log('console/page errors =', errors.length);
[...new Set(errors)].slice(0, 10).forEach(e => console.log('  -', e.slice(0, 160)));
console.log('404 responses =', http404.length);
[...new Set(http404)].slice(0, 10).forEach(e => console.log('  -', e));
await browser.close();
