# P05-03 · 实现作业租约、超时取消与受限 worker · DSH 交接

- **Task ID**：`P05-03`（phase 5 `durable-jobs`，owner `A`，出口 Gate `G05`）
- **计划版本**：1.1.0（任务书）／`TASK_MANIFEST.json` plan_version 1.0.0
- **本角色**：DSH 初步开发 Agent
- **最终状态**：**BLOCKED**
- **签收声明**：本记录不签收任何 Gate，不生成 Codex review，不代表 P05-03 已实现。

## 1. 结论

P05-03 **未开始实现**：10 个交付路径中 6 个实现/测试文件（`api/jobs.py`、`application/jobs.py`、`persistence/jobs.py`、`worker.py`、两个测试）**一个都未创建**。

任务书写「理论上以下依赖已经交付且证据有效：`G04、P05-02`」，本轮逐项实测**两项均不成立**：

| 声明依赖 | 实测 | 判定 |
| --- | --- | --- |
| `G04` | `artifacts/gates/G04.json` **不存在**（该目录只有 `G00-checks.log`、`G00.json`、`G01.json`）；探针 `[FAIL] previous-gate:G04: missing artifacts/gates/G04.json`（`G05: 8/27`） | **无效（阻塞，声明依赖 1）** |
| `P05-02` | 证据 status=**BLOCKED**、交付物 **0/9**；`artifacts/handoffs/P05-02/zcode/precheck.json` **不存在** ⇒ 无有效 `Z_PRECHECK_PASSED` | **无效（阻塞，声明依赖 2）** |

**四项独立结构阻断（即使两个依赖都修好也不可实施）**：

1. **待改的前置文件不存在**：任务书把 `api/router.py` 与 `bootstrap.py` 列为"预计修改**已有**前置产物"，但两者是 **P05-01** 的交付物且从未创建（`find apps` 只有 `__init__.py`）。本任务没有路由表可注册 `GET /jobs/{id}`、`POST /jobs/{id}/cancel`，也没有组合根可把 `JobService` 装配进应用。在任务内新建它们等于替 P05-01 实现，并被其后续修改覆盖——正是 Out of Scope 禁止的"改另一所有者实现掩盖集成错误"。
2. **领域/契约/持久化栈不存在**：`logistics_domain.jobs`、`logistics_contracts.jobs`、`logistics_contracts.dto`、`logistics_backend.application`、`.persistence`、`.worker` 全部 `ModuleNotFoundError`。`Job/JobStatus` 的实体归属在 P02-02/P02-03（precheck 全 `BLOCKED`），UoW/幂等/版本存储归属 P03-03/P03-04（全 `BLOCKED`）。SKIP LOCKED 领取、心跳续约、过期租约回收所需的表与工作单元一个都不存在。
3. **第 3 条强制命令结构性不可能通过**：`uv run python scripts/export_contracts.py --check` → **exit 2**（`No such file or directory`）。该脚本属 P02-04，不存在；`contracts/openapi.json` 亦不存在，而任务书明令"`contracts/*.json` 只能运行生成器更新，不得手改"。这与 P05-01、P05-02 两轮的失败**根因完全相同**——连续第三轮。
4. **无隔离 PostgreSQL + 锁内无数据库驱动**：`psql`/`pg_ctl` 不在 PATH；Docker 守护进程不可达；`TEST_DATABASE_URL` 未设置；`uv.lock` 中 psycopg/SQLAlchemy/Alembic/asyncpg **均为 0 处**。`tests/conftest.py:157`/`:176` 在缺 URL 或缺 psycopg 时 **fail 而非 skip**。两条 Test Case 都是 PostgreSQL 并发语义，无真库无法诚实断言。

**另（本任务特有的边界缺口）**：`DATA_CONTRACTS.md:57` 把 `JobRequest / JobRef` **明确归属 P05-03**，但 P05-03 的 `allowed_files` **不含任何 contracts 模块**；`JobKind`/`LeaseToken`/`Deadline` 在 `DATA_CONTRACTS.md` 中**没有任何行**，`WorkOutcome` 在三份冻结契约中**出现 0 次**。实现者因此只剩三条路：重复定义边界层（违 Constraint 6）、返回未定义 dict（违 Constraint 1）、或手写生成物（任务书明令禁止）。

## 2. 依赖核验（逐项实测，非按文件名认定）

| 前置 | 实测证据 | 判定 |
| --- | --- | --- |
| `G00` | `G00.json` status=passed（`cb1245e2…39a1c`） | 有效（全链唯一有效记录） |
| `G01` | status=**failed**（`4383ccac…5c4d4`），失败项恰为 3 份 P01 预验收 + `G01-codex-review.json` | **无效（阻塞）** |
| `G02` | `G02.json` **不存在**；`[FAIL] previous-gate:G02: missing` | **无效（阻塞）** |
| `G03` | `G03.json` **不存在**；`[FAIL] previous-gate:G03: missing` | **无效（阻塞）** |
| `G04` | `G04.json` **不存在**；`[FAIL] previous-gate:G04: missing` | **无效（阻塞，声明依赖 1）** |
| `P05-01` | 证据 `BLOCKED`（0/11）；无 ZCode precheck；`router.py`/`bootstrap.py` 不存在 | **无效（阻塞）** |
| `P05-02` | 证据 `BLOCKED`（0/9）；无 ZCode precheck；`application/master_data.py` 不存在 | **无效（阻塞，声明依赖 2）** |
| `P04-01`/`P04-02` | 证据均 `BLOCKED`（零 fixture / 0 交付） | **无效（阻塞）** |
| `P03-01`..`P03-04` | 证据均 `BLOCKED`；持久化模块不存在 | **无效（阻塞）** |
| `P02-01`..`P02-04` | precheck 均 `BLOCKED`；`logistics_domain.entities`/`logistics_contracts.dto` 抛 `NotImplementedError` | **无效（阻塞）** |

## 3. 实际执行的命令与结果

工作目录统一 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`；环境：Windows 11、CPython 3.12.10、`uv 0.12.13`（PATH 上无 `uv`，使用 `tools/bin/uv.exe`）；本仓库**无 `.git`**。

| # | 命令 | exit code | 结果 | 原始日志（sha256，字节） |
| --- | --- | --- | --- | --- |
| 1 | `uv run pytest tests/unit/test_p05_03_durable_jobs.py tests/integration/test_p05_03_durable_jobs.py -q` | **4** | 文件不存在；`no tests ran in 0.01s`（0/0/0/0） | `cmd1-pytest.log`（`25f2d0c3…4710`，103 B） |
| 2 | `uv run python scripts/check_architecture.py` | 0 | `scanned 7 module(s) … violations=0` | `cmd2-architecture.log`（`cabb9484…7b6e`，74 B） |
| 3 | `uv run python scripts/export_contracts.py --check` | **2** | `can't open file '...\scripts\export_contracts.py': [Errno 2] No such file or directory` | `cmd3-export-contracts.log`（`968035c6…787d`，218 B） |
| 4 | `uv run python scripts/gates.py --phase 05 --revision auto --out-dir tmp/dsh-p0503/g05` | 1 | `G05: 8/27`；`previous-gate:G04 missing` | `gates-probe-phase05.log`（`8e924b9e…1661`，2235 B） |

**环境探针**（不计入强制命令）：`logistics_backend.api/.application/.persistence/.worker/.bootstrap`、`logistics_domain.jobs`、`logistics_contracts.jobs/.dto` 均 `ModuleNotFoundError`；`httpx`/`psycopg`/`psycopg2`/`sqlalchemy`/`alembic`/`asyncpg` 全部缺失（`fastapi 0.141.1`、`pytest 9.1.1` 在）；`psql`/`pg_ctl` 缺失；Docker 守护进程不可达；`TEST_DATABASE_URL` 未设置。

**三条强制命令中只有 1 条 exit 0，且该条为空洞通过** ⇒ 本任务**不满足** Acceptance Criteria 第 2 条。

**命令 2 的诚实标注**：exit 0 是**空洞通过**。`check_architecture.py` 的 `LAYERS` 只扫描 7 个 workspace 源根，被扫到的正是未改动的 P01-01 占位包；`logistics_backend.api`、`.application`、`.persistence`、`.worker` **都不存在**，因此它**无法**检查本任务特有的规则"application 不 import adapters""`DTO→application→UoW→domain→adapter` 链""请求内不跑长求解"。**不得**作为验收证据。

命令 4 刻意写入 gitignored `tmp/`，**没有**创建或覆盖任何 Gate 记录。

**G05 计数变化**：上一轮（P05-02 轮次）为 **6/27**，本轮 **8/27**；增量 **+2 全部来自本任务的 `docs:*` 由 missing 变 present**（纯文档行）。本任务的 3 条命令通过数：`cmd2` 空洞通过，`cmd1`（exit 4）与 `cmd3`（exit 2）失败——与 P05-01/P05-02 轮次完全同型。

## 4. 未测试项（禁止读作通过或失败）

- **Test Case 1**：worker 领取后崩溃 ⇒ 租约到期可重领。**UNVERIFIED**（无 worker、无租约表、无数据库、无第二进程）。
- **Test Case 2**：旧 lease 写结果 ⇒ 拒绝且不覆盖新结果。**UNVERIFIED**（无 lease epoch CAS、无已持久化行）。
- 接口 `JobService.submit(request: JobRequest, key: str) -> JobRef; Worker.run_once() -> WorkOutcome`（六个类型/模块均不存在；`WorkOutcome` 甚至不是冻结契约类型）。
- HTTP：`GET /api/v1/jobs/{id}`、`POST /api/v1/jobs/{id}/cancel`（`API_CONTRACT.md:33`）——无 app、无 router、无 HTTP 测试客户端。
- Business Rules：PostgreSQL 持久化 job、进程并发默认 1、不以 FastAPI BackgroundTasks 跑重求解、lease epoch 防旧 worker 写回。
- Algorithm：SKIP LOCKED 领取、心跳续约、独立进程 deadline、取消标志与终态 CAS、过期租约回收、重试上限。
- Edge Cases 全表（空集合、重复 ID、非法枚举/单位、负值/整数溢出、缺失关联、边界时间相等、过期 revision、取消/超时、依赖不可用）：**全部 UNVERIFIED**。其中"取消/超时"与"旧 lease 写结果"即两条 Test Case。
- Error Handling 映射：`INVALID_INPUT`/422、`INVALID_TRANSITION`、`UNSUPPORTED`、409（版本/资源/幂等冲突）、401/403、503；`TIMEOUT/UNKNOWN/INFEASIBLE` 为 typed 结果而非 500。
- Logging 事件 `p05_03.started/completed/rejected` 与结构化字段（operation、trace_id、输入/输出 hash、schema_version、结果状态、duration_ms、错误码）：**未发出**（无任何 P05-03 代码路径被执行）。
- Observability 四项指标未实现、未发出（如实记 0）；并上报其**跨任务越界**（`commit_conflicts_total{reason}` 属 P16-03；`http_requests_total` 属 P05-01 的 HTTP 边界）。这是**连续第三个 Phase 05 任务**携带同一越界段落。
- G05 出口断言（`docs/plan/PHASE_GATES.md:27`：API 认证/错误/分页/revision/持久 Job 可验收；杀 worker 后租约可重领；无长求解阻塞请求）——属 Phase 05 整体，**完全无证据**。
- 不适用项：本任务自身不产生调度数据，故候选/已验证/已确认三态、`version_id`/`parent_version_id`/`snapshot_hash` 的正式方案要求、求解 `TIMEOUT/UNKNOWN/INFEASIBLE` 不适用于本任务输出（它们适用于它本应持久化的 job payload，而该 payload 无法构建）。

## 5. 边界类型归属缺口（`ARCH-0006` 同类；本轮记为 `ARCH-0010-candidate`）

- `DATA_CONTRACTS.md:57` 把 `JobRequest / JobRef` **归属 P05-03**；`DOMAIN_CATALOG.md:54` 把 `Job` 列为 32 实体之一。但 P05-03 的 `allowed_files` **不含任何 `packages/contracts` 或 `packages/domain` 模块**，唯一可承载边界的白名单文件是 `contracts/openapi.json`，而任务书**明令禁止手改**它。
- `logistics_contracts._PENDING_APIS` 只登记了 `dto`/`mapping`/`export_schema`（P02-04）与 `errors`（P05-01）——**连"待实现登记"里都没有 jobs DTO 的位置**。
- `JobKind`/`LeaseToken`/`Deadline` 在 `DATA_CONTRACTS.md` 具名 Schema 表中**无行**；`WorkOutcome` 在 `DATA_CONTRACTS.md`/`DOMAIN_CATALOG.md`/`API_CONTRACT.md` 中**出现 0 次**——它是任务书 `Interfaces` 自造的名字，不是冻结契约类型。

**这是第四次命中同一"任务被指名为类型所有者、却没有合法落点"模式**（P05-01、P05-02、P05-03、`ARCH-0006`）。该模式已是本仓库最主要的阻断类别。

**本轮刻意未新建 issue 记录**：该缺口在本任务中已是**阻断条件本身**（非"非阻断的设计问题"），且登记需修改本任务白名单外的 `docs/architecture/issues/README.md`。已记入 `evidence.json` 的 `ARCH-0010-candidate`，建议与 `ARCH-0006`、P05-01/P05-02 轮次的同类缺口**合并为一条架构决定**。

## 6. 文件变更

**新建**

- `artifacts/handoffs/P05-03/dsh/evidence.json`
- `artifacts/handoffs/P05-03/dsh/logs/{cmd1-pytest,cmd2-architecture,cmd3-export-contracts,env-probe-modules,gates-probe-phase05}.log`
- `docs/handoffs/P05-03/dsh.md`（本文件）
- `docs/implementation/P05-03.md`
- `docs/implementation/reports/P05-03.md`
- `tmp/dsh-p0503/g05/G05.json`（非官方探针记录，gitignored）

**修改：无。** 本任务未触碰任何既有文件。特别地：`api/router.py` 与 `bootstrap.py` **未创建**（属 P05-01，越界新建会掩盖集成错误）；未创建任何 domain/contracts 模块；`contracts/openapi.json` **未创建也未手写**；`scripts/export_contracts.py` 未新建（属 P02-04）；`uv.lock`/`apps/backend/pyproject.toml` 未改（G01 输入，属项目管理侧决定）；`docs/architecture/issues/README.md` 未改（理由见 §5）；`artifacts/gates/**` 未改。

**未创建的任务交付物（6/10 实现与测试文件，刻意）**：见 §1。**没有硬编码 409/422 或租约行为来"通过"两条用例**，也没有引入 SQLite、内存租约表或假 worker 冒充真实边界。

## 7. 契约版本与 hash

- 契约版本前/后：`1.0.0` → `1.0.0`（未触碰任何冻结契约文件，未提出契约变更——边界缺口属契约所有者裁决，非本任务可做的迁移）。
- 代码 revision：本仓库无 `.git`；本轮探针实测 `content-sha256:6cec84a14861e3c0a2f25e7cf5efbafaa2fa49b861ab1f359d6fa6a716bf5430`。标签**自扰动**（`compute_revision()` 覆盖 `artifacts/handoffs/**`、`.mimosa/**`、`tmp/**`），历轮已出现十个不同值。
- 输入 hash（关键项）：`docs/prompts/04-api/P05-03-durable-jobs.md` = `62f8bf93…38ae`、`API_CONTRACT.md` = `2728f1cf…10b9`、`DATA_CONTRACTS.md` = `1c77514c…f422e`、`DOMAIN_CATALOG.md` = `0c062652…03b1`、`artifacts/handoffs/P05-02/dsh/evidence.json` = `06686907…13fa`、`artifacts/handoffs/P05-01/dsh/evidence.json` = `bb53bde6…01d9`、`TASK_MANIFEST.json` = `aa8dfad3…12e5`。完整 28 项见 `evidence.json`。
- 输出 hash：无实现产物（0/6）；五份日志 hash 见 §3 与 `evidence.json` 的 `output_hashes.check_logs`。
- Gate 证据引用：`G00`（passed）、`G01`（failed）、`G02`/`G03`/`G04` **均无记录**、`G05` 未签收；出口断言见 `docs/plan/PHASE_GATES.md:27`。
- 事件日志：未发出 `p05_03.started/completed/rejected`；结构化替代为 `evidence.json` 的 `commands[]` 与五份原始日志。未输出 secret、完整个人数据或模型内部思维。

## 8. 交给 ZCode 的重点边界与未测试项

本角色状态为 **BLOCKED**，**不请求**本次预验收（实现交付物 0/6，无候选可审）。

1. **不要再下发 Phase 05 任务**：本任务两个声明依赖在**签发时**均不成立；且 `cmd3`（`export_contracts.py --check`）对 Phase 05 各任务**系统性**不可通过——连续三轮同一 exit 2 根因。阻塞集已跨三阶段 10 个 DSH 轮次。处置顺序见 `docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md`。
2. 契约所有者：请把 `ARCH-0006`、P05-01/P05-02 的 HTTP 边界缺口、与本轮 `JobRequest`/`JobRef`（**已被契约指名为 P05-03 所有却无落点**）+ `JobKind`/`LeaseToken`/`Deadline`/`WorkOutcome`（**未冻结**）缺口**合并裁决**。连续四个任务命中同一模式，建议升级为一条架构决定而非逐任务登记。
3. 请评审侧裁决 Observability 指标跨任务越界（连续第三个 Phase 05 任务）。
4. 重发后的预验收重点：
   - 在**隔离真实 PostgreSQL** 上**真实杀死 worker 进程**，证明租约到期后可被**第二个进程**重新领取（非 `sleep` 后直接改状态）；
   - 用**旧 lease epoch** 写入结果时证明被**拒绝**（终态 CAS），且**新结果未被覆盖**（核对行内容与 epoch）；
   - 确认 `Job/JobStatus/JobKind/LeaseToken/Deadline` 与 `JobRequest/JobRef/WorkOutcome` 全仓库**只有一份定义**，且 `application` 不 import adapters、`bootstrap` 仍为唯一装配点、API 不 import OR-Tools；
   - 确认**未**使用 `FastAPI BackgroundTasks` 运行重求解，且请求线程内无长求解；
   - `cmd3` 必须由**生成器**产出 `contracts/openapi.json` 并重跑比对**字节稳定**，不得手改 JSON。
5. 本任务 3 条 manifest 命令中，`cmd2` 对本任务是**空洞检查**（占位包 + 缺少被测模块），`cmd1`（exit 4）与 `cmd3`（exit 2）当前均不可通过；预验收不得据 `cmd2` 判定通过。
6. 测试**不得**以 SQLite、内存租约表、假 worker 或关键 skip 冒充真实并发边界；`tests/conftest.py` 在缺 `TEST_DATABASE_URL`/psycopg 时本就 fail 而非 skip。
7. §4 中标为 UNVERIFIED 的全部条目即当前未测试面，不得改述为已通过。

## 9. 建议的下一步动作（按顺序）

1. 按 `docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md` 修复 G01（4 份记录：3 份 ZCode 预验收 + 1 份 Codex review）→ 项目管理侧把锁与环境决定**一次做完且排在 G01 最终签收之前**（数据库驱动 + 迁移工具 + HTTP 测试客户端 + 隔离 PostgreSQL + `TEST_DATABASE_URL` + 缺失的 Phase 01 环境手册）→ 交付 `P02-01 → P02-04`（**P02-04 同时提供 cmd3 所需的 `scripts/export_contracts.py`**）→ 签 `G02`。
2. 重发并交付 `P03-01 → P03-04`（含 `uow.py`、`idempotency.py`、`version_store.py`）→ 签 `G03`。
3. 重发 `P04-01`、`P04-02` → 签 `G04`。
4. 交付 `P05-01`（组合根/错误协议/鉴权/`router.py`/`bootstrap.py`）与 `P05-02` 并通过预验收。
5. 契约所有者定论 job 边界类型归属（并入 `ARCH-0006`），并给出 `JobRequest`/`JobRef` 的合法承载模块。
6. **然后**才重发 `P05-03`（租约 + 超时取消 + 受限 worker + 两条用例，在隔离真实 PostgreSQL 上验证崩溃重领与旧 lease 拒绝）。
7. **不得**启动 Phase 06 或任何后续阶段：`G02`~`G05` 均未签收。
