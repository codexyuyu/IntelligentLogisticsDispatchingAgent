# RELIABILITY-20261029 · 现有功能可靠性与操作体验

授权：2026-10-29 用户要求优化异常重调度闭环以外的部分，选择“功能可靠性与操作体验”，并要求充分执行。该任务维护当前运行实现，不启动历史 P 阶段、不签收 Gate。

事实来源：当前 DeepSeekHarness 工程、INTEGRATION.md、COMPETITION-BUILD-20261029.md、实际 API/契约及测试。旧 G01 的输入已有漂移，历史 passed 不作为本轮验收证据。

## 唯一任务与分区

目标：修复真实数据展示、列表加载和选择一致性，以及求解/实验/仿真任务在失败、切页、刷新时的恢复。

精确可写文件（相对工程根）：

- root：`apps/frontend/src/api.ts`、`apps/frontend/src/api.test.ts`、`apps/frontend/src/lib/masterData.ts`、`apps/frontend/src/lib/masterData.test.ts`、`apps/frontend/src/features/dashboard/Page.tsx`、`apps/frontend/src/features/dashboard/LiveOverview.tsx`、`apps/frontend/src/features/dashboard/LiveOverview.test.tsx`、`apps/frontend/src/features/orders/Page.tsx`、`apps/frontend/src/App.tsx`、`apps/frontend/src/appContext.tsx`（仅连接检查）、`apps/frontend/e2e/reliability.spec.ts`。
- transport：`apps/frontend/src/components/TransportWorkflow.tsx`、`apps/frontend/src/components/TransportWorkflow.test.tsx`、`apps/frontend/src/features/postgres/ResourcePanel.tsx`、`apps/frontend/src/features/postgres/ResourcePanel.test.tsx`。
- async：`apps/frontend/src/features/integration/Page.tsx`、`apps/frontend/src/features/integration/Page.test.tsx`、`apps/frontend/src/features/experiments/IntegrationExperiments.tsx`、`apps/frontend/src/features/experiments/IntegrationExperiments.test.tsx`、`apps/frontend/src/features/simulations/LiveSimulation.tsx`、`apps/frontend/src/features/simulations/LiveSimulation.test.tsx`、`apps/frontend/src/lib/asyncJobs.ts`、`apps/frontend/src/lib/asyncJobs.test.ts`、`apps/frontend/e2e/integration-loop.spec.ts`。
- warehouse：`apps/frontend/src/features/warehouses/Page.tsx`、`apps/frontend/src/features/warehouses/Page.test.tsx`。
- 文档与开发证据：本文件、`docs/implementation/reports/RELIABILITY-20261029.md`、`tmp/RELIABILITY-20261029/`。

所有文件属 A；唯一整合者 root。公共 request 保留原签名并支持 signal、错误正文与超时。运输任务的浏览器恢复键约定为 `dsh_transport_job_id`；联合运行沿用 `integration_last_run`。

不修改：异常重调度闭环、B 模块、公共契约/生成类型、依赖与锁、历史 Gate、demo/demos/archive。仓库孪生及其三维资源存在用户并发修改，本任务不覆盖。

## 验证

先执行定向组件/请求测试，再前端测试与生产构建；对真实服务做浏览器操作验证。测试替身只证明前端分支，真实 PostgreSQL/worker/求解器流程另外记录。无证据不声明功能或 Gate 通过。保留失败日志；最终记录修改文件哈希与测试结果。
