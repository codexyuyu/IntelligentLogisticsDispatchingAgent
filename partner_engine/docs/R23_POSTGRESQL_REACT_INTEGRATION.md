# R23 PostgreSQL 实库调度台 · React 集成与交接

版本：R23（基于 R22）；2026-10-17。此版本新增**前端操作功能**，未改动 R20 Routing 求解器、共享 `/api/v1` OpenAPI、R17～R20 证据与旧 PostgreSQL 业务表。

## 已实现

- 左侧导航“业务数据 → PostgreSQL 实库调度”新增独立 React 页面。
- 原“订单与库存”“运输计划”页顶部增加 PostgreSQL 实库的只读摘要表；原有数字孪生场景视图仍单独保留，防止混用。
- 实库台提供：订单全列表、车辆全列表、WH 仓库/冷藏冷冻/速度/预算/订单上限表单，通过原 R21 `POST /local-pg/pg-preview/route` 调用 **R20 OrToolsRoutingSolver**，展示独立校验和路线停靠序列。
- 只有求解器有解、独立校验为 `passed`、无漏单、且用户明确勾选“仅保存模拟路线”时，才允许调用 R22 `POST /local-pg/pg-preview/saved`；服务端**重新取数求解并独立校验**，保存后只写 `public.pg_simulation_previews`。
- 归档列表、详情和内嵌原 R22 Leaflet 地图；地图直线连线，非道路导航，不作为执行路线。
- 本轮不创建数据库表、不自动修改 PostgreSQL；不改现有正式业务方案 `dispatch_plans/routes/route_stops`。

## Windows 最短启动步骤

**把 ZIP 解压到新的文件夹，不覆盖 R22；旧 R22 后端先按 Ctrl+C 停止。**

第一次运行 R23 前端需要联网安装 Node.js 依赖；建议 Node.js 22.12 或以上。默认本机 FastAPI 在 8000、Vite 在 5173。需要两个 PowerShell 窗口。

窗口 A：在解压后的 `backend` 目录打开 PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_pg_r22_local.ps1
```

输入原 PostgreSQL 密码。**不用**再指定 `-CreateDemoTable`，因为 R22 演示表已由用户成功创建、归档已写入。

窗口 B：在 `frontend` 目录打开 PowerShell：

```powershell
npm ci
npm run dev
```

浏览器打开 `http://127.0.0.1:5173`，在左侧点 `PostgreSQL 实库调度`。

若 `npm ci` 提示命令不存在，先安装 Node.js 22.12+。若 5173 被占用，请关闭旧前端进程：本项目启用了 `strictPort`。

## 仅验收 4 件事（不重跑性能实验）

1. 在实库调度台看到订单 20、车辆 4、节点 22、距离记录 484（以当前数据库值为准），订单/车辆两个选项卡有明细；原订单、车辆页顶部能看到实库摘要。
2. 选择 WH001 / chilled / 30 km/h / 5000 ms / 20 单，点击 `运行模拟路线预览`，确认出现求解状态、独立校验、路线停靠节点。真实返回为准，不预先保证任何特定路线。
3. 如校验 `passed` 且零未服务，勾选确认并点击归档，后端重新求解；成功时会显示新的 `SIMR22_...` 编号，且 `business_plans_mutated` 为 `false`。
4. 进入 `归档与地图` 选择已经成功保存的 `SIMR22_714f433174d845e7bfbb0554` 或新的编号，地图能正常嵌入（第一次加载需能访问 OSM/Leaflet 公网资源）。

**安全边界**：R23 前端只使用 Vite 本地代理 `/local-pg`，对应后端必须通过本机启动脚本启用；此接口没有生产身份认证，不得暴露到公网。`/api/v1` 的主 OpenAPI 与生成的 TypeScript 契约**保持原样**，实库台通过独立的窄类型适配器连接原已发布的本地 PG API。

**业务边界**：缺失真实道路行驶时长、体积、车辆班次、仓储装车交接等条件时不得确认执行。UI 明示“模拟预览、不可执行”；当前暂不开发正式业务计划保存，防止演示假设进入生产记录。

## 测试说明与已知问题

- 定向后端接口/契约回归：`python -m pytest -q tests/test_pg_simulation_archive.py tests/test_pg_routing_preview.py tests/test_contracts.py` → `33 passed`（隔离环境，未连接用户 PG）。
- 前端源文件 TS/TSX 解析（全局 TypeScript 5.8.3 `transpileModule`）：新增/改动 7 个 TS/TSX 文件均无语法诊断。`node frontend/scripts/test-r23-pg-ui.cjs` → PASS。
- 当前交付环境无法完整获取 npm 锁定包：`npm ci --offline` 缺缓存；之后 `npm ci` 未完整结束导致包目录空壳；`npm run build` 因缺 `openapi-typescript` 而无法继续。**未宣称前端完整类型检查/构建成功；需用户 Windows 执行 `npm ci` + `npm run build` 检查**。
- 项目原有静态检查的 7 条 application→adapters 既有告警未修复，本轮没有增添该类依赖。
- 本轮没有重跑 R17、R18、R19、R20 任何规模/消融实验。

## 修改范围

- `frontend/src/App.tsx`, `frontend/vite.config.ts`, `frontend/src/styles.css`
- `frontend/src/features/orders/Page.tsx`, `frontend/src/features/vehicles/Page.tsx`
- `frontend/src/features/postgres/api.ts`, `Page.tsx`, `ResourcePanel.tsx`
- `frontend/scripts/test-r23-pg-ui.cjs`, `frontend/package.json`
- 文档、增量日志、FILE_MAP 与打包清单。

未修改 `backend/app/`, `backend/app/contracts/`, `backend/app/adapters/routing/`, `contracts/`, 已验收证据目录、`OWNERSHIP.json`。
