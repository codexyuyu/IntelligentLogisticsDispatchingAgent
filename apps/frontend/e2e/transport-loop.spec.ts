import { expect, test, type Page, type Response } from "@playwright/test";
import { writeFile } from "node:fs/promises";

type Captured = {
  method: string;
  path: string;
  status: number;
  body: unknown;
};

const TOKEN = process.env.E2E_TOKEN ?? "dev-operator-token";

async function capture(page: Page, captured: Captured[]) {
  page.on("response", async (response: Response) => {
    const url = response.url();
    if (!url.includes("/api/v1/")) return;
    const request = response.request();
    if (!["GET", "POST"].includes(request.method())) return;
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      body = null;
    }
    captured.push({
      method: request.method(),
      path: url.replace(/^https?:\/\/[^/]+/, ""),
      status: response.status(),
      body,
    });
  });
}

function find(captured: Captured[], method: string, suffix: string) {
  return captured.find((item) =>
    item.method === method && item.path.endsWith(suffix),
  );
}

test("transport dispatch browser loop commits and survives refresh", async ({ page }, testInfo) => {
  test.setTimeout(120_000);
  const captured: Captured[] = [];
  const operations: string[] = [];
  await capture(page, captured);

  operations.push("open workbench");
  await page.goto("/", { waitUntil: "networkidle" });
  await page.evaluate(() => localStorage.clear());
  await page.reload({ waitUntil: "networkidle" });

  operations.push("login");
  await page.getByPlaceholder("Bearer token").first().fill(TOKEN);
  await page.getByRole("button", { name: "sign in" }).click();
  await page.getByRole("link", { name: "Transport optimization" }).click();

  operations.push("read database orders, vehicles, warehouses and matrices");
  await expect(page.getByText(/已从数据库读取 \d+ 个订单/)).toBeVisible();
  await expect(page.getByLabel("订单（数据库）")).toBeVisible();
  await expect(page.getByLabel("车辆（数据库）")).toBeVisible();

  operations.push("submit transport solve");
  await page.getByRole("button", { name: "提交运输求解" }).click();
  await expect(page.getByText("候选与提交")).toBeVisible({ timeout: 90_000 });
  await expect(page.getByText(/校验：\s*passed/)).toBeVisible();

  operations.push("confirm candidate");
  await expect(page.getByText(/valid true/)).toBeVisible();
  await page.getByRole("checkbox").check();
  operations.push("commit version");
  await page.getByRole("button", { name: "确认提交版本" }).click();
  await expect(page.getByText("已提交并从数据库回读")).toBeVisible({ timeout: 30_000 });

  const schedule = find(captured, "POST", "/schedules");
  const job = find(captured, "POST", "/optimizations/transport");
  const candidate = find(captured, "POST", "/candidates/from-job");
  const commit = find(captured, "POST", "/versions/commit");
  const current = find(captured, "GET", "/versions/current");
  expect(schedule?.body, "schedule response").toBeTruthy();
  expect(job?.body, "job response").toBeTruthy();
  expect(candidate?.body, "candidate response").toBeTruthy();
  expect(commit?.body, "commit response").toBeTruthy();
  expect(current?.body, "current version response").toBeTruthy();

  const scheduleId = (schedule?.body as { schedule_id: string }).schedule_id;
  const jobId = (job?.body as { job_id: string }).job_id;
  const candidateId = (candidate?.body as { candidate_id: string }).candidate_id;
  const versionId = (commit?.body as { version_id: string }).version_id;
  const currentVersionId = (current?.body as { version: { version_id: string } }).version.version_id;
  expect(currentVersionId, "database readback after commit").toBe(versionId);

  const committedText = await page.locator("main").innerText();
  expect(committedText).toContain(versionId);
  expect(committedText).toContain(scheduleId);

  operations.push("refresh and read same current version");
  await page.reload({ waitUntil: "networkidle" });
  await expect(page.getByText("已提交并从数据库回读")).toBeVisible({ timeout: 20_000 });
  const refreshedText = await page.locator("main").innerText();
  expect(refreshedText).toContain(versionId);
  expect(refreshedText).toContain("当前版本 v1");

  const currentReads = captured.filter((item) =>
    item.method === "GET" && item.path.endsWith("/versions/current"));
  const afterRefresh = currentReads[currentReads.length - 1];
  const afterRefreshBody = afterRefresh?.body as { version: { version_id: string }; tasks: unknown[] } | undefined;
  expect(afterRefreshBody?.version.version_id).toBe(versionId);
  expect(afterRefreshBody?.tasks.length).toBeGreaterThan(0);

  await page.screenshot({ path: testInfo.outputPath("transport-loop.png"), fullPage: true });
  const artifact = {
    token_used: TOKEN === "dev-operator-token" ? "development token" : "custom token",
    operations,
    schedule_id: scheduleId,
    job_id: jobId,
    candidate_id: candidateId,
    version_id: versionId,
    current_version_id: currentVersionId,
    after_refresh_version_id: afterRefreshBody?.version.version_id,
    task_count: afterRefreshBody?.tasks.length,
    requests: captured,
  };
  await writeFile(testInfo.outputPath("transport-loop.json"), JSON.stringify(artifact, null, 2));
  await testInfo.attach("transport-loop.json", {
    path: testInfo.outputPath("transport-loop.json"),
    contentType: "application/json",
  });
});
