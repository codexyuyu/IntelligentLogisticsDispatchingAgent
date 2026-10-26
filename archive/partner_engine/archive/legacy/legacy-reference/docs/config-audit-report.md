# 配置检查与修复记录

本次检查范围包括：后端 Maven 版本配置、Docker 镜像版本、MySQL/Redis 配置、Spring Boot 配置、前端 Vite 配置、Nginx 反向代理路径、README 和启动说明。

## 已统一的版本

| 检查项 | 修复后 |
|---|---|
| Java 编译版本 | 21 |
| 后端 Docker 构建镜像 | maven:3.9-eclipse-temurin-21 |
| 后端 Docker 运行镜像 | eclipse-temurin:21-jre |
| Spring Boot | 3.5.11 |
| MyBatis Spring Boot Starter | 3.0.5 |
| Spring AI | 1.0.3 |
| Node Docker 镜像 | node:22-alpine |
| Nginx Docker 镜像 | nginx:1.27-alpine |
| MySQL Docker 镜像 | mysql:8.4 |
| Redis Docker 镜像 | redis:7.4 |

## 已统一的端口

| 服务 | 端口 |
|---|---|
| 后端 Spring Boot | 8080 |
| 前端 Vite / Docker 前端访问 | 5173 |
| MySQL 外部访问端口 | 3306 |
| Redis | 6379 |
| Docker 内部 Nginx | 80 |

## 已统一的数据库配置

| 配置项 | 值 |
|---|---|
| 数据库名 | smart_warehouse |
| 用户名 | root |
| 密码 | 123456 |
| JDBC 地址 | jdbc:mysql://${MYSQL_HOST:localhost}:${MYSQL_PORT:3306}/${MYSQL_DATABASE:smart_warehouse} |

## 已统一的访问路径

| 类型 | 路径 |
|---|---|
| 前端页面 | http://localhost:5173 |
| 后端接口 | http://localhost:8080/api |
| WebSocket | /ws |
| 前端开发代理 | /api -> http://localhost:8080；/ws -> http://localhost:8080 |
| Docker Nginx 代理 | /api -> backend:8080；/ws -> backend:8080 |

## 本次具体修改

1. 将所有数据库 root 密码从旧值统一为 `123456`。
2. 将 Java 运行/编译配置从不便于新手安装的 Java 25 统一为 Java 21。
3. 将 Docker 全量启动方式的前端访问端口从 `8088` 统一为 `5173`。
4. 将后端端口改为 `${SERVER_PORT:8080}`，既有默认值，又支持环境变量覆盖。
5. 由于很多电脑本机已经安装 MySQL 并占用 `3306`，本项目将 Docker MySQL 的外部访问端口改为 `3306`；容器内部 MySQL 仍是标准 `3306`，Redis `6379`、Spring Boot `8080`、Vite `5173` 保持不变。
6. 修正文档中旧端口、旧密码、旧 Java 版本说明。
7. 新增 `START_HERE.md` 和 Windows/Mac/Linux 启动脚本，方便零基础启动。
8. 将前端 Docker 构建命令从 `npm install` 改为 `npm ci`，与 `package-lock.json` 保持一致，更适合可复现构建。

## 注意事项

如果之前已经启动过旧版本，Docker 数据卷里可能仍保存旧 MySQL 密码。此时请参考 `START_HERE.md` 中的“如果数据库密码改了但仍然连不上”部分处理。
