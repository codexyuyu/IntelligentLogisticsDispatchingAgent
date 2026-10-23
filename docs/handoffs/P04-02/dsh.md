# P04-02 · 实现可重复执行的数据库种子导入 · DSH 交接

- **Task ID**：`P04-02`（phase 4 `database-seed`，owner `A`，出口 Gate `G04`）
- **计划版本**：1.1.0（任务书）／`TASK_MANIFEST.json` plan_version 1.0.0
- **本角色**：DSH 初步开发 Agent
- **最终状态**：**BLOCKED**
- **签收声明**：本记录不签收任何 Gate，不生成 Codex review，不代表 P04-02 已实现。

## 1. 结论

P04-02 **未开始实现**：6 个白名单交付物（1 个种子 CLI、1 份目录说明、2 个测试）**一个都未创建**，`data/seed/` 目录本身也不存在。

任务书写「理论上已交付且证据有效：`G03、P04-01`」，本轮逐项实测**两项均不成立**：

| 声明依赖 | 实测 | 判定 |
| --- | --- | --- |
| `G03` | `artifacts/gates/G03.json` **不存在**（该目录只有 `G00-checks.log`、`G00.json`、`G01.json`）；探针 `[FAIL] previous-gate:G03: missing artifacts/gates/G03.json`（`G04: 5/17`） | **无效（阻塞）** |
| `P04-01` | `artifacts/handoffs/P04-01/dsh/evidence.json` status=**BLOCKED**（第 2 轮，2/9 且两份均为 BLOCKED 文档）；`artifacts/handoffs/P04-01/zcode/precheck.json` **不存在** ⇒ 无有效 `Z_PRECHECK_PASSED`；`data/scenarios/` 只有 `README.md`，`scripts/generate_scenarios.py` 与四个 fixture 全部缺失 | **无效（阻塞）** |

**另有两条独立阻断**：

- **数据库不可达**：`psql`/`pg_ctl` 不在 PATH；Docker 守护进程 `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`；`TEST_DATABASE_URL` 未设置；`uv.lock` 无 psycopg/sqlalchemy/alembic/asyncpg，`apps/backend/pyproject.toml` 无任何数据库依赖。本任务是**数据库任务**，其集成测试与 G04 的种子幂等断言都需要**真实隔离 PostgreSQL**。
- **入口模块与类型不存在**：`import logistics_backend.cli` → `ModuleNotFoundError`；`packages/*` 与 `apps/backend` 均为 P01-01 占位包（自述 "Nothing is implemented yet"）；`ScenarioBundle` 无归属（`ARCH-0006` open），`ImportReceipt` 在 `DATA_CONTRACTS.md:15-68` 具名 Schema 表中**无行**，而本任务白名单不含任何领域/DTO 模块。

**本质原因**：P04-02 的职责是把 **P04-01 生成的场景包导入数据库**。fixture 不存在 ⇒ 无数据可导；数据库不可达 ⇒ 无法验证幂等与回滚；回执类型未冻结 ⇒ 声明输出无法以类型表达。因此本任务连"部分实现"都不可做。

## 2. 依赖核验（逐项实测，非按文件名认定）

| 前置 | 实测证据 | 判定 |
| --- | --- | --- |
| `G00` | `G00.json` status=passed（`cb1245e2…39a1c`） | 有效 |
| `G01` | status=**failed**（`4383ccac…5c4d4`）；失败项为 3 份 P01 预验收 + `G01-codex-review.json` | **无效（阻塞）** |
| `G02` | `G02.json` **不存在**；探针 `previous-gate:G02: missing` | **无效（阻塞）** |
| `G03` | `G03.json` **不存在**；探针 `previous-gate:G03: missing` | **无效（阻塞，声明依赖 1）** |
| `P04-01` | 证据 status=`BLOCKED`、2/9 交付物、无 ZCode precheck、fixture 0/4 | **无效（阻塞，声明依赖 2）** |
| `P03-01..04` | DSH 证据与 ZCode precheck 全部 `BLOCKED`；交付文件 0 个存在 | **无效（阻塞）** |

## 3. 实际执行的命令与结果

工作目录统一 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`；环境：Windows 11、CPython 3.12.10、`uv 0.12.13`（PATH 上无 `uv`，使用 `tools/bin/uv.exe`）；本仓库**无 `.git`**。

| # | 命令 | exit code | 结果 | 原始日志（sha256，字节） |
| --- | --- | --- | --- | --- |
| 1 | `uv run pytest tests/unit/test_p04_02_database_seed.py tests/integration/test_p04_02_database_seed.py -q` | **4** | `ERROR: file or directory not found: tests/unit/test_p04_02_database_seed.py`；`no tests ran in 0.00s`（0/0/0/0） | `cmd1-pytest.log`（`f6df96e9…9545`，123 B） |
| 2 | `uv run python scripts/check_architecture.py` | 0 | `architecture-layers: scanned 7 module(s) across 7 layer(s); violations=0` | `cmd2-architecture.log`（`5e06f590…9ac6`，77 B） |
| 3 | `uv run python scripts/gates.py --phase 04 --revision auto --out-dir tmp/dsh-p0402/g04` | 1 | `G04: 5/17`；`previous-gate:G03: missing` | `gates-probe-phase04.log`（`37dbe3e0…aebf`，3078 B） |

**环境探针**（不计入强制命令）：`psql`/`pg_ctl` NOT FOUND；`docker version` 失败（daemon 不可达）；`TEST_DATABASE_URL` 未设置；`uv.lock` 无数据库驱动；`import logistics_backend.cli` → `ModuleNotFoundError`。

**命令 2 的诚实标注**：exit 0 是**空洞通过**（7 个模块是未改动的 P01-01 占位包，`logistics_backend.cli` 甚至不在扫描范围），且它**无法**发现本任务真正要防的 Constraint 1 失败模式（"跨边界传未定义 dict"），因为不存在 seeder 与 `ImportReceipt` 类型。**不得**作为验收证据。

命令 3 刻意写入 gitignored `tmp/`，**没有**创建或覆盖任何 Gate 记录。

## 4. 未测试项（禁止读作通过或失败）

- **Test Case 1**：同数据导入两次 ⇒ 第二次 `inserted=0`（无 seeder、无数据、无库）。
- **Test Case 2**：第二个对象 FK 无效 ⇒ 本次全回滚（需真实 PostgreSQL 的 FK 约束）。
- 入口 `python -m logistics_backend.cli.seed --scenario tiny_transport --database-url-env TEST_DATABASE_URL`（`logistics_backend.cli` 不存在）。
- Business Rules：仅显式测试/演示库、禁止默认清库、fixture ID 稳定、已有关联事实不得被覆盖。
- Algorithm：schema/hash 校验后事务插入、同 hash 返回 `no_change`、内容变化要求新 `dataset_version`。
- G04 出口断言中属本任务的「同种子二次导入不重复，不清空既有库」：**完全无证据**。（「T1/W1/I1/M1 数据 hash 可复现」「反例各有原因」属 P04-01。）
- Edge Cases 全表（空集合、重复 ID、非法枚举/单位、负值/整数溢出、缺失关联、边界时间相等、过期 revision、取消/超时、依赖不可用）：**全部 UNVERIFIED**。
- 本任务 Observability 要求的检查通过/失败数、耗时、处理文件数：无种子运行可测量，**如实记 0**；改报 Gate 探针实测（4 条命令、合计 1202 ms）。
- 错误码映射（422/409/503）与 `If-Match`/`Idempotency-Key`：本任务暴露 CLI 入口而非 HTTP 路由，**不适用**。
- 候选/已验证/已确认三态与 `version_id`/`parent_version_id`/`snapshot_hash`：本任务不产生调度方案，**不适用**。

## 5. 类型缺口（`ARCH-0006` + 本轮确认的 `ImportReceipt`）

- `ScenarioBundle`：`ARCH-0006` 仍 `open`；其正文**已点名本任务**（"同类风险也存在于后续引用该返回类型的 `P04-02`（`ScenarioBundle、ImportReceipt`）"）。
- `ImportReceipt`：本轮**穷尽读取** `DATA_CONTRACTS.md:15-68` 的具名 Schema 表，**确认无该行**。对照 `CommitReceipt`→P02-03、`JobRef`→P05-03 均有归属，说明这是**遗漏**而非隐含继承。全仓库 grep `ImportReceipt` 仅命中 `TASK_MANIFEST.json`（P04-02 的 `model` 字段）、P04-02 任务书第 68 行、以及 `ARCH-0006` 正文第 13 行。
- 而 P04-02 白名单**不含任何领域/DTO 模块**，故无法在不违反 Constraint 6（重复定义 Domain Model）的前提下自行定义回执类型；返回未经定义 dict 则违反 Constraint 1。

**本轮刻意未新建 issue 记录**：该缺口与 `ARCH-0006` 属**同一未决决定**，重复登记会造成重复记录，且需修改本任务白名单外的 `docs/architecture/issues/README.md`。已记入 `evidence.json` 的 `ARCH-0007-candidate`，供契约所有者并入同一决定。

## 6. 文件变更

**新建**

- `artifacts/handoffs/P04-02/dsh/evidence.json`
- `artifacts/handoffs/P04-02/dsh/logs/{cmd1-pytest,cmd2-architecture,gates-probe-phase04}.log`
- `docs/handoffs/P04-02/dsh.md`（本文件）
- `docs/implementation/P04-02.md`
- `docs/implementation/reports/P04-02.md`
- `tmp/dsh-p0402/g04/`（非官方探针记录，gitignored）

**修改：无。** 本任务未触碰任何既有文件（含 `docs/architecture/issues/README.md`，理由见 §5）。

**未创建的任务交付物（0/6，刻意）**：`apps/backend/src/logistics_backend/cli/seed.py`、`data/seed/README.md`、两个测试文件。**也没有手写样本数据或假 `ImportReceipt`**——那会伪造 G04 依赖的 `dataset_hash` 与幂等/回滚证据。

## 7. 契约版本与 hash

- 契约版本前/后：`1.0.0` → `1.0.0`（未触碰任何冻结契约文件）。
- 代码 revision：本仓库无 `.git`；本轮探针实测 `content-sha256:611588e4a13f3d2e6e34151a122201e8b49b6fc657b9f9fb0fe085b23ac79dcd`。标签**自扰动**（`compute_revision()` 覆盖 `artifacts/handoffs/**`、`.mimosa/**`、`tmp/**`），历轮已出现七个不同值。
- 输入 hash（关键项）：`P04-02-database-seed.md` = `c584c3d6…d9db`、`TEST_FIXTURES.md` = `25bd3ca9…927f`、`DATA_CONTRACTS.md` = `1c77514c…f422e`、`apps/backend/pyproject.toml` = `97c9e247…9344`、`uv.lock` = `89f78a20…86c5`、`artifacts/handoffs/P04-01/dsh/evidence.json` = `1bd668e7…c4de`。完整 22 项见 `evidence.json`。
- 输出 hash：无实现产物（0/6）；三份日志 hash 见 §3 与 `evidence.json` 的 `output_hashes.check_logs`。
- Gate 证据引用：`G00`（passed）、`G01`（failed）、`G02`/`G03` **均无记录**、`G04` 未签收；出口断言见 `docs/plan/PHASE_GATES.md:25` 与 `:26`。
- 事件日志：未发出 `p04_02.started/completed/rejected`（无任何 P04-02 代码路径被执行）；结构化替代为 `evidence.json` 的 `commands[]` 与三份原始日志。未输出 secret、个人数据或模型内部推理。

## 8. 交给 ZCode 的重点边界与未测试项

本角色状态为 **BLOCKED**，**不请求**本次预验收（交付物 0/6，无候选可审）。

1. **不要再下发 Phase 04 任务**：本任务的两个声明依赖在**签发时**即未满足（`G03` 无记录、`P04-01` BLOCKED 且零 fixture）。阻塞集已跨两阶段 7 个 DSH 轮次。处置顺序见 `docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md`。
2. `ARCH-0006` 需契约所有者定论，并请**一并核对**本记录 §5 的 `ImportReceipt` 具名 Schema 缺口（同一决定）。
3. 待重发后的预验收重点：
   - 在**隔离真实 PostgreSQL** 上跑两次导入，独立核对**真实行数**以证明第二次 `inserted=0`，不接受"status 非空"；
   - 构造第二个对象 FK 无效的输入，核对**第一个对象也未落库**（全回滚）且无残留行；
   - `dataset_hash`/`dataset_version` 必须由 fixture **重算**，不得采信记录值；
   - 默认**不清库**、仅写显式命名测试/演示库（请专门尝试对非测试库运行以验证拒绝）；
   - fixture ID 稳定；返回**类型化 `ImportReceipt`** 而非 dict。
4. 本任务 2 条 manifest 命令中，只有 `cmd1`（pytest）能证明交付物存在与用例通过；`cmd2` 对本任务是**空洞检查**，预验收不得据它判定通过。
5. 集成测试**不得**以 SQLite 替代或标关键 skip；`tests/conftest.py` 在缺 `TEST_DATABASE_URL`/psycopg 时本就 fail 而非 skip。
6. §4 中标为 UNVERIFIED 的全部条目即当前未测试面，不得改述为已通过。

## 9. 建议的下一步动作（按顺序）

1. 按 `docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md` 修复 G01（4 份记录）→ 项目管理侧两个决定（数据库依赖入锁 + 环境手册）→ 交付 `P02-01 → P02-04` → 签 `G02` → 重发并签 `G03`。
2. 重发 `P04-01` 产出四个 fixture 并通过预验收。
3. 契约所有者定论 `ARCH-0006`（并入 `ImportReceipt`）。
4. **然后**才重发 `P04-02`（种子 CLI + 两条用例，在隔离真实 PostgreSQL 上验证幂等与回滚）。
5. **不得**启动 Phase 05 或任何后续阶段：`G02`~`G04` 均未签收。
