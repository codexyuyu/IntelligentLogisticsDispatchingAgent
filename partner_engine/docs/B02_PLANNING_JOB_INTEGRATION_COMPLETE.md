# B-02 -> Unified planning-jobs 集成完成

完成日期：2026-09-10

## 已接通链路

`POST /api/v1/scenarios/import`

→ 将不可变 `PlanningSnapshot` 放入 demo runtime

`POST /api/v1/planning-jobs`

→ B-01 `CpSatWarehouseScheduler` 生成 `WarehouseHandoff`
→ 按仓库拆分订单作用域
→ B-02 `OrToolsRoutingSolver`
→ `FixedTravelMatrixProvider`
→ 独立 `validate_transport`
→ 聚合 `RoutingResult`
→ 生成 `CandidatePlan`

`GET /api/v1/jobs/{job_id}`

→ 返回 planning job 状态与 `plan_id`

`GET /api/v1/plans/{plan_id}`

→ 返回已验证 `CandidatePlan`

## 多仓库说明

B-02 求解器当前保持“单仓库一次求解”的边界。统一 planning job 在应用层按 `warehouse_id` 分组，分别调用 RoutingModel，再把各仓库结果聚合为一个 snapshot-scoped `RoutingResult`。不会把多个仓库伪装成一次单模型求解。

## 当前存储边界

本次接入使用 `DemoRuntime` 内存存储，用于开发和验收。没有修改数据库，也没有把 HTTP 请求当作生产队列。后续由 AC 的 persistence/worker 实现替换该 demo runtime。

## 运行

进入 `backend`：

```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload --port 8000
```

打开 `http://127.0.0.1:8000/docs`。

Swagger 操作顺序：

1. `POST /api/v1/scenarios/import`，粘贴 `data/scenarios/two_warehouses_20_orders.json` 的内容作为 `snapshot`，例如 `scenario_id=scn_demo`。
2. `POST /api/v1/planning-jobs`，使用 `contracts/examples/dispatch_request.json` 的请求体。
3. 取返回的 `job_id` 调 `GET /api/v1/jobs/{job_id}`。
4. 成功后，用返回的 `plan_id` 调 `GET /api/v1/plans/{plan_id}`。

首次安装时，`backend/requirements.txt` 已包含 `ortools==9.15.6755`，不再需要额外安装 `requirements-optional.txt` 才能运行 B-01/B-02。
