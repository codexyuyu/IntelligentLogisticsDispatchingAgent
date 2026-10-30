# Stage A + Stage B 本地运行环境说明

本文件说明如何在本机复现 **2026-10-30 的阶段一（Stage A 后端）与阶段二（Stage B 前端）验收**。
所有步骤只使用 **5434 隔离测试库**；**5433 演示库必须保持停止、不得连接**。

---

## 1. 端口与角色对照

| 组件 | 端口 | 说明 |
| --- | --- | --- |
| `cc_test_pg`（Docker） | 主机 5434 → 容器 5432 | **唯一允许使用的数据库**，库名 `logistics_stage_a_test` |
| `coldchain_demo_20261029-db-1` | 主机 5433 | **演示库，禁止启动与连接** |
| 隔离后端 API | 8100 | 启动时 `DATABASE_URL` 必须指向 5434 |
| 前端 dev server | 5199 | `VITE_API_PROXY` 指向 8100 |
| 前端 UI 验收（Playwright） | — | 驱动本机 Chrome 访问 http://localhost:5199 |

> 避坑：vite 默认绑定 IPv6 的 `localhost`，验收脚本请使用 **`http://localhost:5199`**，
> 用 `127.0.0.1:5199` 会得到 `ERR_CONNECTION_REFUSED`。

---

## 2. 环境变量（不含任何明文口令）

仓库内的 `stage_b_evidence/env_stage_b.example.sh` 是占位符模板：

```bash
cp stage_b_evidence/env_stage_b.example.sh stage_b_evidence/.env.local
# 用编辑器填入本机测试库账号、API Key 与 Chrome 路径
source stage_b_evidence/.env.local
```

必填项：

| 变量 | 用途 |
| --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://<user>:<pwd>@127.0.0.1:5434/logistics_stage_a_test`（alembic 迁移用） |
| `TEST_DATABASE_URL` | 必须与 `DATABASE_URL` **指向同一库**，否则 Stage A 测试会因迁移未生效而失败 |
| `LOGISTICS_SETTINGS_JSON` | 后端 Settings：`mode` / `database_url` / `scope_id` / `credentials[].token_sha256` |
| `API_PORT` | 隔离后端端口，默认 8100 |
| `UV_BIN_DIR` | `uv` 不在 PATH 时指定其目录 |
| `STAGE_B_API_TOKEN` | operator 角色 API Key，UI 脚本登录注入用 |
| `CHROME_PATH` | 本机 Chrome 可执行文件绝对路径（Playwright 未下载自带浏览器时使用） |

### token_sha256 校验

`LOGISTICS_SETTINGS_JSON` 里的 `token_sha256` 必须等于所使用 API Key 的 sha256：

```bash
python -c "import hashlib;print(hashlib.sha256(b'<你的 API Key>').hexdigest())"
```

`mode` 取 `development` 时 Settings 强制要求 `bind_host` 为回环地址。

---

## 3. 一键启动顺序

```bash
# 0) 数据库：确认 5434 在跑、5433 停止
docker ps --format '{{.Names}}\t{{.Status}}' | grep -E 'cc_test_pg|coldchain_demo'

# 1) 迁移到 Stage A head：0012_integration_simulation
export DATABASE_URL=... TEST_DATABASE_URL=...
uv run alembic upgrade head

# 2) 后端依赖 与 前端依赖（首次）
uv sync
npm ci

# 3) 启动 worker（必须，否则集成运行会 503）
bash stage_b_evidence/run_worker.sh &

# 4) 启动隔离后端
bash stage_b_evidence/run_backend.sh &

# 5) 启动前端（代理到隔离后端）
cd apps/frontend && npx vite --port 5199 --strictPort
```

> worker 缺失的典型报错：`dependency_unavailable / job deadline or attempt limit reached`。
> 该失败不可重试（job 已判 failed），需要重新发起一次 integration run。

---

## 4. 验收命令与本次通过记录

| 项目 | 命令 | 2026-10-30 结果 |
| --- | --- | --- |
| 类型检查 + 生产构建 | `npm --workspace @logistics/frontend run build` | exit 0 |
| 前端单元测试 | `npm --workspace @logistics/frontend run test` | 13 文件 / **48 通过**（含 `stageB/api.test.ts` 4 例） |
| Stage A 后端回归 | `uv run pytest --import-mode=importlib tests/integration/test_integration_simulation.py tests/unit/test_integration_simulation_tracks.py` | **8 passed** |
| 浏览器端到端 | `node stage_b_evidence/ui_check.mjs` / `ui_check2.mjs` | 批准路径与拒绝路径各 1 条真实 run |

> pytest 必须使用 `uv run pytest --import-mode=importlib`（仓库 `addopts` 已配置），
> 直接使用 `python -m pytest` 会把仓库根加入 `sys.path`，掩盖真实导入问题。

---

## 5. 零污染核验

验收前后对比以下表，Stage A/B 的模拟操作不应改变其中任何一项
（`events` 仅随模拟自身登记的 `transport_delay` 事件增加）：

```sql
select 'inventory_ledger' t, count(*) from inventory_ledger
union all select 'schedules', count(*) from schedules
union all select 'schedule_versions', count(*) from schedule_versions
union all select 'warehouse_tasks', count(*) from warehouse_tasks
union all select 'events', count(*) from events;
```

2026-10-30 实测：`inventory_ledger / schedules / schedule_versions` 全程为 0，
`warehouse_tasks` 保持 30（幂等导入），`events` 仅因模拟自身事件 +1。

---

## 6. 不在隔离库范围内的事项

- 5433 演示库：全程 `exited`，不接受任何导入或 run；
- OpenAPI 契约自动生成（`contracts:generate`）与旧 `generated.ts` 不兼容问题，仍是后续修复项；
- 车辆中途重新寻路尚未支持，当前批准后采用的是「原地等待 + 后续顺延」。
