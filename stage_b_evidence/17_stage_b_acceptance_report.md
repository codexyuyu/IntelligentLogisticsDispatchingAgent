# 阶段二前端整合验收报告（Stage B）

**验收对象**：`StageB_frontend_integration_overlay_20261030.zip`（13 文件前端增量）
**验收日期**：2026-10-30
**验收结论**：**发现 1 个挂载缺陷，已修复并全量复验通过；建议队友同步该 1 行修复后正式关闭阶段二**

---

## 1. 基线与合并方式

| 项 | 值 |
| --- | --- |
| 合并目标 | `D:\1aaaqianduan\partner\_stage_a_test`（已通过 Stage A 实库验收的副本，HEAD `fd1f241` + Stage A 后端 overlay 11 项未提交改动） |
| 合并方式 | 增量覆盖（仅前端 12 文件 + 1 交接文档），未触碰任何 Stage A 后端文件 |
| 冲突核对 | 三方哈希对比：6 个被修改文件的工作区版本 == `fd1f241` HEAD（Stage A 未动前端），7 个全新文件，**零冲突、无覆盖风险** |
| 5433 演示库 | 全程 `exited`、无监听、`StartedAt` 未变（2026-10-29T18:01:35Z），**未被触碰** |
| 数据库 | 仅 5434 隔离库 `logistics_stage_a_test`（迁移 `0012_integration_simulation`） |

## 2. 构建与测试（全部真实执行，非离线声明）

| 步骤 | 命令 | 结果 |
| --- | --- | --- |
| 依赖安装 | `npm ci` | exit 0，163 包（队友环境缺失的一步，本机 27s 完成） |
| 类型检查+生产构建 | `npm --workspace @logistics/frontend run build`（`tsc --noEmit && vite build`） | exit 0，2.1s |
| 单元测试 | `npm --workspace @logistics/frontend run test` | **13 文件 / 48 用例全部通过**，含新增 `features/stageB/api.test.ts` 4 例 |
| 后端回归 | `uv run pytest --import-mode=importlib tests/integration/test_integration_simulation.py tests/unit/test_integration_simulation_tracks.py` | **8 passed**（44.8s，真实 5434 库） |

## 3. 契约一致性核对（以已验收的 Stage A API 实际 JSON 为准）

逐字段比对 `features/stageB/api.ts` 与后端 `api/integration.py`、`application/integration_simulation.py`、`integration_simulation_tracks.py`、`timeline.py`：

- 路由：`GET/POST /integration/runs/{id}/simulation`、`GET .../simulation/state-at?time_s&view`、`POST .../simulation/incidents`、`POST .../incidents/{id}/approve|reject` —— **全部一致**；
- 请求体：`vehicle_id/time_s/delay_s/source_event_id/reason/budget_ms`、`expected_row_version` —— 一致（后端 `extra='forbid'`，前端不多发字段）；
- 响应：`tracks[]`（`vehicle_id/segments/from_node_id/to_node_id/start_s/end_s`）、`sample_track` 返回的 `from_node_id/to_node_id/progress`、`impact.before_eta_s/after_eta_s`、`proposal_valid`、`checks: Record<string,boolean>`、state-at 的 `in_transit_vehicle_ids/completed_order_ids/completed_operation_ids/active_operation_ids` —— **全部一致，无需修订 api.ts**。

## 4. 发现的缺陷与修复

### Bug（1 个，阻断级）：「仿真回放」页未挂载 Stage B 组件

- **现象**：首轮 UI 验收中 `#/simulations` 显示的仍是旧版本地 SimPy 仿真页，无时间轴滑块、无 3D、无方案视图切换。
- **根因**：补丁把 `StageReplay` 整合进了 `features/simulations/Page.tsx`，并在 `App.tsx` 里加了导航分组与 `stageB.css` 引入，**但 `App.tsx` 第 14 行的 import 仍指向 `./features/simulations/LiveSimulation`**，新版 `Page.tsx` 从未被引用。
- **修复**（1 行）：

```diff
-import SimulationsPage from './features/simulations/LiveSimulation';
+// Stage B: 「仿真回放」入口改用整合后的 Page（数据库驱动回放 + 折叠保留的旧本地仿真）。
+import SimulationsPage from './features/simulations/Page';
```

- 修复后重新构建、48 用例复测、全链路 UI 复验均通过。修复 diff 见 `16_fix_simulations_entry.diff`。
- 其余 4 个页面（联合调度/仓储运营/运输计划/异常处置）挂载关系核对无误。

### 非缺陷备注

- `favicon.ico` 404：浏览器默认请求，项目从未提供，与 Stage B 无关；
- `features/simulations/LiveSimulation.tsx` 修复后成为未被引用的孤儿文件，建议队友决定去留；
- 回放页"后端返回车辆位置"只显示 `to_node_id`，未显示 `progress`，导致 baseline/candidate 文本相同（数据实际不同，3D 与状态行可区分）——建议后续把 progress 一并显示。

## 5. 真实业务链端到端验收（Chrome 真实浏览器 + 隔离后端 8100 + 5434 库）

完整走查两个 run（批准路径 `929e8f73…`、拒绝路径 `fd05f7b7…`），共 20 项 PASS：

| 页面 | 验证内容 | 结果 |
| --- | --- | --- |
| 联合调度 | 场景选择→「计算并协商」→ checked → RunBar 自动获得 run 编号（无需复制任务 ID）→「启动本次模拟」→ `integration_last_run` 持久化跨页传递 | PASS ×2 run |
| 仓储运营 | 「联合排程甘特图」30 工序渲染；「实际库存台账」切换渲染 | PASS |
| 运输计划 | `DigitalTwin3D` canvas 渲染持久化路线（示意拓扑），统一时间轴/播放控制，旧"运输调度"功能保留 | PASS |
| 异常处置 | 默认选中首辆在途车、发生时刻=首条发车+1s；60s 延误 → 二次确认 → 影响分析（4 单、最大顺延 60s）→ 批准 v0→v1 / 拒绝保持 v0 → 刷新后审批状态从数据库恢复 | PASS ×2 |
| 仿真回放 | StageReplay 挂载（修复后）；方案视图 active/baseline/candidate；t=1400 时 active(v1)≡candidate 且车辆进度落后于 baseline（0.117 vs 0.183，顺延生效）；回到起点重播 | PASS |

**接口级权威证据**（t=1400）：baseline 事件 87 条 / candidate 88 条（多一条 `transport_delay`）；两视图 `operational_schedule_mutated=false`、`inventory_mutated=false`。

## 6. 零污染核验

| 表 | 验收前 | 验收后 | 结论 |
| --- | --- | --- | --- |
| inventory_ledger | 0 | 0 | 无写入 |
| schedules | 0 | 0 | 无写入 |
| schedule_versions | 0 | 0 | 无写入 |
| warehouse_tasks | 30 | 30 | 幂等，未新增 |
| events | 12 | 13 | +1 为第二轮模拟自身合法的 `transport_delay` 事件 |

## 7. 结论与移交

1. **阶段二前端整合在功能与契约层面验收通过**（含 1 行挂载修复，需队友同步）。
2. 需要队友做的最小同步：把 `16_fix_simulations_entry.diff` 应用到其工作副本（或直接改 `App.tsx` import 行）。
3. 遗留项不变：`contracts:generate` 与旧 OpenAPI 不兼容问题仍待后续修复；S1 车辆延误重调度尚未接入状态快照。
4. 本轮**未执行任何 commit / push**，`_demo_p0` 原工作区未动，5433 演示库未动。

## 附件清单（stage_b_evidence/）

| 文件 | 内容 |
| --- | --- |
| 01_npm_ci.log | 依赖安装 |
| 02/12_*_build*.log | 修复前后生产构建 |
| 03/13_*_vitest*.log | 修复前后 48 用例 |
| 04_backend.log / 06_worker.log | 隔离 API 与 worker |
| 05/07/08/09_*_*.json | run/模拟响应取证 |
| 10_vite.log | 前端 dev server |
| 11_ui_check.log | 第一轮 UI 验收（发现 Bug） |
| 14_pollution_before.log | 污染基线 |
| 15_ui_check2.log | 第二轮 UI 验收（修复后全 PASS） |
| 16_fix_simulations_entry.diff | **需同步给队友的 1 行修复** |
| state_{baseline,active,candidate}.json | t=1400 三视图权威证据 |
| shots/*.png | 20 张关键页面截图 |
