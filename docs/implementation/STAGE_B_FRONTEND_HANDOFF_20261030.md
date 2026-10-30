# Stage B 前端整合补丁 · 2026-10-30

## 基线、适用范围和不能误用的事项

- 原始前端基线：`feat/vehicle-delay-reschedule` @ `fd1f241`。
- 本补丁是**前端增量修改**，必须应用到 WorkBuddy 已通过 `0012_integration_simulation` 实库验收的 `_stage_a_test` 副本（或其无冲突更新版本）上。
- 用户上传的 `StageA_backend_acceptance_20261030(2).zip` 只有报告、日志和验收脚本，不包含 Stage A 后端源码；本环境无法启动真实 Stage A API。因此**代码的页面与真实 API 联调仍待 WorkBuddy 验证**。
- 本轮不修改 Stage A 数据库结构、仓储核心算法、S1 重调度算法；**绝对禁止碰 5433 演示库**。

## 增量变更说明

- 保留「联合调度」「仓储运营」「运输计划」「异常处置」「仿真回放」原有页面和旧行为；S5 甘特图、库存台账改作仓储运营内切换入口；S5 原 hash 保留兼容，但不单独显示导航分组。
- 联合调度：checked run 后显示模拟启动和跨页操作；通过浏览器已有 `integration_last_run` 自动传递 run ID。
- 仓储运营：保留旧本地演示库存，新增 S3 实际库存、S2/S3 甘特标签；页面明确区分模拟与真实作业推进。
- 运输计划：使用已有 `DigitalTwin3D` 绘制从 PostgreSQL 持久化读取的 Stage A 轨迹分段（示意拓扑，非 GPS）；若有审批时刻和延误长度，允许显示 hold-and-resume 动画。
- 异常处置：在原有取消订单功能上方增加单次 `transport_delay` 登记与候选影响、批准/拒绝，所有写操作由用户二次确认；审批只切换模拟版本。
- 仿真回放：在原有页面上显示统一时钟、车辆 3D、事件列表和后端 state-at；旧本地回放折叠保留，非重复导航页面。
- `features/stageB/api.ts` 使用 WorkBuddy 实测过的 Stage A 端点，避免自行发明另一个后端入口。

## 已检查证据（当前隔离构建环境）

- TypeScript 生产源码检查：`tsc --noEmit -p tsconfig.stageb.check.json`，**exit 0**。使用 R30 附件携带的离线 TypeScript/React 类型依赖完成，不代表项目锁定的 npm ci 环境验收。
- 路线段映射与候选批准纯逻辑 Node 离线冒烟：**PASS**。
- 新增 `features/stageB/api.test.ts` 共 4 个用例：**代码已写入，Vitest 需 WorkBuddy 在本机执行**。
- 原项目 `npm ci` 在此环境没有完成，且 R30 自带依赖缺少 Linux Rollup native 模块；故**生产打包和全部 Vitest 不能声称通过**。
- `contracts/openapi.json` 仍停留在旧后端的 65 条路径，不能用其覆盖 `src/client/generated.ts`：实际尝试由旧 OpenAPI 重新生成后出现老前端 `PlanningSnapshot` 等别名缺失，已恢复原文件。**契约生成器问题保留为后续修复项，不在本补丁伪造类型。**

## WorkBuddy 一次集中验收（只用 5434 专用测试数据库）

1. 在 `_stage_a_test` 中核对 `0012_integration_simulation` 已存在，工作区变化先记录。若有人已经改动前端，先逐文件比较本补丁，不要无条件覆盖。
2. 在隔离副本应用 ZIP 内与仓库根目录对应的路径；**不要覆盖 Stage A 后端代码**。不要运行 `scripts/test_database.ps1`。
3. Windows PowerShell，在仓库根目录运行：

```powershell
node --version
npm ci
npm --workspace @logistics/frontend run build
npm --workspace @logistics/frontend run test
```

4. 在已配置测试库的环境里运行后端关键冒烟（可跳过已经取得新鲜通过证据的同一代码版本，但前端 API 需要真实测试）：

```powershell
uv run pytest --import-mode=importlib -q tests/integration/test_integration_simulation.py
```

5. 开启本机隔离 API 和前端开发服务器后，以已经入库的 `coldchain_chain_10` 做**一次完整页面验收**：
   - 「联合调度」确认 checked run，点击“启动本次模拟”；不得要求用户重新复制多个任务 ID。
   - 「仓储运营」甘特图显示 30 道工序，真实库存为空时明确标注，不要点击实际作业写入。
   - 「运输计划」3D 展示 2 车及其路线；时间轴拖动时后端 `state-at` 能返回真实的模拟状态。
   - 「异常处置」选在途车辆，默认时刻为第一条发车事件+1 秒，触发 60 秒延误；核验受影响订单与候选对比。
   - 在不同运行中分别验收批准（v0→v1）和拒绝（维持 v0）；刷新页面后再次打开能恢复审批信息。
   - 「仿真回放」对照 baseline、active、candidate；异常之前两种视图状态相同，批准后路线暂停和 ETA 顺延，最后可回到起点重播。
   - 同时核对 `inventory_ledger` 与真实 `schedules/schedule_versions` 数量前后相等。
6. 发现字段名不匹配，应以已经通过真库验收的 Stage A API 实际 JSON 为准修订 `features/stageB/api.ts`，**不要改 Stage A 的已验收契约来迎合前端猜测**。
7. 一次性返回测试日志、截图或 HAR（去除 token）及失败根因；不自动 commit/push、不动 5433。

## 硬约束与未覆盖项

- 模拟状态、真实库存和实际派车必须区分；不允许回放自动执行 S3 `transitions`。
- 一次模拟只允许一个异常；重调度可批准候选目前为原地等待、剩余行程顺延，**不是中途道路重新规划**。
- 已批准路线的地图是节点示意图；后端 state-at 才是时刻位置/送达状态权威证据。
- 源码 ZIP 未含 Stage A 后端，WorkBuddy 必须基于自身完整 `_stage_a_test` 合并。
