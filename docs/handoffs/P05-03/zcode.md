# P05-03 · 实现作业租约、超时取消与受限 worker · ZCode 独立预验收

- **Task ID**：`P05-03`（phase 5 `durable-jobs`，owner `A`，出口 Gate `G05`）
- **本角色**：ZCode，独立预验收（不覆盖 DSH 开发身份；不签收任何 Gate）
- **判定**：**BLOCKED**
- **候选**：工作根 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，与 DSH 同一项目、同一文件状态；本仓库**无 `.git`**，revision 为内容哈希（自扰动）
- **记录**：本文件；结构化证据 `artifacts/handoffs/P05-03/zcode/{evidence.json,precheck.json}`（同内容）；原始日志 `artifacts/handoffs/P05-03/zcode/logs/`（6 份，全部 UTF-8）
- **DSH 报告**：`docs/handoffs/P05-03/dsh.md` 与 `artifacts/handoffs/P05-03/dsh/evidence.json` **原样保留，未修改**
- **读取需求**：`docs/prompts/04-api/P05-03-durable-jobs.md`（**含 3 条强制命令**）

## 1. 结论

**P05-03 无可验收候选，判定 BLOCKED。** DSH 的判定**成立**，我独立复现其全部载荷性结论。

**本次与两个同阶段任务的一处显著差异（值得肯定）**：DSH 这份结构化记录**内部自洽且对自身文档的计数正确**——10 行、分母 10、4 个 present，且 4 行**确实存在于磁盘**（我复核一致）；它**没有**出现 P04-02、P05-01、P05-02 记录中「把已存在的本文档记为缺失」的陈旧行，也**没有**分母与行数不符的问题。这使本任务成为 Phase 05 中唯一"记录可直接与文件系统对账"的一份。唯一保留意见见 `Z-D6`（写入时点 vs 复算时点的同类过程缺口，但结论现在正确，**无需修正**）。

| 事实 | 我的实测 |
| --- | --- |
| 交付物 | 白名单 11 条中 **2 条存在（都是文档）**；**9 个代码/openapi/测试交付物 0 个存在**（`api/jobs.py`、`application/jobs.py`、`persistence/jobs.py`、`worker.py`、`contracts/openapi.json`、2 个测试，以及待增量修改的 `api/router.py`、`bootstrap.py`） |
| 强制命令 1（pytest） | **exit 4**，0/0/0/0 |
| 强制命令 2（architecture） | exit 0，但**空洞通过**：与 P05-01/P05-02 同名命令输出**逐字节相同**；`.api`/`.application`/`.persistence`/`.worker` 均不存在，无法检查本任务特有的三条分层规则 |
| 强制命令 3（export_contracts） | **exit 2**：脚本不存在 ⇒ **连续第三轮同一根因** |
| 声明依赖 | `G04` 无记录；`P05-02` `BLOCKED`（0/8） |
| 两条 Test Case | **均未运行**（无 worker、无租约表、无数据库、无第二进程） |

**四项独立阻断**：待改前置不存在；job 边界类型无落点；`cmd3` 结构性不可能；无 PostgreSQL/驱动/HTTP 客户端。

## 2. 本次验收范围与同一候选确认

- 读取：本任务 Prompt（Interfaces / Test Cases / Edge Cases / Validation Commands）、`TASK_MANIFEST.json`、`TASK_GRAPH.md:82`、`PHASE_GATES.md:27`、`API_CONTRACT.md:33`、`DATA_CONTRACTS.md:57`、`DOMAIN_CATALOG.md:54`、`tests/conftest.py`、DSH 交接与证据。
- **同一候选确认**：同一工作根、同一命令、同一（缺失的）交付物集合。DSH 的 `input_hashes` **28/28 逐字节复算一致**，5 份日志 hash **5/5 一致**。
- Prompt 与 DSH 引述**逐条核对一致**：接口 `JobService.submit(request: JobRequest, key: str) -> JobRef; Worker.run_once() -> WorkOutcome`；Test Case 1（worker 领取后崩溃 ⇒ 租约到期可重领）、Test Case 2（旧 lease 写结果 ⇒ 拒绝且不覆盖新结果）；3 条强制命令。**DSH 未误述验收需求。**

## 3. 独立核验

| 前置 | 我的实测 | 判定 |
| --- | --- | --- |
| `G00` | passed | 有效（全链唯一有效记录） |
| `G01` | **failed**，失败项 4 份记录仍缺失 | **无效（阻断）** |
| `G02`/`G03`/`G04` | **均不存在** | **无效（阻断）** |
| `P05-01` | `BLOCKED` 0/9；`api/router.py`/`bootstrap.py` 不存在 | **无效（阻断）** |
| `P05-02` | `BLOCKED` 0/8；precheck 存在但为 `BLOCKED`（我上一轮所写），非 `Z_PRECHECK_PASSED` | **无效（阻断，声明依赖）** |
| `P03-03`/`P03-04` | precheck 均 `BLOCKED` | **无效（阻断）：SKIP LOCKED 领取、心跳续约、过期租约回收所需的 UoW 与表全不存在** |
| `P02-02`/`P02-03`/`P02-04` | precheck 均 `BLOCKED` | **无效（阻断）** |

**独立复现的环境事实**（`logs/env-probe.log` 原文）：`httpx`/`psycopg`/`psycopg2`/`sqlalchemy`/`alembic`/`asyncpg` **全部缺失**；`fastapi.testclient` 抛需 `httpx2` 的 `RuntimeError`；`logistics_backend.api`/`.application`/`.persistence`/`.worker`/`.bootstrap`、`logistics_domain.jobs`、`logistics_contracts.jobs`/`.dto` **均 `ModuleNotFoundError`**；`apps/backend/src/logistics_backend/` 与 `packages/domain/src/logistics_domain/` **各只有 `__init__.py`**；`uv.lock` 中数据库驱动 **0 处命中**。

**边界类型归属核对**（DSH 称 `WorkOutcome` 等未冻结，我逐条验证）：

| 类型 | 出现次数（`DATA_CONTRACTS.md`+`DOMAIN_CATALOG.md`+`API_CONTRACT.md`） | 结论 |
| --- | --- | --- |
| `JobRequest` / `JobRef` | `DATA_CONTRACTS.md:57` **明确归属 P05-03** | 被指名为本任务所有，但白名单**无 contracts 模块**可承载 |
| `JobKind` / `LeaseToken` / `Deadline` | **各 0 次** | 未冻结；`Deadline` 甚至与本任务 Prompt 的独立进程 deadline 语义相关却无定义 |
| `WorkOutcome` | **0 次** | 由 Prompt 的 Interfaces 行自造，非冻结契约类型 |
| `logistics_contracts._PENDING_APIS` | 只有 `dto`/`mapping`/`export_schema`（P02-04）与 `errors`（P05-01） | **连 job DTO 的待实现占位都没有** |

⇒ 实现者只剩三条路：重复定义边界层（违 Constraint 6）、返回未定义 dict（违 Constraint 1）、或手写生成物（任务书明令禁止）。

## 4. 强制命令实跑结果

| # | 命令 | exit | 结果 | 原始日志 |
| --- | --- | --- | --- | --- |
| 1 | `uv run pytest tests/unit/test_p05_03_durable_jobs.py tests/integration/test_p05_03_durable_jobs.py -q` | **4** | `ERROR: file or directory not found`；0/0/0/0 | `cmd1-pytest.log` |
| 2 | `uv run python scripts/check_architecture.py` | 0 | `scanned 7 module(s) … violations=0`（空洞，与 P05-01/02 逐字节相同） | `cmd2-architecture.log` |
| 3 | `uv run python scripts/export_contracts.py --check` | **2** | 文件不存在 | `cmd3-export-contracts.log` |
| 4 | `uv run python scripts/gates.py --phase 05 --revision auto --out-dir tmp/zcode-p05/probe-g05-p0503` | 1 | `G05: 10/27`；`previous-gate:G04 missing` | `gates-probe-phase05.log` |
| 5 | `uv run pytest tests/unit tests/integration -q` | 0 | `187 passed`（无 P05-03 用例） | `regression-full-pytest.log` |

**三条强制命令中仅 1 条 exit 0，且为空洞通过** ⇒ 本任务**不满足** Acceptance Criteria 第 2 条。

**`G05` 计数对账**：DSH 记 4/27 → 6/27 → 8/27（P05-01/02/03 三轮），我实测 **10/27**。每轮 +2 恰为上一任务两份文档由 missing 变 present；8 → 10 的 +2 是 P05-03 自己的两份文档（写于 00:54:47 / 00:54:59，**晚于**其 00:52:46 的探针）。DSH 的三个数字均为**诚实的时点快照**，非错报。命令 4 写入 gitignored `tmp/`，未创建或覆盖任何 Gate 记录。

## 5. 适用范围检查

| 检查 | exit | 结果 |
| --- | --- | --- |
| `uv lock --check` | 0 | `Resolved 40 packages` |
| `check_architecture.py --verbose` | 0 | 空洞（7 个占位模块） |
| `check_ownership.py` | 0 | `files=1360 rules=60 violations=0` |
| `gates.py --phase 01 --check-only` | 0 | `recorded status=failed`，4 份记录缺失，`gate not signed` |
| `ruff check`（scoped） | 1 | 39 errors，**全在既有 P01 文件**，与 P05-03 无关 |
| **Schema / OpenAPI / 生成客户端一致性** | — | **无法运行且属结构性阻断**；未臆造替代比对 |
| 受影响相邻模块回归 | 0 | 187 passed，无 P05-03 用例 |

## 6. 测试区分力审查与我补充的边界

**测试区分力**：无测试文件可审；不存在 mock 核心路径或关键 skip（`tests/conftest.py` 缺 `TEST_DATABASE_URL`/psycopg 时 **fail 而非 skip**——这一点对本任务尤其关键，因为它排除了用 SQLite 或内存租约表伪装并发边界的可能）。

**我补充的边界与失败面（重发验收口径）**：

1. Test Case 1 必须**真实杀死 worker 进程**，并由**第二个进程**在租约到期后重新领取；「`sleep` 后直接改状态」**不算证据**。
2. Test Case 2 必须以**旧 lease epoch** 写入并证明**被拒绝**，且**核对持久化行**仍保存较新的结果与较新的 epoch（不能只看返回码）。
3. 进程并发默认为 1，**不得**用 FastAPI `BackgroundTasks` 跑重求解，请求线程内不得有长求解。
4. 「取消/超时」与「旧 lease 写结果」**即两条 Test Case**，不得以关键 skip 绕过；取消的终态 CAS 与过期租约回收须各有负例。
5. 重试仅限幂等暂态操作，须有最大次数与 deadline。
6. 边界面全表**当前 UNVERIFIED**。

## 7. 确定缺陷（含路径与证据）

| ID | 级别 | 缺陷 | 证据 | 归属 | 我是否修复 |
| --- | --- | --- | --- | --- | --- |
| `Z-D1` | **阻断（继承）** | `G04` 无记录且无法拼装 | `artifacts/gates/` 仅 3 文件；探针 `previous-gate:G04: missing`；`G01` failed、`G02`/`G03` 无记录；P03/P04 全 BLOCKED | 项目管理侧 + P01-03 | 否 |
| `Z-D2` | **阻断（依赖）** | `P05-02` 未交付，且本任务要扩展的 `api/router.py`/`bootstrap.py`（属 P05-01）也不存在 | `P05-02` 证据 `BLOCKED` 0/8；`api/router.py`/`bootstrap.py` 不存在；`persistence/` 包不存在 ⇒ 无路由表可注册 `GET /jobs/{id}`、`POST /jobs/{id}/cancel`，无组合根可装配 `JobService` | P05-01 → P05-02（屏障修复后） | 否 |
| `Z-D3` | **阻断（契约缺口）** | `JobRequest`/`JobRef` 被契约指名为 P05-03 所有却无承载模块；`JobKind`/`LeaseToken`/`Deadline`/`WorkOutcome` **完全未冻结** | `DATA_CONTRACTS.md:57` 指派 P05-03；白名单不含 contracts/domain 模块；四类型在三份冻结契约中**各 0 次命中**；`_PENDING_APIS` 无 job DTO 占位。**这是第四次命中同一「被指名为所有者却无合法落点」模式**（`ARCH-0006`、P05-01、P05-02、本任务） | 契约所有者（建议与另三处合并为一条架构决定） | 否 |
| `Z-D4` | **阻断（依赖/计划）** | 第 3 条强制命令**连续第三轮**结构性不可能通过 | exit 2；`scripts/export_contracts.py` 不存在（属 P02-04），`contracts/openapi.json` 不存在且禁止手改；同一命令在 P05-01、P05-02 轮次**根因完全相同** | P02-04 + 计划所有者（清单歧义） | 否 |
| `Z-D5` | **阻断（环境）** | 无 PostgreSQL、无驱动、无 HTTP 客户端，两条用例不可执行 | `psql`/`pg_ctl` 缺失、Docker 守护不可达、`TEST_DATABASE_URL` 未设置、`uv.lock` 驱动 0 处；`httpx` 缺失；conftest fail 而非 skip | 项目管理侧（`G01` 最终签收前） | 否 |
| `Z-D6` | **低（过程，无需修正）** | 同一「不复算」过程缺口的边界情形 | 该记录在 00:54:11 断言其自身文档与 `dsh.md`/`evidence.json` 存在，而其中三份在 00:54:34/00:54:47/00:54:59 才写出——即按**预期**而非文件系统核验；**当前全部存在，结论正确**，故与 P04-02/P05-01/P05-02 的"陈旧行"不同，**无需修正** | DSH（过程改进建议） | 否 |

**我没有发现**：硬编码 409/422 或租约行为冒充用例、SQLite/内存租约表/假 worker 冒充真实并发边界、手写 `openapi.json`、伪造 hash 或未披露的契约改动。DSH 在「不造假也不越界替 P05-01/P05-02 实现」上的处理是**正确的**。

## 8. 修改前后候选与我改动的代码

- **候选实现：不存在**（0/9）。无「修改前后」可对比。
- **我改动的代码：无。** 仅写入本职产出：`artifacts/handoffs/P05-03/zcode/{build-evidence.py,evidence.json,precheck.json}` 与 `logs/`（6 份）。
- **未触碰**：`apps/`、`packages/`、`contracts/`、`scripts/`、`tests/`、`uv.lock`、`docs/architecture/issues/`、`artifacts/gates/`，以及 DSH 的报告与证据。
- 供 Codex 查验：`python artifacts/handoffs/P05-03/zcode/build-evidence.py` 可重建并逐字段比对。

## 9. 契约版本与 revision

- 契约版本前/后：`1.0.0` → `1.0.0`（未触碰冻结契约；边界缺口交契约所有者裁决，本任务不做单方面迁移）。
- 输入 hash：16 项 `verified_input_hashes` 现场复算，与 DSH 记录共用键一致。
- revision：`content-sha256:c627d4…f40526`（探针实测，**自扰动**，不能当 commit id；`G01.json` 的 `ab054daf…` 已过期）。
- 输出 hash：无实现产物（0/9）；6 份日志 hash 见 `evidence_logs`。

## 10. 安全检查（基础项）

- **凭据**：无可疑凭据字面量；`TEST_DATABASE_URL` 仅变量名出现，无取值。
- **鉴权/对象范围**：job 端点在 `API_CONTRACT.md` 中为 operator 专属，但**无实现可审** ⇒ 记为**不适用**而非通过。
- **注入面**：**本轮不适用**（无 SQL/无路由/无 subprocess）。重发清单要求 SKIP LOCKED 领取、心跳续约、终态 CAS 等**每一条语句参数绑定**，禁止拼接/`format`/f-string 组装 SQL；重试必须有界。
- **日志脱敏**：日志只含命令输出；无 secret、无个人数据、无模型内部推理。
- **依赖变化**：无；`uv lock --check` exit 0。
- **已知依赖漏洞**：无扫描工具，**不声称扫描通过**，记「未运行」。**可复现 0；待验证告警无**。未对外部生产目标扫描。

## 11. 已修复 / 未修复 / 未验证

**已修复（我）**：无。

**未修复**：`Z-D1`–`Z-D5`（`Z-D6` 为过程建议，无需修正）。

**未验证**：两条 Test Case（崩溃后租约重领、旧 lease 拒绝且不覆盖）；接口 `JobService.submit(...)`/`Worker.run_once()`；HTTP `GET /api/v1/jobs/{id}`、`POST /api/v1/jobs/{id}/cancel`；Business Rules（PostgreSQL 持久化、进程并发 1、不用 `BackgroundTasks` 跑重求解、lease epoch 防旧 worker 写回）；Algorithm（SKIP LOCKED、心跳续约、独立进程 deadline、取消标志与终态 CAS、过期租约回收、重试上限）；`PHASE_GATES.md:27` 的 G05 出口断言；Edge Cases 全表；错误码映射与 typed `TIMEOUT/UNKNOWN/INFEASIBLE`；Logging 事件 `p05_03.*` 未发出；Observability（如实记 0；DSH 报告其指标清单**跨任务越界**，**连续第三个 Phase 05 任务**如此，我确认重叠并把措辞裁决交 Prompt 所有者）；不适用项（三态、`version_id`/`snapshot_hash`）。

## 12. 给 Codex 的重点风险

1. **不要再下发 Phase 05**：两个声明依赖在**签发时**均不成立；`cmd3` 对 Phase 05 **系统性**不可通过（连续三轮）。阻塞集已跨三阶段 10 个 DSH 轮次。
2. **按序推进**：修屏障（4 份 Phase 01 记录）→ 项目管理侧把锁与环境决定**一次做完且排在 `G01` 最终签收之前**（驱动 + 迁移工具 + **HTTP 测试客户端** + 隔离 PostgreSQL + `TEST_DATABASE_URL` + 环境手册）→ `P02-01..P02-04` 并签 `G02` → `P03-01..P03-04` 并签 `G03` → 重发 P04 并签 `G04` → 交付 `P05-01`、`P05-02` → **然后**才重发 `P05-03`。
3. **契约所有者请一次裁决四处同类缺口**（`ARCH-0006`、P05-01、P05-02、本任务的 job 边界类型）。连续四个任务命中同一模式，宜升级为一条架构决定，而非逐任务登记。
4. **请评审侧裁决 Observability 指标跨任务越界**（连续第三个 Phase 05 任务）——`commit_conflicts_total{reason}` 属 P16-03、`http_requests_total` 属 P05-01 的 HTTP 边界。
5. **重发验收红线**：真实杀死 worker 进程并用**第二个进程**证明租约重领；用旧 lease epoch 证明拒绝且**核对持久化行未被覆盖**；确认 `Job`/`JobStatus`/`JobKind`/`LeaseToken`/`Deadline` 与 `JobRequest`/`JobRef`/`WorkOutcome` 全仓**只有一份定义**，`application` 不 import adapters、`bootstrap` 仍为唯一装配点、API 不 import OR-Tools；`cmd3` 必须由**生成器**产出 `openapi.json` 并重跑比对**字节稳定**。
6. **`cmd2` 的 exit 0 不可作证据**（占位包 + 被测模块缺失，三任务输出逐字节相同）。
7. **本任务的 DSH 记录可直接与文件系统对账**（与 P05-01/P05-02 不同）：10 行、分母 10、4 present 且 4 存在。若下游有自动比对，本任务可启用，另两任务需先修正。

## 13. 我的边界声明

本记录**不签收 Gate**（`signs_gate=false`、`gate_signed=null`），不生成 Codex review。我在本任务中**未修复任何代码**；既未创建 `api/router.py`/`bootstrap.py`（属 P05-01），也未创建任何 domain/contracts 模块或手写 `contracts/openapi.json`。
