# 统一演示流程（2026-10-30）

## 目标

让演示者通过原有页面完成一次完整的数据库驱动业务链，避免反复找菜单和复制 UUID。

**没有新增一级导航菜单、没有修改数据库表或业务求解器，也没有启动/修改任何 PostgreSQL 实例。**

## 典型演示（从登录开始）

1. 页面顶部「演示流程导航」提示「生成联合方案」：点击「前往联合调度」，选择场景（如 `coldchain_chain_10`），点击「计算并协商」；若后台仍在计算，顶部会自动更新进度，等待 `checked` 且联合校验成功。
2. 顶部自动变为「启动数据库模拟」：确认当前连接的是获得授权的隔离环境后，点击「启动本次模拟」。用户必须在确认框手动确认，前端才会调用后端现有模拟启动 API；若模拟已存在，读取旧模拟而非重复创建。
3. 导航自动进入「异常处置」。在已有模拟车辆延误表单选择车辆、时刻和延误时长；点击「触发模拟延误并分析」，审阅候选，再人工批准或拒绝。旧的订单取消流程被折叠保留，并明确是另一条业务链。
4. 审批后点击页面底部「下一步：查看方案回放与路线对比」，或者顶部导航的「查看 v0 / v1 回放」。在原「仿真回放」查看 baseline / candidate / active 和 3D 轨迹；刷新页面后可以重新读取数据库记录。

需要时可通过顶部「查看车辆轨迹」跳转原「运输计划」；仓储运营、调度助手、对照实验等仍保留原入口，但不是主演示的必经步骤。

## 本次修改

- `apps/frontend/src/components/DemoJourney.tsx`：持久的四步流程与上下文提示；只通过已有 API 查询 checked run 和 simulation/incident 状态，绝不从浏览器阶段标记推断数据库审批已生效。
- `apps/frontend/src/App.tsx`：原导航和业务页面不变，给所有页面顶部加统一引导。
- `apps/frontend/src/features/stageB/RunContext.tsx`：已关联 UUID 以简明状态呈现；历史运行手动输入折叠到高级操作；模拟启动添加显式确认；必要时通知全局状态刷新。
- `apps/frontend/src/features/stageB/Incident.tsx`：登记和审批之后刷新全局进度；审批结束给出下一步跳转。
- `apps/frontend/src/components/ExceptionPanel.tsx`：旧订单取消独立流程折叠，减少与模拟延误混淆。
- `apps/frontend/src/styles.css`：响应式流程导航样式。
- `apps/frontend/src/components/DemoJourney.test.ts`：不同业务状态的流程推导测试。

## 安全与边界

- 查询运行状态均为 GET。唯一新增的写操作入口是用户明确点击并确认的「启动本次模拟」，直接复用现有后端端点；不提供自动审批。
- 首次运行仍需有人选择并求解场景。不自动导入、修改订单或清理数据库。
- 绝不自动操作 `5433`；所有实际数据库验收需事先确认授权的隔离环境。
- 运行编号从 `integration_last_run` 恢复，页面无需反复复制；切换历史运行的手工 UUID 输入保留在高级操作内。
- 若后端不在线或未通过联合校验，流程不跳到模拟/审批阶段，避免假成功。

## 验证说明

对本次变更已执行 `node node_modules/typescript/bin/tsc --noEmit -p apps/frontend/tsconfig.json`。原 ZIP 内 `node_modules` 是 Windows 平台依赖，本环境缺少 Linux 版 Rollup 原生包，因此 Vite 构建和 Vitest 未在当前容器执行；请在项目规范 Node 环境中进行一次前端构建和浏览器流程验收。此状态不能误写为构建已通过。
