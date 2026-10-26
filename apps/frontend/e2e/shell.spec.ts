import { expect, test } from '@playwright/test';

// UI-only failure-path checks. No API responses, database rows or solves are faked.
test('offline session keeps the Chinese shell and never reports imported data', async ({ page }, info) => {
  await page.addInitScript(() => localStorage.setItem('dsh_token', 'offline-ui-test'));
  await page.route('**/api/v1/**', route => route.abort('connectionrefused'));
  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.goto('/');
  await expect(page.getByText('县域冷链调度', { exact: true })).toBeVisible();
  await expect(page.getByText('后端未连接', { exact: true })).toBeVisible();
  await expect(page.getByText('Dispatch Workbench', { exact: true })).toHaveCount(0);
  await expect(page.getByText('数据已同步', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: '开始演练', exact: true })).toBeDisabled();
  await page.screenshot({ path: info.outputPath('chinese-dashboard-offline.png'), fullPage: true });
  await page.getByRole('button', { name: '运输计划', exact: true }).click();
  await expect(page).toHaveURL(/#\/vehicles$/);
  await page.reload();
  await expect(page.getByRole('heading', { name: '运输计划', exact: true })).toBeVisible();
  await expect(page.getByText('已提交并从数据库回读', { exact: true })).toHaveCount(0);
});

test('unreachable backend does not accept a login', async ({ page }) => {
  await page.route('**/api/v1/**', route => route.abort('connectionrefused'));
  await page.goto('/');
  await page.getByPlaceholder('输入 API Key').fill('offline-ui-test');
  await page.getByRole('button', { name: '验证并进入' }).click();
  await expect(page.locator('.auth-error')).toBeVisible();
  await expect(page.getByRole('navigation', { name: '主导航' })).toHaveCount(0);
  expect(await page.evaluate(() => localStorage.getItem('dsh_token'))).toBeNull();
});
