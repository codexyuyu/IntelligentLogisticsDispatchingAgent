import { expect, test } from '@playwright/test';

test('local Chinese UI imports, solves, observes and reloads the integrated pipeline', async ({ page }) => {
  test.setTimeout(120_000);
  await page.goto('/');
  await page.getByPlaceholder('输入 API Key').fill(process.env.E2E_TOKEN ?? 'dev-operator-token');
  await page.getByRole('button', { name: '验证并进入' }).click();
  await expect(page.getByText('县域冷链调度', { exact: true })).toBeVisible();
  await page.goto('/#/negotiation');
  await page.getByRole('button', { name: '加载合成测试样本' }).click();
  await expect(page.getByLabel('场景 JSON')).not.toHaveValue('');
  await page.getByRole('button', { name: '校验并导入' }).click();
  await expect(page.getByText('场景已校验并保存。')).toBeVisible();
  const response = page.waitForResponse(r => r.url().endsWith('/integration/runs') && r.request().method() === 'POST');
  await page.getByRole('button', { name: '计算并协商', exact: true }).click();
  const result = await (await response).json();
  expect(result.status).toBe('checked');
  expect(result.joint_validation.valid).toBe(true);
  expect(result.negotiation.result.status).toBe('confirmed');
  expect(result.observations.metrics.values).toHaveLength(14);
  expect(result.observations.handoffs.length).toBeGreaterThan(0);
  for (const handoff of result.observations.handoffs) {
    expect(handoff.pickup_start_s).toBeGreaterThanOrEqual(handoff.warehouse_ready_s);
  }
  await expect(page.getByText(`记录编号：${result.run_id}`)).toBeVisible();
  await page.getByRole('button', { name: '14 项指标', exact: true }).click();
  await expect(page.locator('tbody tr')).toHaveCount(14);
  await page.reload();
  await expect(page.getByText(`记录编号：${result.run_id}`)).toBeVisible();
  const revoke = page.waitForResponse(r => r.url().endsWith('/revoke'));
  await page.getByRole('button', { name: '撤销确认', exact: true }).first().click();
  const revoked = await (await revoke).json();
  expect(revoked.negotiation.result.status).toBe('revoked');
  expect(revoked.negotiation.result.digest).not.toBe(result.negotiation.result.digest);
  await page.reload();
  await expect(page.getByText(`摘要：${revoked.negotiation.result.digest}`)).toBeVisible();
});
