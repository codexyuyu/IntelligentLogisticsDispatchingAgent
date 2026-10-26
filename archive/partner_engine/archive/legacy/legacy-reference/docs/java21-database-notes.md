# Java 21 与数据库持久化说明

## Java / JDK 版本

本项目后端已统一为 Java 21：

- `backend/pom.xml` 中 `<java.version>21</java.version>`
- Maven Compiler Plugin 使用 `<release>${java.version}</release>`
- `backend/Dockerfile` 使用 `maven:3.9-eclipse-temurin-21` 和 `eclipse-temurin:21-jre`

本地开发请安装 JDK 21，并确认：

```bash
java -version
mvn -version
```

## 数据库连接配置

当前项目统一使用：

```text
数据库：smart_warehouse
用户名：root
密码：123456
端口：3306
```

这些配置已经同步到：

- `backend/src/main/resources/application.yml`
- `docker-compose.yml`
- `docker-compose.full.yml`
- 本说明文档中的重置命令

## 密码存储

- 新注册用户使用 BCrypt 加密保存密码。
- 早期演示账号仍兼容旧 SHA-256 哈希，避免已有演示数据无法登录。
- 新业务代码不要再新增 SHA-256 密码写入逻辑。

## 数据库数据不丢失

`db/init.sql` 只负责首次建表与插入基础演示数据，已经改为幂等脚本，不再执行 `truncate table`。

Docker Compose 使用命名卷保存 MySQL 数据：

```yaml
volumes:
  mysql-data:
```

只要不执行下面命令，数据库数据不会被清空：

```bash
docker compose down -v
```

`-v` 会删除 MySQL 数据卷，注册用户、库存变化、任务记录都会丢失。

## 旧版本已经创建过 MySQL 数据卷怎么办

MySQL 第一次初始化后，root 密码会写进 Docker 数据卷。之后即使你修改 `docker-compose.yml` 里的密码，旧数据卷里的 root 密码也不会自动变化。

如果你不需要旧数据，可以执行：

```bash
docker compose down -v
docker compose up -d
```

这样会删除旧数据卷，并按当前统一密码 `123456` 重新初始化。

## 如何安全重置演示数据

如确实需要重置演示库存和货架数据，可以手动执行：

```bash
cat db/reset-demo.sql db/init.sql | docker exec -i sw-mysql mysql -uroot -p123456
```

注意：`reset-demo.sql` 默认不清空 `app_user`，避免注册用户丢失。
