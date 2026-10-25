# 功能模块合并说明

本次只重组系统功能入口，并恢复冷链运输、大数据平台、收货与批次风险页面；原有入库、出库、数字孪生、预警、AI Agent 与后端业务接口均保留。

## 最终菜单结构

1. 数字孪生大屏

2. 冷链流转管理
   - 出库管理
   - 入库管理
   - 冷链运输

3. 质量与风险管理
   - 收货与批次风险
   - 风险预警

4. 智能分析
   - 大数据平台
   - AI 智能模块

## 新增与调整

- 新增 `ColdChainTransport.vue` 冷链运输页面。
- 新增 `ReceivingRisk.vue` 收货与批次风险页面。
- 新增 `DataPlatform.vue` 大数据平台页面。
- 新增 `/api/cold-chain/overview` 演示运输数据接口。
- 新增 `/api/data-platform/overview` 数据平台概览接口。
- 复用原有 `/api/fresh/batches`、`/api/fresh/batches/risk` 和 `/api/fresh/receive/confirm`。
- 将 Agent 明确放在 AI 智能模块中；大数据平台与 AI 智能模块共同归入“智能分析”。
- 未修改数据库结构。

## 验证结果

- 13 个 Vue 文件均通过 Vue SFC 脚本与模板编译检查。
- 当前执行环境未安装 Maven，未进行完整 Maven 编译。
- 原项目内的 Node 依赖缺少 Linux Rollup 可选包，因此此环境无法执行完整 Vite build；这是原压缩包依赖环境问题，不是本次页面语法错误。
