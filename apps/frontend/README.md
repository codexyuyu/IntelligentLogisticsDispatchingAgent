# 唯一正式前端

保留“县域冷链调度”中文界面；英文 Dispatch Workbench 外壳及 workbench.html 已删除。
唯一 npm workspace 为 apps/frontend；唯一 Compose 前端服务为 frontend，配置地址 http://localhost:8080。
后端仍是 apps/backend + packages，接口 /api/v1，契约 2.0.0；不启动旧 backend/app 或 local-pg 服务。

已绑定现有 API 的页面：API Key 登录、数据库订单/车辆读取、运输求解/候选/确认提交/刷新回读、版本管理、异常接口、调度助手。
本轮构建和单元测试通过；浏览器及容器切换尚未通过验收，见 docs/implementation/R08-ROLES-20261025.md。
未对接：第一版 20 单演练、旧仓运闭环和孪生执行接口；相关操作显示未接入，不生成假结果。
client/generated.ts 只保存第一版视图的历史类型，供未联动的可视化组件使用；不是当前 API 的校验依据。
当前 API 功能使用 src/api.ts。R08 目前在 Python 进程内调用，不宣称已有 HTTP 或前端 transcript 接口。

开发：在项目根执行 npm ci，再执行 npm --workspace @logistics/frontend run dev。
验证：npm --workspace @logistics/frontend run build / run test；实际浏览器测试位于 e2e/transport-loop.spec.ts。
