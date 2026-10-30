# Stage A 后端闭环交接（基于 fd1f241）

本次变更只覆盖后端、增量数据库迁移及测试。前端仍由阶段 B 接入现有六个页面；没有创建新的前端入口。

## 已实现

1. 基于 **PostgreSQL 已存储的 `integration_scenarios` 和 checked `integration_runs`**，在 S4 七项对账均通过后，创建唯一的模拟运行记录。10 单×3 工序由既有 S2/S3/S4 数据提供，不重新造一套仓储模型。
2. 从 checked 运输路线、停靠点、行车矩阵及时间线生成确定性的 `segments`，落入 `integration_simulations.payload`。它是示意路线的时间插值输入，不是 GPS／道路导航，也不是 SimPy 的实测事件。
3. 通过模拟运行 ID 串联运输中车辆、延误事件、变更候选及历史回放。用合法 `transport_delay` + `transport_task` 事件写入既有 `events` 表，来源固定为 `integration-simulation`。
4. 中途延误生成有物理连续性的 **原位置等待→剩余行程顺延** 候选，冻结异常时刻之前的轨迹与事件；验证剩余节点硬时间窗、车辆可用窗和总体仿真时域。现有 S1 局部 OR-Tools 求解器也被调用以形成诊断，但其以仓库为起点的局部线路 **不会直接接到行驶中的车上**（那会导致瞬移）。
5. 每次模拟暂限 **一个延误事件**，人工操作员可批准或拒绝。批准切换模拟版本 v0→v1，拒绝保持 v0；决策加行版本检查，重复同向审批幂等。无自动提交真实 `schedule_versions`、实际派车、实际库存或 S3 实体作业变更。
6. `state-at` 返回同一时刻的仓储作业、送达状态、车辆路线进度与异常记录，可选择 `baseline`、`candidate` 或 `active`。模拟状态与既有 S4 `planned_validated` 独立，结果明确标记 `simulated_from_planned` / `simulated_delay_projection`。

## 新增 HTTP API

路径均加现有前缀 `/api/v1`，基于已完成的 `run_id`，使用原有认证和 scope 隔离。

| 方法 | 路径 | 权限 / 用途 |
| --- | --- | --- |
| POST | `/integration/runs/{run_id}/simulation` | operator，幂等建立模拟基线 |
| GET | `/integration/runs/{run_id}/simulation` | actor，读取基线线路、事件、审批及当前版本 |
| POST | `/integration/runs/{run_id}/simulation/incidents` | operator，生成合法 `transport_delay`，并计算候选 |
| POST | `/integration/runs/{run_id}/simulation/incidents/{incident_id}/approve` | operator，人工批准模拟版本 |
| POST | `/integration/runs/{run_id}/simulation/incidents/{incident_id}/reject` | operator，人工拒绝，原方案保持不变 |
| GET | `/integration/runs/{run_id}/simulation/state-at?time_s=123&view=active` | actor，同步仓储/车辆/事件快照；`view=baseline/candidate/active` |

创建事件示例（先从 GET simulation 的事件获取某车发车时刻，选择其发车后的在途时间）：

```json
{
  "vehicle_id": "<本次 checked 方案中的 vehicle_id>",
  "time_s": 301,
  "delay_s": 1,
  "source_event_id": "demo-delay-01",
  "reason": "途中模拟车辆延误",
  "budget_ms": 1000
}
```

注：`301` 只是接口格式示例，必须以实际 checked 方案中的在途时间为准，不保证该时刻对任意场景有效。批准/拒绝请求为 `{ "expected_row_version": 0 }`；若候选有硬约束违反，则 `proposal_valid=false`，禁止批准，可拒绝。记录再次读取时会显示状态和已批准的模拟版本。

## 数据库迁移与隔离

新增唯一迁移 `0012_integration_simulation`：

- `integration_simulations`：每个 checked run 一份不可变基线（含运行来源、路线段、计划事件）。
- `integration_simulation_incidents`：每份模拟最多一条异常，保存有效性、S1 建议、候选轨迹及人工状态。
- 所有新数据按 `scope_id` 查询；设置 run / incident 幂等唯一键；未获同意不会动演示数据库。

**严禁把当前压缩包的迁移脚本直接作用到 5433。** 需在授权的隔离 PostgreSQL（既定 5434）备份／核对库名、连接地址、migration head 后再执行 `uv run alembic upgrade head`。

## 验证方式

```bash
uv run ruff check apps/backend/src/logistics_backend/application/integration_simulation.py apps/backend/src/logistics_backend/application/integration_simulation_tracks.py apps/backend/src/logistics_backend/api/integration.py tests/unit/test_integration_simulation_tracks.py tests/integration/test_integration_simulation.py
uv run pytest --import-mode=importlib -q tests/unit/test_integration_simulation_tracks.py
uv run pytest --import-mode=importlib -q tests/unit tests/integration/test_s4_timeline.py tests/integration/test_coldchain_chain_10.py -m 'not requires_postgres'
```

在隔离 5434 配好 `TEST_DATABASE_URL` 且 **已执行 0012 迁移** 后，额外运行：

```bash
uv run pytest --import-mode=importlib -q tests/integration/test_integration_simulation.py
```

当前执行环境无 `TEST_DATABASE_URL`，未连接 PostgreSQL，故本轮不能声称真实数据库迁移和 HTTP 持久化验收已通过；数据库用例已随代码提供，待隔离环境执行。

## 阶段 B 需要的接入和暂不完成项

- 复用 `DigitalTwin3D`、S5 `TimelinePage`、仓储运营和现有异常处置界面，统一使用 `run_id`；轨迹 `segments` 包含 `from_node_id`、`to_node_id`、`start_s`、`end_s`、`start_fraction`、`end_fraction`，前端用既有 `layoutNodes` 显示，不要将它宣传为真实道路/GPS。
- 当前仅支持一次模拟中的单个延误、持有并顺延策略。真正从**行驶中位置**求解新的道路后缀（而非 S1 仓库起点求解）及多次连续异常，仍属后续优化；不应把 S1 诊断线路直接展示为已批准的物理轨迹。
- 数据驱动指读取 PostgreSQL 存储的已导入场景和 checked 运行证据；尚未做企业真实业务表自动抽取适配，也没有触发独立的 SimPy Job。阶段 B 必须如实区分“计划”“模拟”“实际作业”。
- 当前 `generated.ts` 缺少 S3/S4 类型、`contracts:generate` 工具链损坏，此次没有改动；阶段 B 接入新 API 时应一并补齐。
