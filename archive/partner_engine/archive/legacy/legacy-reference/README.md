# 基于数字孪生与大语言模型的智能仓储可视化决策系统 MVP 完整版

## 已修改内容概述

这是一个可以直接解压运行的**完整项目版本**，不是只覆盖部分文件的补丁包。它基于你上传的 `smart-warehouse-twin-mvp-optimized` 项目，已经合并前两次修改：

1. SQL 演示数据真实化：仓库名、货架/货柜名、货物名改为更贴近真实智慧仓储场景的名称。
2. 新增仓库维修表 `warehouse_maintenance`，支持设备名称、设备 id、维修时间、维修人员 id、维修方法、维修结果。
3. 修复前端部分中文乱码风险：SQL、后端 JDBC、Nginx、HTML、全局字体、3D Canvas 字体全部加入 UTF-8/utf8mb4 保险。
4. 修复 VS Code 中 `.sql` 文件被 SQL Server/MSSQL 插件误识别时容易出现的红线误报问题。
5. AI 助手示例问题同步为真实商品和真实货架名称，避免页面继续出现旧的“牛奶 / A-01”测试名称。
6. 保留原项目功能：数字孪生仓库大屏、入库管理、出库管理、库存预警、AI Agent、本地规则 RAG、WebSocket、Docker 部署等均未删除。

## 本次具体修改

| 文件 | 修改内容 |
|---|---|
| `.editorconfig` | 新增，统一 UTF-8 与 LF 换行。 |
| `.vscode/settings.json` | 增加 UTF-8、禁止自动猜编码、`.sql` 关联普通 SQL。 |
| `db/init.sql` | 合并真实演示数据、维修表、utf8mb4 编码保险。 |
| `db/reset-demo.sql` | 重置演示数据时同步真实名称和 utf8mb4。 |
| `db/upgrade-realistic-demo-data.sql` | 旧数据库升级真实名称专用脚本。 |
| `db/encoding-check.sql` | 新增乱码来源检查脚本。 |
| `backend/src/main/resources/application.yml` | JDBC 和 Hikari 连接池加入 UTF-8/utf8mb4。 |
| `backend/src/main/java/com/example/warehouse/mapper/WarehouseMapper.java` | 仓储类型修改后自动生成真实仓库名。 |
| `backend/src/main/java/com/example/warehouse/service/AiAgentService.java` | AI 示例和本地规则回答同步真实数据。 |
| `frontend/nginx.conf` | Docker 前端 Nginx 显式声明 UTF-8。 |
| `frontend/index.html` | 增加 UTF-8 双保险 meta。 |
| `frontend/src/style.css` | 增加中文字体 fallback。 |
| `frontend/src/components/Warehouse3D.vue` | 3D Canvas 中文字体 fallback。 |
| `frontend/src/views/AiAssistant.vue` | AI 页面示例问题改为真实商品。 |
| `docs/*.md` | 同步 SQL、功能映射、新手说明中的旧名称。 |

## 配置检查与修复记录

| 检查项 | 当前结果 |
|---|---|
| Java | 21 |
| Spring Boot | 3.5.11 |
| MyBatis | 3.0.5 |
| Spring AI | 1.0.3 |
| MySQL 账户 | root |
| MySQL 密码 | 123456 |
| 数据库名 | smart_warehouse |
| MySQL 字符集 | utf8mb4 / utf8mb4_unicode_ci |
| SQL 执行编码 | 已加入 `set names utf8mb4 collate utf8mb4_unicode_ci;` |
| 后端 JDBC 编码 | 已加入 `characterEncoding=UTF-8` 与 `connectionCollation=utf8mb4_unicode_ci` |
| 后端连接初始化 | 已加入 `SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci` |
| 前端 Nginx 编码 | 已加入 `charset utf-8;` |
| HTML 编码 | 已加入双 UTF-8 meta |
| 3D Canvas 中文字体 | 已加入微软雅黑、苹方、Noto、思源黑体等 fallback |
| SQL Server/MSSQL 误报 | `.sql` 已关联普通 SQL；仍建议在本项目工作区禁用 SQL Server(mssql) 插件 |

## 项目的结构

- `.dockerignore`
  - 作用/此次修改：项目文件，本次未修改。
- `.editorconfig`
  - 作用/此次修改：新增，统一 UTF-8 与 LF 换行，减少新建文件乱码风险。
- `.env`
  - 作用/此次修改：环境变量配置文件，本次未修改。
- `.env.example`
  - 作用/此次修改：环境变量配置文件，本次未修改。
- `.github/modernize/java-upgrade/.gitignore`
  - 作用/此次修改：GitHub/VS Code modernization 辅助文件，本次未修改。
- `.github/modernize/java-upgrade/hooks/scripts/recordToolUse.ps1`
  - 作用/此次修改：GitHub/VS Code modernization 辅助文件，本次未修改。
- `.github/modernize/java-upgrade/hooks/scripts/recordToolUse.sh`
  - 作用/此次修改：GitHub/VS Code modernization 辅助文件，本次未修改。
- `.gitignore`
  - 作用/此次修改：项目文件，本次未修改。
- `.vscode/extensions.json`
  - 作用/此次修改：VS Code 项目配置、启动、任务或推荐插件文件，本次未修改。
- `.vscode/launch.json`
  - 作用/此次修改：VS Code 项目配置、启动、任务或推荐插件文件，本次未修改。
- `.vscode/settings.json`
  - 作用/此次修改：增加 UTF-8、禁止自动猜编码、将 SQL 文件关联到普通 SQL，降低 MSSQL 插件误报。
- `.vscode/tasks.json`
  - 作用/此次修改：VS Code 项目配置、启动、任务或推荐插件文件，本次未修改。
- `README.md`
  - 作用/此次修改：重写为完整版本说明。
- `START_HERE.md`
  - 作用/此次修改：新手快速入口说明，本次未修改。
- `backend/.dockerignore`
  - 作用/此次修改：后端 Maven/Spring Boot 或 Docker 配置文件，本次未修改。
- `backend/Dockerfile`
  - 作用/此次修改：后端 Maven/Spring Boot 或 Docker 配置文件，本次未修改。
- `backend/pom.xml`
  - 作用/此次修改：后端 Maven/Spring Boot 或 Docker 配置文件，本次未修改。
- `backend/src/main/java/com/example/warehouse/SmartWarehouseApplication.java`
  - 作用/此次修改：后端 Java 源码文件，本次未修改。
- `backend/src/main/java/com/example/warehouse/config/PasswordConfig.java`
  - 作用/此次修改：后端配置类，处理跨域、密码、WebSocket 等，本次未修改。
- `backend/src/main/java/com/example/warehouse/config/WebConfig.java`
  - 作用/此次修改：后端配置类，处理跨域、密码、WebSocket 等，本次未修改。
- `backend/src/main/java/com/example/warehouse/config/WebSocketConfig.java`
  - 作用/此次修改：后端配置类，处理跨域、密码、WebSocket 等，本次未修改。
- `backend/src/main/java/com/example/warehouse/controller/AiController.java`
  - 作用/此次修改：后端 Controller，提供前端调用的 REST API，本次未修改。
- `backend/src/main/java/com/example/warehouse/controller/AuthController.java`
  - 作用/此次修改：后端 Controller，提供前端调用的 REST API，本次未修改。
- `backend/src/main/java/com/example/warehouse/controller/DashboardController.java`
  - 作用/此次修改：后端 Controller，提供前端调用的 REST API，本次未修改。
- `backend/src/main/java/com/example/warehouse/controller/GlobalExceptionHandler.java`
  - 作用/此次修改：后端 Controller，提供前端调用的 REST API，本次未修改。
- `backend/src/main/java/com/example/warehouse/controller/HealthController.java`
  - 作用/此次修改：后端 Controller，提供前端调用的 REST API，本次未修改。
- `backend/src/main/java/com/example/warehouse/controller/InboundController.java`
  - 作用/此次修改：后端 Controller，提供前端调用的 REST API，本次未修改。
- `backend/src/main/java/com/example/warehouse/controller/OutboundController.java`
  - 作用/此次修改：后端 Controller，提供前端调用的 REST API，本次未修改。
- `backend/src/main/java/com/example/warehouse/controller/ProductController.java`
  - 作用/此次修改：后端 Controller，提供前端调用的 REST API，本次未修改。
- `backend/src/main/java/com/example/warehouse/controller/WarehouseController.java`
  - 作用/此次修改：后端 Controller，提供前端调用的 REST API，本次未修改。
- `backend/src/main/java/com/example/warehouse/controller/WarningController.java`
  - 作用/此次修改：后端 Controller，提供前端调用的 REST API，本次未修改。
- `backend/src/main/java/com/example/warehouse/dto/AiChatRequest.java`
  - 作用/此次修改：请求/响应 DTO，用于前后端传参，本次未修改。
- `backend/src/main/java/com/example/warehouse/dto/InboundRequest.java`
  - 作用/此次修改：请求/响应 DTO，用于前后端传参，本次未修改。
- `backend/src/main/java/com/example/warehouse/dto/LoginRequest.java`
  - 作用/此次修改：请求/响应 DTO，用于前后端传参，本次未修改。
- `backend/src/main/java/com/example/warehouse/dto/OutboundRequest.java`
  - 作用/此次修改：请求/响应 DTO，用于前后端传参，本次未修改。
- `backend/src/main/java/com/example/warehouse/dto/Point.java`
  - 作用/此次修改：请求/响应 DTO，用于前后端传参，本次未修改。
- `backend/src/main/java/com/example/warehouse/dto/RegisterRequest.java`
  - 作用/此次修改：请求/响应 DTO，用于前后端传参，本次未修改。
- `backend/src/main/java/com/example/warehouse/dto/WarehouseStorageTypeRequest.java`
  - 作用/此次修改：请求/响应 DTO，用于前后端传参，本次未修改。
- `backend/src/main/java/com/example/warehouse/entity/AppUser.java`
  - 作用/此次修改：后端实体类，对应数据库表字段，本次未修改。
- `backend/src/main/java/com/example/warehouse/entity/InboundTask.java`
  - 作用/此次修改：后端实体类，对应数据库表字段，本次未修改。
- `backend/src/main/java/com/example/warehouse/entity/Inventory.java`
  - 作用/此次修改：后端实体类，对应数据库表字段，本次未修改。
- `backend/src/main/java/com/example/warehouse/entity/OutboundOrder.java`
  - 作用/此次修改：后端实体类，对应数据库表字段，本次未修改。
- `backend/src/main/java/com/example/warehouse/entity/Product.java`
  - 作用/此次修改：后端实体类，对应数据库表字段，本次未修改。
- `backend/src/main/java/com/example/warehouse/entity/ReplenishmentTask.java`
  - 作用/此次修改：后端实体类，对应数据库表字段，本次未修改。
- `backend/src/main/java/com/example/warehouse/entity/Shelf.java`
  - 作用/此次修改：后端实体类，对应数据库表字段，本次未修改。
- `backend/src/main/java/com/example/warehouse/entity/Warehouse.java`
  - 作用/此次修改：后端实体类，对应数据库表字段，本次未修改。
- `backend/src/main/java/com/example/warehouse/entity/WarningRecord.java`
  - 作用/此次修改：后端实体类，对应数据库表字段，本次未修改。
- `backend/src/main/java/com/example/warehouse/mapper/InventoryMapper.java`
  - 作用/此次修改：MyBatis Mapper，负责访问 MySQL 数据表，本次未修改。
- `backend/src/main/java/com/example/warehouse/mapper/ProductMapper.java`
  - 作用/此次修改：MyBatis Mapper，负责访问 MySQL 数据表，本次未修改。
- `backend/src/main/java/com/example/warehouse/mapper/ShelfMapper.java`
  - 作用/此次修改：MyBatis Mapper，负责访问 MySQL 数据表，本次未修改。
- `backend/src/main/java/com/example/warehouse/mapper/TaskMapper.java`
  - 作用/此次修改：MyBatis Mapper，负责访问 MySQL 数据表，本次未修改。
- `backend/src/main/java/com/example/warehouse/mapper/UserMapper.java`
  - 作用/此次修改：MyBatis Mapper，负责访问 MySQL 数据表，本次未修改。
- `backend/src/main/java/com/example/warehouse/mapper/WarehouseMapper.java`
  - 作用/此次修改：主管修改仓储类型后，仓库名自动改成更贴近真实业务的名称。
- `backend/src/main/java/com/example/warehouse/mapper/WarningMapper.java`
  - 作用/此次修改：MyBatis Mapper，负责访问 MySQL 数据表，本次未修改。
- `backend/src/main/java/com/example/warehouse/service/AiAgentService.java`
  - 作用/此次修改：AI 示例问题与本地规则回答同步使用真实商品/货架名称。
- `backend/src/main/java/com/example/warehouse/service/AuthService.java`
  - 作用/此次修改：后端业务服务层，处理库存、入库、出库、预警或 AI 逻辑，本次未修改。
- `backend/src/main/java/com/example/warehouse/service/DashboardService.java`
  - 作用/此次修改：后端业务服务层，处理库存、入库、出库、预警或 AI 逻辑，本次未修改。
- `backend/src/main/java/com/example/warehouse/service/DeepSeekClient.java`
  - 作用/此次修改：后端业务服务层，处理库存、入库、出库、预警或 AI 逻辑，本次未修改。
- `backend/src/main/java/com/example/warehouse/service/InboundService.java`
  - 作用/此次修改：后端业务服务层，处理库存、入库、出库、预警或 AI 逻辑，本次未修改。
- `backend/src/main/java/com/example/warehouse/service/OutboundService.java`
  - 作用/此次修改：后端业务服务层，处理库存、入库、出库、预警或 AI 逻辑，本次未修改。
- `backend/src/main/java/com/example/warehouse/service/WarehouseEventPublisher.java`
  - 作用/此次修改：后端业务服务层，处理库存、入库、出库、预警或 AI 逻辑，本次未修改。
- `backend/src/main/java/com/example/warehouse/service/WarehouseService.java`
  - 作用/此次修改：后端业务服务层，处理库存、入库、出库、预警或 AI 逻辑，本次未修改。
- `backend/src/main/java/com/example/warehouse/service/WarningService.java`
  - 作用/此次修改：后端业务服务层，处理库存、入库、出库、预警或 AI 逻辑，本次未修改。
- `backend/src/main/java/com/example/warehouse/util/PathPlanner.java`
  - 作用/此次修改：后端 Java 源码文件，本次未修改。
- `backend/src/main/resources/application.yml`
  - 作用/此次修改：JDBC 增加 UTF-8/utf8mb4 连接参数和 Hikari SET NAMES 初始化。
- `db/encoding-check.sql`
  - 作用/此次修改：新增编码检查脚本，用于判断乱码是否来自数据库写入。
- `db/init.sql`
  - 作用/此次修改：合并真实仓库/货架/商品数据、维修表、utf8mb4 编码保险。
- `db/reset-demo.sql`
  - 作用/此次修改：合并真实演示数据重置、维修表重置、utf8mb4 编码保险。
- `db/upgrade-realistic-demo-data.sql`
  - 作用/此次修改：旧数据库升级到真实演示名称的脚本，并加入 utf8mb4 编码保险。
- `docker-compose.full.yml`
  - 作用/此次修改：完整 Docker Compose，启动前端、后端、MySQL、Redis，本次未修改。
- `docker-compose.yml`
  - 作用/此次修改：基础 Docker Compose，只启动 MySQL/Redis 等基础服务，本次未修改。
- `docs/api-test.http`
  - 作用/此次修改：项目说明文档，本次未修改。
- `docs/config-audit-report.md`
  - 作用/此次修改：项目说明文档，本次未修改。
- `docs/feature-mapping.md`
  - 作用/此次修改：同步真实名称和功能映射。
- `docs/java21-database-notes.md`
  - 作用/此次修改：项目说明文档，本次未修改。
- `docs/model-sources.md`
  - 作用/此次修改：项目说明文档，本次未修改。
- `docs/optimized-for-vscode-docker.md`
  - 作用/此次修改：项目说明文档，本次未修改。
- `docs/spring-ai-and-embedding-upgrade.md`
  - 作用/此次修改：项目说明文档，本次未修改。
- `docs/sql-table-change-report.md`
  - 作用/此次修改：同步真实名称和 SQL 表说明。
- `docs/step-by-step-guide.md`
  - 作用/此次修改：同步真实名称和新手操作说明。
- `frontend/.dockerignore`
  - 作用/此次修改：前端 Vue/Vite/Nginx/Docker 配置文件，本次未修改。
- `frontend/.env.example`
  - 作用/此次修改：前端 Vue/Vite/Nginx/Docker 配置文件，本次未修改。
- `frontend/Dockerfile`
  - 作用/此次修改：前端 Vue/Vite/Nginx/Docker 配置文件，本次未修改。
- `frontend/index.html`
  - 作用/此次修改：增加 UTF-8 双保险 meta。
- `frontend/nginx.conf`
  - 作用/此次修改：增加 charset utf-8 和常见文本类型编码声明。
- `frontend/package-lock.json`
  - 作用/此次修改：前端 Vue/Vite/Nginx/Docker 配置文件，本次未修改。
- `frontend/package.json`
  - 作用/此次修改：前端 Vue/Vite/Nginx/Docker 配置文件，本次未修改。
- `frontend/src/App.vue`
  - 作用/此次修改：前端 Vue 源码文件，本次未修改。
- `frontend/src/api/http.js`
  - 作用/此次修改：前端 API 封装文件，负责调用后端接口，本次未修改。
- `frontend/src/components/DashboardChart.vue`
  - 作用/此次修改：前端通用组件或 3D 组件，本次未修改。
- `frontend/src/components/MetricCards.vue`
  - 作用/此次修改：前端通用组件或 3D 组件，本次未修改。
- `frontend/src/components/Warehouse3D.vue`
  - 作用/此次修改：3D Canvas 文字使用更完整中文字体 fallback。
- `frontend/src/main.js`
  - 作用/此次修改：前端 Vue 源码文件，本次未修改。
- `frontend/src/style.css`
  - 作用/此次修改：增加中文字体 fallback，减少页面中文显示异常。
- `frontend/src/views/AiAssistant.vue`
  - 作用/此次修改：AI 页面占位提示和示例按钮改为真实商品名称。
- `frontend/src/views/Dashboard.vue`
  - 作用/此次修改：前端页面视图组件，本次未修改。
- `frontend/src/views/Inbound.vue`
  - 作用/此次修改：前端页面视图组件，本次未修改。
- `frontend/src/views/Login.vue`
  - 作用/此次修改：前端页面视图组件，本次未修改。
- `frontend/src/views/Outbound.vue`
  - 作用/此次修改：前端页面视图组件，本次未修改。
- `frontend/src/views/Warning.vue`
  - 作用/此次修改：前端页面视图组件，本次未修改。
- `frontend/vite.config.js`
  - 作用/此次修改：前端 Vue/Vite/Nginx/Docker 配置文件，本次未修改。
- `start-dev-mac-linux.sh`
  - 作用/此次修改：一键启动脚本，本次未修改。
- `start-dev-windows.bat`
  - 作用/此次修改：一键启动脚本，本次未修改。
- `start-full-docker-windows.bat`
  - 作用/此次修改：一键启动脚本，本次未修改。

## 已统一的端口

| 服务 | 端口 | 说明 |
|---|---:|---|
| 前端 Vite 开发服务 | 5173 | 本地开发访问地址 |
| 后端 Spring Boot | 8080 | 后端 API 与 WebSocket |
| MySQL | 3306 | 数据库 |
| Redis | 6379 | 缓存/扩展能力 |
| Docker 前端 Nginx | 80 | 完整 Docker 部署访问入口 |

## 已统一的数据库配置

```yaml
数据库类型：MySQL
数据库名：smart_warehouse
用户名：root
密码：123456
字符集：utf8mb4
排序规则：utf8mb4_unicode_ci
后端连接：jdbc:mysql://localhost:3306/smart_warehouse?useUnicode=true&characterEncoding=UTF-8&connectionCollation=utf8mb4_unicode_ci&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true&useSSL=false
```

## 已统一的访问路

| 功能 | 地址 |
|---|---|
| 前端本地开发 | http://localhost:5173 |
| 后端健康检查 | http://localhost:8080/api/health |
| 仓库大屏 | http://localhost:5173/dashboard |
| 入库管理 | http://localhost:5173/inbound |
| 出库管理 | http://localhost:5173/outbound |
| 库存预警 | http://localhost:5173/warnings |
| AI 助手 | http://localhost:5173/ai |
| Docker 完整部署入口 | http://localhost |

## 功能与代码对应表

| 功能 | 前端文件 | 后端文件 | 数据库表 |
|---|---|---|---|
| 登录/注册 | `frontend/src/views/Login.vue` | `AuthController.java`、`AuthService.java` | `app_user` |
| 数字孪生大屏 | `Dashboard.vue`、`Warehouse3D.vue` | `DashboardController.java`、`WarehouseService.java` | `warehouse`、`shelf`、`inventory`、`product` |
| 入库管理 | `Inbound.vue` | `InboundController.java`、`InboundService.java` | `inbound_task`、`inventory` |
| 出库管理 | `Outbound.vue` | `OutboundController.java`、`OutboundService.java`、`PathPlanningService.java` | `outbound_order`、`inventory` |
| 库存预警 | `Warnings.vue` | `WarningController.java`、`WarningService.java` | `warning_record`、`replenishment_task` |
| AI 助手 | `AiAssistant.vue` | `AiController.java`、`AiAgentService.java`、`DeepSeekClient.java` | `inventory`、`warning_record`、`product` |
| 仓库类型修改 | 仓库相关页面/接口调用 | `WarehouseController.java`、`WarehouseMapper.java` | `warehouse` |
| 维修记录 | 当前主要由 SQL 表支撑 | 后续可新增 Controller/Service 页面 | `warehouse_maintenance` |

## 功能的实现思路

系统按照下面这条链路运行：

```text
前端 Vue 页面点击/提交数据
→ frontend/src/api/*.js 调用后端 /api 接口
→ Spring Boot Controller 接收请求
→ Service 执行业务规则
→ MyBatis Mapper 读写 MySQL
→ 返回 JSON 给前端
→ 前端刷新表格、指标、3D 场景或 AI 回答
```

为什么这样做：

- 前端只负责展示和交互，适合比赛演示。
- 后端负责业务判断，逻辑更清楚。
- 数据库保存库存、货架、仓库、预警和任务，便于后续扩展。
- AI Agent 先用本地规则和仓库实时数据模拟 RAG，DeepSeek API 可选接入。

## 功能的实现链条

### 1. 数字孪生仓库大屏

- 这一步要做什么：展示仓库、货架、库存状态、预警状态和 3D 标签。
- 为什么要这样做：比赛展示时比单纯表格更直观。
- 文件链条：
  - `frontend/src/views/Dashboard.vue` 调用 API。
  - `frontend/src/api/warehouse.js` 请求后端。
  - `DashboardController.java` 接收请求。
  - `DashboardService.java` 汇总指标。
  - `WarehouseMapper.java`、`InventoryMapper.java` 查询 `warehouse`、`shelf`、`inventory`、`product`。
  - `Warehouse3D.vue` 根据返回数据绘制 3D 仓库。

### 2. 入库管理

- 这一步要做什么：输入商品和数量，系统推荐合适货架，管理员确认后增加库存。
- 为什么要这样做：体现“AI 建议 + 人工确认”。
- 文件链条：
  - `Inbound.vue` 提交商品和数量。
  - `InboundController.java` 接收请求。
  - `InboundService.java` 根据品类、容量、距离推荐货架。
  - `ShelfMapper.java` 查询货架容量。
  - `InventoryMapper.java` 更新 `inventory`。
  - `inbound_task` 记录入库任务。

### 3. 出库管理

- 这一步要做什么：创建出库订单，查找商品所在货架，生成路径并扣减库存。
- 为什么要这样做：体现路径规划和 AGV/叉车模拟。
- 文件链条：
  - `Outbound.vue` 选择商品和数量。
  - `OutboundController.java` 接收请求。
  - `OutboundService.java` 查库存并生成出库单。
  - `PathPlanningService.java` 生成起点→货架→出口路径。
  - `InventoryMapper.java` 扣减库存。
  - `Warehouse3D.vue` 高亮路径并模拟移动。

### 4. 库存预警

- 这一步要做什么：低于安全库存时生成预警，页面显示红色货架，管理员可确认补货。
- 为什么要这样做：体现数据感知到状态更新的闭环。
- 文件链条：
  - `WarningService.java` 查询库存和安全库存。
  - `WarningMapper.java` 写入/读取 `warning_record`。
  - `Warnings.vue` 显示预警列表。
  - 管理员确认后写入 `replenishment_task`。

### 5. AI Agent 智能助手

- 这一步要做什么：回答库存查询、补货建议、入库推荐、路径规划、异常原因。
- 为什么要这样做：不依赖复杂大模型工程，也能演示“仓库数据 + 智能分析”。
- 文件链条：
  - `AiAssistant.vue` 输入自然语言问题。
  - `AiController.java` 接收问题。
  - `AiAgentService.java` 汇总实时库存和预警上下文。
  - `DeepSeekClient.java` 如果开启 API，则调用 DeepSeek；如果未开启，则使用本地规则回答。
  - `InventoryMapper.java`、`WarningMapper.java`、`ProductMapper.java` 提供数据。

## 代码完整内容

本压缩包已经包含完整代码。你不需要再复制补丁文件，只需要解压整个项目文件夹。

## 运行方法

### 方法一：本地 VS Code 开发运行

建议把完整项目解压到：

```bat
C:\Users\30382\Desktop\3D\10\smart-warehouse-twin-mvp-optimized
```

进入项目目录：

```bat
cd /d C:\Users\30382\Desktop\3D\10\smart-warehouse-twin-mvp-optimized
```

启动 MySQL 和 Redis：

```bat
docker compose up -d mysql redis
```

第一次建库或需要初始化表结构时，执行：

```bat
docker exec -i smart-warehouse-mysql mysql -uroot -p123456 < db\init.sql
```

如果表已存在、只想重置演示数据，执行：

```bat
docker exec -i smart-warehouse-mysql mysql -uroot -p123456 < db\reset-demo.sql
```

启动后端：

```bat
cd backend
mvn spring-boot:run
```

再打开一个终端启动前端：

```bat
cd /d C:\Users\30382\Desktop\3D\10\smart-warehouse-twin-mvp-optimized\frontend
npm install
npm run dev
```

浏览器打开：

```text
http://localhost:5173
```

### 方法二：完整 Docker 运行

```bat
cd /d C:\Users\30382\Desktop\3D\10\smart-warehouse-twin-mvp-optimized
docker compose -f docker-compose.full.yml up -d --build
```

浏览器打开：

```text
http://localhost
```

## 成功后我应该看到什么效果

1. 登录后能进入智慧仓储系统。
2. 仓库名显示为 `上海青浦综合智能仓-1`。
3. 货架显示为 `冷链鲜食货架-F01`、`日用百货货架-S01`、`电子配件防静电柜-E01` 等真实名称。
4. 商品显示为 `每日鲜语低温鲜牛奶950ml`、`心相印茶语抽纸6包装`、`小米Redmi Buds 6耳机` 等真实名称。
5. AI 页面示例问题不再显示旧的 `纯牛奶库存在哪`，而是使用真实商品。
6. 中文不应再出现乱码；如果只在数据库返回字段处乱码，运行 `db/encoding-check.sql` 检查。
7. 如果 VS Code 仍出现 MSSQL 红线，说明是 SQL Server 插件在误判，不是 MySQL 脚本错误。

## 常见报错怎么解决

### 1. VS Code 提示 `owner: mssql` 或 `if 附近有语法错误`

原因：SQL Server 插件把 MySQL 文件当成 MSSQL 检查。

解决：在当前工作区禁用 `SQL Server (mssql)` 插件，或把 `.sql` 语言模式改成普通 `SQL`。

### 2. 页面商品名、仓库名乱码

先执行：

```sql
use smart_warehouse;
source db/encoding-check.sql;
```

如果数据库里已经乱码，重新执行：

```bat
docker exec -i smart-warehouse-mysql mysql -uroot -p123456 < db\reset-demo.sql
```

### 3. `Table 'smart_warehouse.xxx' doesn't exist`

原因：还没有执行建表脚本。

解决：

```bat
docker exec -i smart-warehouse-mysql mysql -uroot -p123456 < db\init.sql
```

### 4. `mvn` 不是内部或外部命令

原因：Maven 没有配置到系统 PATH。

解决：在 VS Code 中安装 Maven for Java 并使用 Spring Boot Dashboard，或安装 Maven 后重新打开终端。

### 5. 前端依赖安装失败

先删除旧依赖后重装：

```bat
cd frontend
rmdir /s /q node_modules
rmdir /s /q node_modules\.vite
npm install
npm run dev
```

# SQL 表结构修改说明

本完整版本保留原有表，并新增/强化以下内容：

1. `app_user`：用户名限制纯英文和特殊字符；权限为 0/1/2；注册时间和权限修改时间保留。
2. `warehouse`：仓库 id 从 1 开始；仓库货柜 id 与 `shelf.id` 外键绑定；仓储类型限制为生鲜、小件商品、大件商品、电子产品、贵重物品。
3. `shelf`：`code` 作为前端展示用的真实货架/货柜名称。
4. `product`：商品名改为真实商品名称；SKU 增加唯一约束。
5. `inventory`：记录商品在某货架某层的数量。
6. `warehouse_maintenance`：新增维修表，字段包括设备名称、设备 id、维修时间、维修人员 id、维修方法、维修结果。
7. `warning_record`：记录低库存预警和补货建议。
8. `replenishment_task`：管理员确认预警后生成补货任务。

完整程序结构已在“项目的结构”章节列出。
