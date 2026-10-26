# VSCode + Docker 优化记录

本次整理目标：让项目按照更常见的本地开发和 Docker 部署方式运行，减少零基础同学打开项目时遇到的路径、端口、数据库连接问题。

## 已修改内容

1. 删除压缩包中的重复嵌套项目目录，避免 VSCode 打开错层级。
2. 删除 `frontend/node_modules` 和 `backend/target`，压缩包更干净，依赖由 `npm install` 和 Maven 自动恢复。
3. 统一端口：前端 `5173`，后端 `8080`，MySQL `3306`，Redis `6379`。
4. 统一数据库连接：`root / 123456 / smart_warehouse`。
5. 后端 `application.yml` 改成环境变量 + 默认值写法，既能本地跑，也能 Docker 跑。
6. Docker Compose 增加 `.env` 变量读取，方便以后只改 `.env` 不改代码。
7. 前端 API 统一使用 `/api`，开发环境由 Vite 代理，Docker 环境由 Nginx 代理。
8. WebSocket 统一使用 `/ws`。
9. CORS 改成支持多个来源，并补充 `PATCH`，避免仓库存储类型修改接口被浏览器拦截。
10. 新增 `.vscode/tasks.json`、`.vscode/launch.json`、`.vscode/extensions.json`，方便 VSCode 一键运行任务。
11. 新增 `.dockerignore`，避免 Docker 构建时把无用文件复制进去。

## 最常用启动命令

```bash
docker compose up -d
cd backend && mvn spring-boot:run
cd frontend && npm install && npm run dev
```

或者全 Docker：

```bash
docker compose -f docker-compose.full.yml up --build
```
