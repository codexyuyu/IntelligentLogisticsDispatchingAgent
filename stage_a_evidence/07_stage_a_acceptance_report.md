# 阶段一后端闭环实库验收报告

**验收对象**：县域农产品冷链调度智能体 · Stage A（模拟 + 延误 + 人工审批 + 回放）
**验收日期**：2026-10-30
**验收结论**：**通过，建议进入阶段二**

---

## 1. 基线与代码

| 项 | 值 |
| --- | --- |
| 仓库 | `codexyuyu/IntelligentLogisticsDispatchingAgent` |
| 分支 | `feat/vehicle-delay-reschedule` |
| 基线 HEAD | `fd1f241`（本地 = 远端，工作区提交前干净 0 项） |
| 测试副本 | `D:\1aaaqianduan\partner\_stage_a_test`（独立 clone，`core.autocrlf=false`，未改动原工作区） |
| 迁移目标 | `0012_integration_simulation` |

原始工作区 `_demo_p0` 未被覆盖、未被 reset、未被强切分支。overlay 只施加到独立副本。

### 1.1 overlay 修改文件清单（9 个）

| 状态 | 文件 | 行数 |
| --- | --- | --- |
| 修改 | `apps/backend/src/logistics_backend/api/integration.py` | 6535 B |
| 修改 | `apps/backend/src/logistics_backend/bootstrap.py` | 12254 B |
| 修改 | `apps/backend/src/logistics_backend/persistence/integration_models.py` | 5266 B |
| 新增 | `apps/backend/src/logistics_backend/application/integration_simulation.py` | 17537 B |
| 新增 | `apps/backend/src/logistics_backend/application/integration_simulation_tracks.py` | 10483 B |
| 新增 | `apps/backend/migrations/versions/0012_integration_simulation.py` | 2307 B |
| 新增 | `tests/integration/test_integration_simulation.py` | 5659 B |
| 新增 | `tests/unit/test_integration_simulation_tracks.py` | 7821 B |
| 新增 | `docs/implementation/STAGE_A_SIMULATION_HANDOFF_20261030.md` | 6192 B |

额外：本报告随附的 `test_stage_a_acceptance_14.py` 是**验收取证脚本**（untracked，未提交），用于逐条验证第六节的 14 项要求，不属于产品代码。

**未执行任何 commit / push / merge / PR。**

---

## 2. 测试环境

| 项 | 值 |
| --- | --- |
| Python | 3.12.10（`.venv`，满足 `requires-python >=3.12,<3.13`） |
| uv | 0.13.6 |
| 数据库 | `127.0.0.1:5434 / logistics_stage_a_test`（Docker 容器 `cc_test_pg`） |
| 凭据 | 仅通过进程环境变量传递，未出现在本报告与任何日志中 |
| 迁移/测试指向 | `DATABASE_URL` == `TEST_DATABASE_URL`（同一隔离库） |

### 2.1 数据库隔离核对

| 检查项 | 结果 |
| --- | --- |
| 5433 演示库容器 `coldchain_demo_20261029-db-1` | `exited`，StartedAt `2026-10-29T18:01:35Z`、FinishedAt `2026-10-30T05:59:07Z` —— **本轮全程未启动** |
| 5433 端口监听 | 无监听 |
| 5434 容器 `cc_test_pg` | `running`（本轮启动） |
| 新建库 | `logistics_stage_a_test`（全新，迁移前 0 张表） |
| 既存库 `logistics_test` | **未清空、未迁移**（保持原状） |
| 是否出现 5433 连接参数 | 0 处 |

⚠️ 说明：容器内 `current_setting('port')` 返回 `5432` 是 Docker 端口映射的固有表现（主机 5434 → 容器 5432），实际连接入口确认是 `127.0.0.1:5434`。

---

## 3. Alembic 迁移

| 阶段 | 版本 |
| --- | --- |
| 迁移前 | 空（新库无 `alembic_version`） |
| head | `0012_integration_simulation` |
| 迁移后 | `0012_integration_simulation (head)` |

- 命令：`uv run alembic upgrade head`（退出码 0）
- `public` 表总数：**45**
- 原有表和业务数据：本库为新建库，迁移不涉及删除；既存库 `logistics_test` 未参与

### 3.1 新增表结构

**`integration_simulations`**：`id, scope_id, run_id, created_at, created_by, payload`
**`integration_simulation_incidents`**：`id, scope_id, simulation_id, event_id, status, row_version, created_at, updated_at, created_by, payload`

### 3.2 约束与索引

| 类型 | 内容 |
| --- | --- |
| 主键 | `integration_simulations_pkey`、`integration_simulation_incidents_pkey` |
| 外键 | `integration_simulations_run_id_fkey`、`integration_simulation_incidents_simulation_id_fkey`、`integration_simulation_incidents_event_id_fkey` |
| 唯一 | `uq_integration_simulations_run`、`uq_integration_simulation_incident_event`、`uq_integration_simulation_one_incident` |
| 检查 | `ck_*_payload_identity`（payload 与行标识一致）、`ck_integration_simulation_incidents_row_version_nonnegative`、`ck_integration_simulation_incidents_status` |
| 索引 | `ix_integration_simulations_scope_run`、`ix_integration_simulation_incidents_scope` |

`uq_integration_simulation_one_incident` 是"每次模拟仅一条异常"的数据库级保证，与代码中的 advisory lock 形成双保险。

---

## 4. 测试执行记录

全部使用 `uv run pytest --import-mode=importlib`（等价入口 `python -m uv run pytest`，因本机 `uv.exe` 不在 PATH）。

| # | 命令 | 结果 | 退出码 | 日志 |
| --- | --- | --- | --- | --- |
| 0 | `ruff check`（新增/修改的 5 个 py 文件） | All checks passed | 0 | 见报告正文 |
| 1 | `pytest -q tests/integration/test_integration_simulation.py` | **1 passed**（32.05s） | 0 | `02_stage_a_integration.log` |
| 2 | `pytest -q tests/unit/test_integration_simulation_tracks.py tests/unit/test_vehicle_delay_reschedule.py tests/integration/test_s4_timeline.py tests/integration/test_coldchain_chain_10.py` | **23 passed**（60.73s） | 0 | `03_regression.log` |
| 3 | `pytest -q -s tests/integration/test_stage_a_acceptance_14.py`（14 项取证） | **1 passed / 14 项全 PASS**（32.48s） | 0 | `04_acceptance_14.log` |

失败数：**0**。未删除测试、未降低断言、未添加 skip/xfail。

---

## 5. 14 项业务流程验收（逐条）

场景：PostgreSQL 中的 `coldchain_chain_10`（10 单 × 3 工序）。

| # | 验收项 | 实测证据 | 结论 |
| --- | --- | --- | --- |
| 1 | 从数据库读场景并生成 checked run | `integration_scenarios` 回查到行（`source_kind=synthetic`），run 状态 `checked` | PASS |
| 2 | 10 订单 / 30 工序正确关联 | `scope_orders=10`；`warehouse_tasks=30`，分布 `receive 10 / sort 10 / load 10`；每单 `warehouse_task_count=3` | PASS |
| 3 | 装车交接 ≤ 运输发车 | 10 单 `loading_ready_at_s` 均 ≤ 该车首个后续 `vehicle_departure`；S4 七项对账全 True，含 `departure_before_loading_ready`、`handoff_before_warehouse_operations_finished` | PASS |
| 4 | 生成车辆路线与分段轨迹 | 2 台车 / 42 段；段内 `start_s<=end_s`、段间单调不重叠、末段终点 = `end_node_id` | PASS |
| 5 | 轨迹可从 PostgreSQL 重读 | `integration_simulations.payload->'tracks'` 与 API 返回**逐字节相等** | PASS |
| 6 | 在途车辆可登记合法 `transport_delay` | 事件落 `events` 表，`payload->>'kind'='transport_delay'`、`source='integration-simulation'` | PASS |
| 7 | 正确计算受影响订单与时间变化 | `affected_order_ids` 4 单；`before_eta_s`/`after_eta_s` 差值单调不减、最大顺延 60s；`proposal_valid=true` | PASS |
| 8 | 延误前位置与事件保持不变 | `t = time_s-1` 时 `baseline` 与 `candidate` 的 `vehicle_positions`、`events` **完全一致** | PASS |
| 9 | 未审批前原方案生效 | `state-at view=active` → `baseline`，`active_version=0`，`incident_status=pending` | PASS |
| 10 | 人工批准后 v0→v1 | 批准后 `view=candidate`、`active_version=1`、`source_kind=simulated_delay_projection`；`baseline_version=0` 不变 | PASS |
| 11 | 重复批准不产生第二次审批 | 第二次 approve 返回 `idempotent=true`，`incidents` 计数仍为 1，`active_version` 仍为 1 | PASS |
| 12 | 人工拒绝后原方案不变 | 另一 run 拒绝后 `status=rejected`，`view=baseline`、`active_version=0` | PASS |
| 13 | `state-at` 可恢复不同时刻状态 | 在 `0 / 123 / 246 / 2795s` 四点回放成功：事件数 4→36→77→95，在途车辆数 0→0→2→0 | PASS |
| 14 | 模拟/审批/回放不改真实库存与派车 | `operational_schedule_mutated=false`、`inventory_mutated=false`；`inventory_ledger / schedules / schedule_versions / schedule_tasks` 行数全程不变 | PASS |

### 5.1 关键数值快照

- 订单：10；仓储工序：30（`receive/sort/load` 各 10）
- 车辆：2；轨迹段：42
- 延误：在途 `time_s = 发车 + 1s`，`delay_s=60`
- 影响：4 单，最大 ETA 顺延 60s；S1 局部解 `applied_to_simulation=false`（符合"不得把仓库起点路线接到行驶中车辆"的要求）
- 版本：基线 `v0` → 批准后 `v1`；拒绝保持 `v0`

---

## 6. 库存与派车是否被意外修改

| 表 | 验收前 | 验收后 | 结论 |
| --- | --- | --- | --- |
| `inventory_ledger` | 0 | 0 | 未写入 |
| `schedules` | 0 | 0 | 未写入 |
| `schedule_versions` | 0 | 0 | 未写入 |
| `schedule_tasks` | 0 | 0 | 未写入 |
| `warehouse_tasks` | 30 | 30 | 幂等（累计 13 次模拟/导入仍为 30） |

API 侧 `operational_schedule_mutated=false`、`inventory_mutated=false` 在 baseline、pending、approved、rejected 四种状态下均成立。

**结论：没有真实库存或派车计划被修改。**

---

## 7. 失败项与根因

**产品代码失败项：0。**

验收过程中出现过的失败均在**取证脚本自身**，非被测代码缺陷，如实记录：

| 现象 | 根因 | 处理 |
| --- | --- | --- |
| `column "source_kind" does not exist` | `integration_scenarios` 无该列，值在 `payload` 内 | 改查 `payload->>'source_kind'` |
| `no load task was linked to a transport stop` | 我最初假设 `track.stops[].task_ids` 是仓库作业任务，实际是**运输任务** | 改用 `order_details.loading_ready_at_s` 与 `vehicle_departure` 事件比对 |
| `'str' object has no attribute 'get'` | `reconciliation.checks` 是检查名列表（`{name: bool}`），非 dict 列表 | 直接读 `reconciliation.passed` |
| `assert None`（A07） | `impact` 无 `delay_s`/`max_shift_s` 字段 | 改用 `before_eta_s`/`after_eta_s` 差值 |

环境层面的偏差（非缺陷）：

- 本机 `uv.exe` 不在 PATH → 统一用 `python -m uv run ...`（与 `uv run ...` 等价，解析到同一 `.venv`）。
- Docker 容器内 `port` 显示 5432 属端口映射正常现象。

---

## 8. 尚未完成 / 不在本阶段范围

1. **单次延误限制**：每次模拟只接受一个延误事件（数据库 `uq_integration_simulation_one_incident` 保证），多次连续异常未实现。
2. **仅 hold-and-resume 策略**：批准后是"原地等待 + 剩余行程顺延"；从行驶中位置重新求解道路后缀未实现，S1 局部解仅作诊断展示。
3. **轨迹性质**：由 checked 方案时间插值生成的分段示意（`segments`），不是 GPS/真实道路导航，也不是 SimPy 实测事件。
4. **前端未接入**：前缀 `generated.ts` 缺 S3/S4 类型，`contracts:generate` 工具链本身损坏（脚本缺失 + `openapi-typescript` 未装），阶段 B 需一并补齐。
5. **演示库仍空**：5433 的 `orders / warehouse_tasks / inventory_ledger` 仍为 0（本轮按约定未写入），组会演示前需另行批准导入。
6. **无独立 SimPy Job / 企业业务表抽取**：当前数据来源于已导入的 PostgreSQL 场景与 checked run 证据。

---

## 9. 结论与建议

**建议进入阶段二（前端接入），前置条件如下：**

1. 先补齐 `generated.ts` 与 `contracts:generate`，否则阶段 B 只能继续手写类型。
2. 阶段 B 的 UI 文案必须严格区分"计划 / 模拟 / 实际作业"三种数据来源，不得把 `segments` 表述为真实道路轨迹或 GPS 遥测。
3. 演示前需单独批准是否向 5433 演示库导入 `coldchain_chain_10`（本阶段未写入）。

**Stage A 后端闭环已具备实库可验收状态**：迁移可重复执行、14 项业务闭环全部通过、库存与派车计划零污染、审批幂等且有数据库级唯一约束兜底。

---

## 附：证据文件清单

| 文件 | 内容 |
| --- | --- |
| `01_alembic.log` | 迁移版本与 head |
| `02_stage_a_integration.log` | 阶段一集成测试（1 passed） |
| `03_regression.log` | 回归 23 passed（tracks / vehicle delay / S4 timeline / chain_10） |
| `04_acceptance_14.log` | 14 项逐条取证（含 `[A01]`–`[A14]` 行） |
| `05_schema_and_counts.log` | 表结构、约束、索引、行数 |
| `06_isolation.log` | 5433 未启动、5434 指向、库清单 |
| `test_stage_a_acceptance_14.py` | 14 项验收脚本（untracked，取证用，未提交） |
