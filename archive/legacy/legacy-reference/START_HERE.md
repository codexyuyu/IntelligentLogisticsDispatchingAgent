# 基于数字孪生与大语言模型的智能仓储可视化决策系统 MVP

本版本已经整理成适合 **VSCode + Docker** 打开的常见项目结构：

- 前端：Vue3 + Vite + Element Plus + ECharts + Three.js
- 后端：Spring Boot + MyBatis + WebSocket
- 数据库：MySQL 8.0
- 缓存：Redis
- AI：默认本地规则回答，可选 DeepSeek API

## 统一端口和连接信息

| 项目 | 默认值 |
|---|---|
| 前端地址 | http://localhost:5173 |
| 后端地址 | http://localhost:8080 |
| 后端 API 前缀 | /api |
| WebSocket 地址 | /ws |
| MySQL Host | localhost |
| MySQL Port | 3306 |
| MySQL Database | smart_warehouse |
| MySQL User | root |
| MySQL Password | 123456 |
| Redis Port | 6379 |

> 如果你的电脑已经安装了 MySQL 并占用了 3306，请打开根目录 `.env`，把 `MYSQL_PORT=3306` 改成 `MYSQL_PORT=3306`，然后后端本地运行时也要把 `MYSQL_PORT` 改成 3306。

---

## 方式一：推荐开发模式

### 1. 用 VSCode 打开项目根目录

打开的目录必须是包含 `backend`、`frontend`、`db`、`docker-compose.yml` 的这一层。

### 2. 启动 MySQL 和 Redis

在根目录终端执行：

```bash
docker compose up -d
```

### 3. 启动后端

```bash
cd backend
mvn spring-boot:run
```

检查后端：

```text
http://localhost:8080/api/dashboard
```

### 4. 启动前端

另开一个终端：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开：

```text
http://localhost:5173
```

演示账号：

```text
admin / admin123
demo / demo123
```

---

## 方式二：Docker 一键启动全部服务

在根目录执行：

```bash
docker compose -f docker-compose.full.yml up --build
```

然后打开：

```text
http://localhost:5173
```

---

## VSCode 快捷任务

按 `Ctrl + Shift + P`，输入 `Tasks: Run Task`，可以看到：

1. `1. Start MySQL + Redis`
2. `2. Run Backend`
3. `3. Install Frontend Dependencies`
4. `4. Run Frontend`
5. `Docker: Run Full Project`

也可以直接运行根目录的：

- `start-dev-windows.bat`
- `start-full-docker-windows.bat`
- `start-dev-mac-linux.sh`

---

## 目录结构

```text
smart-warehouse-twin-mvp/
├── backend/                 Spring Boot 后端
├── frontend/                Vue3 前端
├── db/init.sql              MySQL 建表和演示数据
├── db/reset-demo.sql        重置演示数据脚本
├── docker-compose.yml       只启动 MySQL + Redis
├── docker-compose.full.yml  一键启动全部服务
├── .env                     端口、数据库密码等统一配置
└── .vscode/                 VSCode 推荐扩展、任务和启动配置
```

---

## 常见问题

### 1. 数据库密码是 123456，但还是连不上

如果你以前运行过旧版本，Docker 可能保留了旧 MySQL 数据卷。你不需要旧数据时，可以执行：

```bash
docker compose down -v
docker compose up -d
```

### 2. 3306 端口被占用

把根目录 `.env` 里的：

```text
MYSQL_PORT=3306
```

改成：

```text
MYSQL_PORT=3306
```

然后本地后端运行时也要使用 `MYSQL_PORT=3306`。如果用全 Docker 模式，后端在容器内仍然访问 `mysql:3306`，不需要改代码。

### 3. 前端请求后端的路线

开发模式：

```text
浏览器 → Vite 5173 → 代理 /api 到 Spring Boot 8080
```

Docker 模式：

```text
浏览器 → Nginx 5173 → 代理 /api 到 backend:8080
```

所以前端代码里统一写 `/api/...`，不要写死 `http://localhost:8080`。
