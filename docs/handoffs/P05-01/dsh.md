# P05-01 · 建立 FastAPI 组合根、错误协议与基础鉴权 · DSH 交接

- **Task ID**：`P05-01`（phase 5 `api-composition`，owner `A`，出口 Gate `G05`）
- **计划版本**：1.1.0（任务书）／`TASK_MANIFEST.json` plan_version 1.0.0
- **本角色**：DSH 初步开发 Agent
- **最终状态**：**BLOCKED**
- **签收声明**：本记录不签收任何 Gate，不生成 Codex review，不代表 P05-01 已实现。

## 1. 结论

P05-01 **未开始实现**：11 个白名单交付物（应用工厂、组合根、路由、错误协议、鉴权依赖、`openapi.json`、导出脚本、两个测试）**一个都未创建**。

任务书写「理论上以下依赖已经交付且证据有效：`G04`」，本轮实测**不成立**：

| 声明依赖 | 实测 | 判定 |
| --- | --- | --- |
| `G04` | `artifacts/gates/G04.json` **不存在**（该目录只有 `G00-checks.log`、`G00.json`、`G01.json`）；探针 `[FAIL] previous-gate:G04: missing artifacts/gates/G04.json`（`G05: 4/27`） | **无效（阻塞）** |
| （其构成任务）`P04-01` | 证据 status=**BLOCKED**（2/9，零 fixture） | **无效（阻塞）** |
| （其构成任务）`P04-02` | 证据 status=**BLOCKED**（0/6） | **无效（阻塞）** |

**三项独立的结构性阻断（即使 G04 签收也不可实施）**：

1. **边界类型无承载者**：`Settings`/`ActorContext`/`ErrorEnvelope`/`HealthResponse` 全仓库**无定义**；`logistics_contracts` 对 `dto`/`errors`/`export_schema` 均抛 `NotImplementedError`（`dto`/`export_schema` 归 P02-04，其 precheck 为 `BLOCKED`）；本任务白名单**不含任何 DTO 模块**。在此定义它们 = 重复定义边界层（Constraint 6）或返回未定义 dict（Constraint 1）。
2. **第 3 条强制命令结构性不可能通过**：`uv run python scripts/export_contracts.py --check` → **exit 2**（`No such file or directory`）。该脚本被任务书列为"预计修改**已有**前置产物"，但它不存在（归属 P02-04）；`contracts/openapi.json`、`contracts/schemas.json` 亦不存在（`contracts/` 只有 `README.md` 与 `changes/README.md`）。
3. **无 HTTP 测试客户端**：`import httpx` → `ModuleNotFoundError`；`fastapi.testclient`/`starlette.testclient` → `RuntimeError: The starlette.testclient module requires the httpx2 package to be installed`。两条 Test Case 都必须在**真实 ASGI 边界**上断言，故在补依赖前无法诚实执行。注意**框架本身在**（fastapi 0.141.1 / starlette 1.6.0 / pydantic 2.13.5），缺的只是测试客户端。

**另有第四项**：Test Case 2 的 ready 探测需要**真实 PostgreSQL** 与 P03 持久化层，而 `psql`/`pg_ctl` 缺失、Docker 守护进程不可达、`TEST_DATABASE_URL` 未设置、`uv.lock` 无 psycopg/sqlalchemy/alembic、`P03-03`/`P03-04` precheck 均为 `BLOCKED`。

## 2. 依赖核验（逐项实测，非按文件名认定）

| 前置 | 实测证据 | 判定 |
| --- | --- | --- |
| `G00` | `G00.json` status=passed（`cb1245e2…39a1c`） | 有效 |
| `G01` | status=**failed**（`4383ccac…5c4d4`）；失败项为 3 份 P01 预验收 + `G01-codex-review.json` | **无效（阻塞）** |
| `G02` | `G02.json` **不存在**；探针 `previous-gate:G02: missing` | **无效（阻塞）** |
| `G03` | `G03.json` **不存在**；探针 `previous-gate:G03: missing` | **无效（阻塞）** |
| `G04` | `G04.json` **不存在**；探针 `previous-gate:G04: missing` | **无效（阻塞，声明依赖）** |
| `P04-01` | 证据 `BLOCKED`（2/9、零 fixture）；无 ZCode precheck | **无效（阻塞）** |
| `P04-02` | 证据 `BLOCKED`（0/6）；无 ZCode precheck | **无效（阻塞）** |
| `P02-04` | precheck `BLOCKED`；`logistics_contracts` 的 `dto`/`export_schema` 抛 `NotImplementedError` | **无效（阻塞）** |
| `P03-03`/`P03-04` | precheck 均 `BLOCKED`（持久化与工作单元、原子版本存储） | **无效（阻塞）** |

## 3. 实际执行的命令与结果

工作目录统一 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`；环境：Windows 11、CPython 3.12.10、`uv 0.12.13`（PATH 上无 `uv`，使用 `tools/bin/uv.exe`）；本仓库**无 `.git`**。

| # | 命令 | exit code | 结果 | 原始日志（sha256，字节） |
| --- | --- | --- | --- | --- |
| 1 | `uv run pytest tests/unit/test_p05_01_api_composition.py tests/integration/test_p05_01_api_composition.py -q` | **4** | 文件不存在；`no tests ran in 0.00s`（0/0/0/0） | `cmd1-pytest.log`（`7e079286…c096e`，125 B） |
| 2 | `uv run python scripts/check_architecture.py` | 0 | `scanned 7 module(s) … violations=0` | `cmd2-architecture.log`（`5e06f590…9ac6`，77 B） |
| 3 | `uv run python scripts/export_contracts.py --check` | **2** | `can't open file '...\scripts\export_contracts.py': [Errno 2] No such file or directory` | `cmd3-export-contracts.log`（`afa41fd4…a4a8`，229 B） |
| 4 | `uv run python scripts/gates.py --phase 05 --revision auto --out-dir tmp/dsh-p0501/g05` | 1 | `G05: 4/27`；`previous-gate:G04 missing` | `gates-probe-phase05.log`（`8cc48077…411f`，4840 B） |

**环境探针**（不计入强制命令）：`httpx` 缺失、`TestClient` 抛出需 `httpx2` 的 `RuntimeError`；`logistics_backend.api/.main/.bootstrap` 均 `ModuleNotFoundError`；`logistics_contracts.dto/.errors/.export_schema` 均 `NotImplementedError`；`psql`/`pg_ctl` 缺失；Docker 守护进程不可达；`TEST_DATABASE_URL` 未设置。

**三条强制命令中只有 1 条 exit 0，且该条为空洞通过** ⇒ 本任务**不满足** Acceptance Criteria 第 2 条（"exit code=0，记录真实测试数量"）。

**命令 2 的诚实标注**：exit 0 是**空洞通过**（7 个模块是未改动的 P01-01 占位包；`bootstrap.py` 与 `api/` 包不存在，故它**无法**检查本任务特有的 Business Rule"仅 bootstrap 装配 adapters""API 不 import OR-Tools"）。**不得**作为验收证据。

命令 4 刻意写入 gitignored `tmp/`，**没有**创建或覆盖任何 Gate 记录。

## 4. 未测试项（禁止读作通过或失败）

- **Test Case 1**：无凭据请求受保护写接口 ⇒ **401**（无 app、无受保护路由、无测试客户端）。
- **Test Case 2**：数据库不可用 ⇒ **ready=503 且 live=200**（无 app、无持久化层、无数据库、无测试客户端）。
- 接口 `create_app(settings: Settings) -> FastAPI; GET /api/v1/health -> HealthResponse`（两个类型与模块均不存在）。
- 错误协议 `ErrorEnvelope` 及其映射（422/409/503/401/403/`INVALID_TRANSITION`/`UNSUPPORTED`）。
- 鉴权（viewer/operator）、body 限额中间件、`trace_id` 贯穿、lifespan 连接管理、**ready 与 live 分离**。
- Business Rules：仅 bootstrap 装配 adapters、API 不 import OR-Tools、开发模式只绑定本机。
- G05 出口断言（`docs/plan/PHASE_GATES.md:27`：API 认证/错误/分页/revision/持久 Job 可验收；杀 worker 后租约可重领；无长求解阻塞请求）——属 Phase 05 整体（P05-01..P05-03），**完全无证据**。
- Edge Cases 全表（空集合、重复 ID、非法枚举/单位、负值/整数溢出、缺失关联、边界时间相等、过期 revision、取消/超时、依赖不可用）：**全部 UNVERIFIED**。
- Observability 四项指标未实现、未发出（无 HTTP 边界可测），如实记 0；并上报其**跨任务越界**（`job_queue_wait_seconds`/`job_lease_expirations_total` 属 P05-03，`commit_conflicts_total{reason}` 属 P16-03，均不在本任务 `Files` 内）。
- 不适用项：本任务不产生调度数据，故候选/已验证/已确认三态、`version_id`/`parent_version_id`/`snapshot_hash` 的正式方案要求、求解 TIMEOUT/UNKNOWN/INFEASIBLE 不适用于本任务自身输出。

## 5. 边界类型与导出物归属缺口（`ARCH-0006` 同类；本轮记为 `ARCH-0008-candidate`）

- 任务书 `Domain Model` 列出 `Settings、ActorContext、ErrorEnvelope、HealthResponse`，但 `DATA_CONTRACTS.md` 具名 Schema 表中**没有任何一行**归属这四者；`logistics_contracts` 以 `NotImplementedError` 明确把 `dto`/`export_schema` 推给 **P02-04**（`BLOCKED`）。
- 任务书把 `scripts/export_contracts.py` 列为"**已有**前置产物"、把 `contracts/openapi.json` 列为产出；但两者**都不存在**。为让 cmd3 通过而手改 `openapi.json` 是任务书**明令禁止**的（"只能运行生成器更新，不得手改"）。
- 本任务白名单不含任何 DTO/领域类型模块。因此实现者只有三条路：重复定义边界层（违 Constraint 6）、返回未定义 dict（违 Constraint 1）、或手写生成物（违任务书明令）。

**本轮刻意未新建 issue 记录**：该缺口在本任务中已是**阻断条件本身**（非"非阻断的设计问题"），且登记需修改本任务白名单外的 `docs/architecture/issues/README.md`。已记入 `evidence.json` 的 `ARCH-0008-candidate`，建议契约所有者与 `ARCH-0006` **合并为同一决定**。

## 6. 文件变更

**新建**

- `artifacts/handoffs/P05-01/dsh/evidence.json`
- `artifacts/handoffs/P05-01/dsh/logs/{cmd1-pytest,cmd2-architecture,cmd3-export-contracts,gates-probe-phase05}.log`
- `docs/handoffs/P05-01/dsh.md`（本文件）
- `docs/implementation/P05-01.md`
- `docs/implementation/reports/P05-01.md`
- `tmp/dsh-p0501/g05/`（非官方探针记录，gitignored）

**修改：无。** 本任务未触碰任何既有文件。特别地：`docs/architecture/issues/README.md` 未改（理由见 §5）；`uv.lock` 与 `apps/backend/pyproject.toml` 未改（加测试客户端/数据库驱动属项目管理侧决定，且二者是 **G01 输入**）；`scripts/export_contracts.py` 未新建（属 P02-04，本任务内新建会与之冲突）；`contracts/openapi.json` **未创建也未手写**。

**未创建的任务交付物（0/11，刻意）**：见 §1。**没有硬编码 401/503 来"通过"两条用例**，也没有引入替代 HTTP 客户端或 SQLite 之类的测试替身。

## 7. 契约版本与 hash

- 契约版本前/后：`1.0.0` → `1.0.0`（未触碰任何冻结契约文件）。
- 代码 revision：本仓库无 `.git`；本轮探针实测 `content-sha256:d9c07f02fc2e4cb3b089102ca4b40210ed634883fd3b4a7ffe5d15ac58897489`。标签**自扰动**（`compute_revision()` 覆盖 `artifacts/handoffs/**`、`.mimosa/**`、`tmp/**`），历轮已出现八个不同值。
- 输入 hash（关键项）：`P05-01-api-composition.md` = `b282fd14…382f`、`API_CONTRACT.md` = `2728f1cf…10b9`、`DATA_CONTRACTS.md` = `1c77514c…f422e`、`contracts/README.md` = `d0a4ea11…335a`、`artifacts/handoffs/P04-01/dsh/evidence.json` = `1bd668e7…c4de`、`artifacts/handoffs/P04-02/dsh/evidence.json` = `64832b85…2e75`。完整 25 项见 `evidence.json`。
- 输出 hash：无实现产物（0/11）；四份日志 hash 见 §3 与 `evidence.json` 的 `output_hashes.check_logs`。
- Gate 证据引用：`G00`（passed）、`G01`（failed）、`G02`/`G03`/`G04` **均无记录**、`G05` 未签收；出口断言见 `docs/plan/PHASE_GATES.md:26` 与 `:27`。
- 事件日志：未发出 `p05_01.started/completed/rejected`（无任何 P05-01 代码路径被执行）；结构化替代为 `evidence.json` 的 `commands[]` 与四份原始日志。未输出 secret、个人数据或模型内部推理。

## 8. 交给 ZCode 的重点边界与未测试项

本角色状态为 **BLOCKED**，**不请求**本次预验收（交付物 0/11，无候选可审）。

1. **不要再下发 Phase 05 任务**：本任务唯一声明依赖 `G04` 在**签发时完全无记录**。阻塞集已跨三个阶段 8 个 DSH 轮次。处置顺序见 `docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md`。
2. 契约所有者：请把 `ARCH-0006` 与 §5 的 HTTP 边界 DTO/OpenAPI 归属缺口**合并裁决**。
3. 请评审侧裁决 Observability 指标跨任务越界（三项属 P05-03/P16-03，不在本任务 `Files` 内）。
4. 重发后的预验收重点：
   - 在**真实 ASGI 边界**上以**真实缺失凭据**触发 **401**（非硬编码），并核对 `ErrorEnvelope` 的 `code`/`trace_id`/`retryable` 字段；
   - 以**真实不可达数据库**证明 **ready=503 且 live=200** 的分离，而非硬编码状态；
   - 确认 `Settings`/`HealthResponse`/`ErrorEnvelope` 全仓库**只有一份定义**、`bootstrap` 是唯一装配点、`api` 包不 import OR-Tools；
   - `cmd3` 必须由**生成器**产出 `contracts/openapi.json`，并重跑比对**字节稳定**；不得手改 JSON；
   - 确认无测试替身进入正式 bootstrap。
5. 本任务 3 条 manifest 命令中，`cmd2` 对本任务是**空洞检查**（占位包 + 缺少被测模块），`cmd1`（exit 4）与 `cmd3`（exit 2）当前均不可通过；预验收不得据 `cmd2` 判定通过。
6. 测试**不得**以替代 HTTP 客户端、SQLite 或关键 skip 冒充真实边界；`tests/conftest.py` 在缺 `TEST_DATABASE_URL`/psycopg 时本就 fail 而非 skip。
7. §4 中标为 UNVERIFIED 的全部条目即当前未测试面，不得改述为已通过。

## 9. 建议的下一步动作（按顺序）

1. 按 `docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md` 修复 G01（4 份记录）→ 项目管理侧把锁与环境决定**一次做完**（数据库驱动 + 迁移工具 + **HTTP 测试客户端** + 隔离 PostgreSQL + `TEST_DATABASE_URL`）→ 交付 `P02-01 → P02-04`（**P02-04 同时提供本任务所需 DTO 与 cmd3 所需的 `scripts/export_contracts.py`**）→ 签 `G02`。
2. 重发并交付 `P03-01 → P03-04` → 签 `G03`。
3. 重发 `P04-01`、`P04-02` → 签 `G04`。
4. 契约所有者定论 DTO/OpenAPI 归属（并入 `ARCH-0006`）。
5. **然后**才重发 `P05-01`（组合根 + 错误协议 + 鉴权 + 两条用例）。
6. **不得**启动 Phase 06 或任何后续阶段：`G02`~`G05` 均未签收。
