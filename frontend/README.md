> 历史源码参考：本目录不再作为正式运行入口。中文界面已移植至 `apps/frontend`，统一访问 http://localhost:8080。

# R23 React 本机 PostgreSQL 调度入口

安装依赖：`npm ci`。保持 `backend/start_pg_r22_local.ps1` 所启动的服务运行，在 frontend 目录执行 `npm run dev`，浏览器访问 `http://127.0.0.1:5173` → 左侧 `PostgreSQL 实库调度`。

`/local-pg` 仅代理本机测试子应用；模拟路线非正式配送路线。Windows 构建：`npm run build`。最小接线检测：`npm run test:pg-ui`。详见 `../docs/R23_POSTGRESQL_REACT_INTEGRATION.md`。

---

# Owner CODEX_FRONTEND

7 个模块页面都是清楚标注的占位页。健康检查通过生成类型客户端调用真实后端；没有订单/路线假数据。页面类型从 OpenAPI 生成，B 不编辑前端。

Node 22.12+；`npm ci` 后 `npm run dev`。Vite 将 /api 转发到本机 8000，不需放宽 CORS。`npm run contracts:check` 和 `npm run build` 是最小交付检查。生产部署由 AC 后续配置同源代理；当前 preview 只预览静态骨架。
