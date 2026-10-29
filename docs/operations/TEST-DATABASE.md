# 本机测试数据库

用于在宿主机运行需要真实 PostgreSQL 的 pytest 用例，与应用库 `logistics` 隔离。

## 组成

- `docker-compose.yml` 的 `db` 服务新增 `5433:5432`，只给宿主机测试使用；应用容器仍走 `db:5432`。
- 测试库：`logistics_test`（独立数据库，独立迁移版本）。
- `tests/conftest.py` 要求 `TEST_DATABASE_URL` 存在且 URL 含 `test`，否则直接失败而不是 skip。

## 一键使用

```powershell
# 只准备容器、测试库和迁移
.\scripts\test_database.ps1 -SetupOnly

# 准备后直接跑指定用例
.\scripts\test_database.ps1 tests/integration -q
.\scripts\test_database.ps1 tests/integration/test_p03_03_repositories_and_snapshot.py -q
```

脚本会：启动 `db` 并等待健康 → 缺库时创建 `logistics_test` → 在测试库上执行 `alembic upgrade head` → 设置 `TEST_DATABASE_URL` → 调用 pytest。

## 手工等价命令

```powershell
docker compose up -d --wait db
docker compose exec -T db psql -U logistics -d postgres -c "CREATE DATABASE logistics_test"
$env:DATABASE_URL='postgresql+psycopg://logistics:logistics@127.0.0.1:5433/logistics_test'
.\.venv\Scripts\alembic.exe upgrade head
$env:TEST_DATABASE_URL='postgresql+psycopg://logistics:logistics@127.0.0.1:5433/logistics_test'
.\.venv\Scripts\python.exe -m pytest tests/integration -q
```

## 边界

- 端口 `5433` 只绑定本机，不对局域网开放；凭据是本地开发用的 `logistics/logistics`，不得用于部署。
- 测试库可被用例写入并在事务中回滚；不要把 `TEST_DATABASE_URL` 指向 `logistics` 应用库。
- 该测试库不等于历史 326 实体/979 关系的准备库，也不替代 Gate 的环境验收记录。
