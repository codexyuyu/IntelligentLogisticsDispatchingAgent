import { expect, test } from '@playwright/test';

test('partner compatibility rejects anonymous access and keeps local-pg private', async ({ request }) => {
  expect((await request.get('/partner/assets/scenarios/single_warehouse_20_orders.json')).status()).toBe(401);
  expect((await request.get('/partner/local-pg/openapi.json', {
    headers: { Authorization: `Bearer ${process.env.E2E_TOKEN ?? 'dev-operator-token'}` },
  })).status()).toBe(404);
});

test('local dashboard runs partner planning, recovery and real simulation', async ({ page }) => {
  test.setTimeout(180_000);
  await page.goto('/');
  await page.getByPlaceholder('输入 API Key').fill(process.env.E2E_TOKEN ?? 'dev-operator-token');
  await page.getByRole('button', { name: '验证并进入' }).click();
  const planning = page.waitForResponse(r => r.url().endsWith('/partner/api/v1/planning-jobs'));
  const simulation = page.waitForResponse(r => r.url().endsWith('/partner/api/v1/simulations'), { timeout: 150_000 });
  await page.getByRole('button', { name: '开始演练', exact: true }).click();
  expect((await planning).status()).toBe(202);
  const accepted = await (await simulation).json();
  expect(accepted.simulation_id).toBeTruthy();
  await expect(page.getByText('案例已完成', { exact: true })).toBeVisible({ timeout: 150_000 });
  await expect(page.getByText('县域冷链调度', { exact: true })).toBeVisible();
});
