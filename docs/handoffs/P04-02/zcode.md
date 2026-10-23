# P04-02 · 实现可重复执行的数据库种子导入 · ZCode 独立预验收

- **Task ID**：`P04-02`（phase 4 `database-seed`，owner `A`，出口 Gate `G04`）
- **本角色**：ZCode，独立预验收（不覆盖 DSH 开发身份；不签收任何 Gate）
- **判定**：**BLOCKED**
- **候选**：工作根 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，与 DSH 同一项目、同一文件状态；本仓库**无 `.git`**，revision 为内容哈希（自扰动，见 §9）
- **记录**：本文件；结构化证据 `artifacts/handoffs/P04-02/zcode/{evidence.json,precheck.json}`（同内容）；原始日志 `artifacts/handoffs/P04-02/zcode/logs/`（全部 UTF-8）
- **DSH 报告**：`docs/handoffs/P04-02/dsh.md` 与 `artifacts/handoffs/P04-02/dsh/evidence.json` **原样保留，未修改**（含其记录中的错误行，见缺陷 `Z-D5`）

## 1. 结论

**P04-02 无可验收候选，判定 BLOCKED。** DSH 的 BLOCKED 判定**成立**，两条声明依赖确实在签发时即未满足；我另外核实了两条**独立于 Gate 链**的阻断（数据库不可达、回执类型无归属）。同时我发现了 DSH 结构化记录中的**一处硬错误**（`Z-D5`）——它把**已存在**的两份本文档标记为缺失。该错误不改变判定（真实未交付的是 4 个代码/数据/测试交付物，这一点 DSH 是对的），但结构化记录不能用于自动比对。

| 事实 | 我的实测 |
| --- | --- |
| 交付物 | **2/6 存在，且两份都是文档**；**4 个代码/数据/测试交付物 0 个存在**（1 个种子 CLI、1 份目录说明、2 个测试），`data/seed/` 目录本身不存在 |
| 声明依赖 1 `G03` | `artifacts/gates/G03.json` **不存在**；探针 `[FAIL] previous-gate:G03: missing` |
| 声明依赖 2 `P04-01` | DSH 证据 status=`BLOCKED`、2/9 交付物、**0/4 fixture**；无有效 `Z_PRECHECK_PASSED`（本次预验收写入的是 `BLOCKED`）⇒ **无数据可导** |
| 强制命令 1（pytest） | **exit 4**，0/0/0/0 —— 零用例不是验收证据 |
| 强制命令 2（architecture） | exit 0，但**空洞通过**，且与本任务 P04-01 的同名命令输出**逐字节相同**（`logistics_backend.cli` 根本不在扫描范围） |
| 数据库 | **五路探测全部不可达**：`psql`/`pg_ctl` 不在 PATH；Docker 守护进程不可达；5432/5433 无监听（立即 ConnectionRefused）；`TEST_DATABASE_URL` 未设置；`uv.lock` 中 psycopg/sqlalchemy/alembic/asyncpg **0 次命中** |
| 入口与类型 | `logistics_backend.cli` → `ModuleNotFoundError`；`ImportReceipt` 在冻结具名 Schema 表中**无行**，`ScenarioBundle` 无归属（`ARCH-0006` open） |
| 测试用例 | Test Case 1、2 **均未运行**（无 seeder、无数据、无库） |

**本质**：本任务的职责是把 P04-01 生成的场景包导入数据库。**fixture 不存在 ⇒ 无数据可导；数据库不可达 ⇒ 无法验证幂等与回滚；回执类型未冻结 ⇒ 声明输出无法以类型表达。** 故连「部分实现」都不可做，DSH 不手造样本与假 `ImportReceipt` 的处理**正确**。

## 2. 本次验收范围与同一候选确认

- 读取：`docs/prompts/01-foundation/P04-02-database-seed.md`（验收需求）、`TASK_MANIFEST.json` 的 P04-02 条目、`TASK_GRAPH.md:71`、`docs/plan/PHASE_GATES.md:25-26`、`docs/plan/TEST_FIXTURES.md`、`DATA_CONTRACTS.md`、`ARCH-0006`、`tests/conftest.py`、`BARRIER_REMEDIATION_G01_G02_G03.md`、DSH 交接与证据。
- **同一候选确认**：同一工作根、同一命令、同一（缺失的）交付物集合。DSH 的 `input_hashes` **22/22 逐字节复算一致**，`output_hashes` 中 3 份日志 **3/3 一致** ⇒ 两轮之间冻结输入无漂移。
- DSH 的 7 条环境断言我**逐条复现**：`psql`/`pg_ctl` NOT FOUND、docker 守护不可达、`TEST_DATABASE_URL` 未设置、`uv.lock` 无数据库驱动、backend manifest 无数据库依赖、`import logistics_backend.cli` 失败、`artifacts/gates/` 只有 3 个文件。**全部成立**。
- `tests/conftest.py` 的口径我亦核实：缺 `TEST_DATABASE_URL` 时**fail 而非 skip**，且会拒绝 URL 中不含 `test` 的库 ⇒ 关键 skip 不能用来伪造覆盖率，`mock`/SQLite 替代也不被契约允许。DSH 关于「不得关键 skip」的提示与契约一致。

## 3. 独立核验（不读 DSH 总结即可复现）

| 前置 | 我的实测 | 判定 |
| --- | --- | --- |
| `G00` | status=passed | 有效 |
| `G01` | status=**failed**（`failed_checks` = 3 份 P01 预验收 + `codex-review`，四者仍全部缺失） | **无效（阻断）** |
| `G02` | 不存在 | **无效（阻断）** |
| `G03` | 不存在 | **无效（阻断，声明依赖 1）** |
| `P04-01` | status=BLOCKED、2/9、0/4 fixture、无 `Z_PRECHECK_PASSED` | **无效（阻断，声明依赖 2）** |
| `P03-01..04` | 全 BLOCKED、交付文件 0 个存在 | **无效（阻断）** |

**类型缺口（独立于 Gate 链）**：

- `ScenarioBundle`：`ARCH-0006` 仍 `open`，且其正文**已点名本任务**承担同类风险。
- `ImportReceipt`：我**穷尽核对** `DATA_CONTRACTS.md` 具名 Schema 表，**确认无该行**；对照 `CommitReceipt`→P02-03、`JobRequest/JobRef`→P05-03 均有归属，故属**遗漏**而非隐含继承。全仓检索该标识符只命中 `TASK_MANIFEST.json`（P04-02 `model` 字段）、P04-02 Prompt 第 68 行、`ARCH-0006` 正文。本任务白名单**不含领域/DTO 模块** ⇒ 无法在不违反 Constraint 6 的前提下定义回执类型；返回未定义 dict 则违反 Constraint 1。
- 我**认同** DSH 不重复登记 issue 的判断：这与 `ARCH-0006` 是**同一个未决决定**，重复登记会造成重复记录，且需改本任务白名单外的文件。

## 4. 强制命令实跑结果

工作目录统一为仓库根；`uv` 不在 PATH，使用 `tools/bin/uv.exe`（`uv 0.12.13`）；CPython 3.12.10；Windows 11。

| # | 命令 | exit | 结果 | 原始日志 |
| --- | --- | --- | --- | --- |
| 1 | `uv run pytest tests/unit/test_p04_02_database_seed.py tests/integration/test_p04_02_database_seed.py -q` | **4** | `ERROR: file or directory not found`；`no tests ran in 0.00s`（0/0/0/0） | `cmd1-pytest.log` |
| 2 | `uv run python scripts/check_architecture.py` | 0 | `scanned 7 module(s) across 7 layer(s); violations=0`（空洞） | `cmd2-architecture.log` |
| 3 | `uv run python scripts/gates.py --phase 04 --revision auto --out-dir tmp/zcode-p04/probe-g04-p0402` | 1 | `G04: 7/17`；`previous-gate:G03: missing`；两条 cmd1 皆 exit 4；两条 dsh-evidence 非预期；两条 zcode-precheck 状态为 BLOCKED；codex-review 缺失 | `gates-probe-phase04.log` |
| 4 | 环境探针（`psql`/`pg_ctl`/`docker`/`TEST_DATABASE_URL`/TCP 5432,5433/`uv.lock` 驱动扫描/import 探测/`data/seed`） | — | 五路均无 PostgreSQL；`data/seed` 不存在 | `environment-probe.log` |
| 5 | `uv run pytest tests/unit tests/integration -q`（相邻回归基线） | 0 | `187 passed` | `regression-full-pytest.log` |

Log 路径与实时 sha256 见 `artifacts/handoffs/P04-02/zcode/evidence.json` 的 `evidence_logs`（构建脚本现场复算，未手抄）。探针写入 gitignored `tmp/`，**未创建或覆盖任何 Gate 记录**：`artifacts/gates/` 复查仍只有 3 个文件。

**与 DSH 记录的对账**：DSH 探针记 `G04: 5/17`，我实测 **7/17**。差异恰为 P04-02 自身两份文档的检查项——DSH 探针在 21:34:15 时这两份文档确实还不存在（其探针日志原文 `missing docs/implementation/P04-02.md`），而它们在 21:36:27/21:36:46 才写出。**DSH 的 5/17 在其时点诚实**；这正是缺陷 `Z-D5` 的成因（见 §7），也说明其结构化记录是**按写入前的状态**生成的、事后未复算。

## 5. 适用范围检查（本项目 CI 契约 + 阶段适用项）

| 检查 | 来源 | exit | 结果 |
| --- | --- | --- | --- |
| `uv lock --check` | ci.yml | 0 | `Resolved 40 packages in 2ms` |
| `scripts/check_architecture.py --verbose` | ci.yml | 0 | **空洞通过**：7 个模块全是 P01-01 占位；与本任务 P04-01 的同名命令输出**逐字节相同**（sha256 一致） |
| `scripts/check_ownership.py` | P01-02 交付 | 0 | `files=1250 rules=60 violations=0` |
| `scripts/gates.py --phase 01 --check-only` | ci.yml（CI 模式） | 0 | `recorded status=failed`，4 份记录缺失，`gate not signed` |
| `ruff check apps/backend/src packages/*/src tests scripts` | dev 依赖（非强制命令、非 ci.yml） | 1 | 39 errors，**全在既有 P01 文件**，与 P04-02 无关（其路径下无文件） |
| Schema / OpenAPI / 生成客户端一致性 | 任务 Prompt | — | **本轮不适用**：本任务暴露 CLI 入口而非 HTTP 路由，不出 Schema 导出物；seeder 的 schema/hash 校验是它自己的运行时检查，不是生成物一致性 |
| 数据库迁移/回滚检查 | 阶段适用（本任务为数据库任务） | — | **无法运行**：无 PostgreSQL、无迁移工具入锁（属 `Z-D3`） |
| 受影响相邻模块回归 | 验收要求 | 0 | 整套既有套件 187 passed；**无任何 P04-02 用例**，反向印证交付测试缺失 |

## 6. 测试区分力审查与我补充的校验

**测试区分力**：无测试文件可审。不存在「mock 掉核心路径」或「关键 skip 掩盖缺失实现」——pytest exit 4；`tests/conftest.py` 明确 fail 而非 skip。

**我补充的校验与重发验收口径**（均为最有区分力的边界/失败面）：

1. **幂等必须数真实行数**：不接受「status 非空」。应在隔离真实 PostgreSQL 上导入两次，断言第二次 `inserted=0`，且导入前后**库内行数增量为 0**、既有行内容未被覆盖。
2. **回滚必须在数据库层面被观测**：构造「第二个对象 FK 无效」的输入，运行后断言**第一个对象也未落库**且无残留行；不得从 exit code 反推。
3. **`dataset_hash`/`dataset_version` 必须由 fixture 重算**，不得采信记录值（否则幂等判定可被伪造）。
4. **必须专门尝试对非测试库运行**，验证其被拒绝（`tests/conftest.py` 已有「URL 不含 `test` 即拒绝」的口径，实现须与之一致）。
5. **不得以 SQLite 替代、不得标关键 skip**（契约与 conftest 均已如此规定）。
6. **返回类型化 `ImportReceipt`**，不得返回 dict（Constraint 1）。
7. fixture ID 必须稳定；已有关联事实不得被覆盖。

边界与失败面（空集合/重复 ID/非法枚举与单位/负值/溢出/缺失关联/边界时间相等/过期 revision/取消/超时/依赖不可用）**当前全部 UNVERIFIED**，不得读作通过或失败。

## 7. 确定缺陷（含路径与证据）

| ID | 级别 | 缺陷 | 证据 | 归属 | 我是否修复 |
| --- | --- | --- | --- | --- | --- |
| `Z-D1` | **阻断（继承）** | 声明依赖 `G03` 无记录且无法拼装 | `artifacts/gates/` 仅 3 文件；探针 `previous-gate:G03: missing`；P03-01..04 全 BLOCKED | 项目管理侧 + P01-03 | 否 |
| `Z-D2` | **阻断（依赖）** | `P04-01` 未交付任何可用于导入的 fixture | P04-01 证据 `BLOCKED`、2/9、0/4 fixture；`data/scenarios/` 只有 `README.md`；`scripts/generate_scenarios.py` 不存在 | P04-01（屏障修复后） | 否 |
| `Z-D3` | **阻断（环境）** | 无隔离 PostgreSQL 可达，且无数据库驱动入锁 | 五路探测（见 §4 命令 4）：`psql`/`pg_ctl` 缺失、docker 守护不可达、5432/5433 立即 refused、`TEST_DATABASE_URL` 未设置、`uv.lock` 0 命中、backend manifest 无数据库依赖 | 项目管理侧（依赖决定 + Phase 01 环境手册） | 否 |
| `Z-D4` | **阻断（契约缺口）** | `ImportReceipt` 无冻结具名 Schema 行，白名单亦无承载模块 | 穷尽核对 `DATA_CONTRACTS.md` 具名 Schema 表无该行（`CommitReceipt`/`JobRef` 有）；全仓仅 3 处命中；白名单不含领域/DTO 模块 | 契约所有者（与 `ARCH-0006` 同一决定） | 否 |
| `Z-D5` | **中（证据准确性，不改变判定）** | **DSH 结构化记录把已存在的两份本文档标记为缺失，且 0/7 计数与其自身说明矛盾** | `artifacts/handoffs/P04-02/dsh/evidence.json` 的 `deliverable_presence` 将 `docs/implementation/P04-02.md` 与 `reports/P04-02.md` 记为 `false`；两者实际存在（9559 B、13533 B），我的 G04 探针两项均 `present`；其 mtime（21:36:27 / 21:36:46）**早于**记录自身 mtime（21:37:16）⇒ 记录写出时文件已存在，**属写入时即错误而非事后失效**；其 `deliverable_count_note` 定义「7 = 6 个 allow-list 文件 + 本记录 evidence.json」，却又报 0 present，而该 evidence.json 当时已写出 | DSH | 否（他人证据属审计链，原样保留） |
| `Z-D6` | 低（证据可读性） | 1 份 DSH 日志为 **UTF-16-BOM**，标准 UTF-8 工具读不出 | `artifacts/handoffs/P04-02/dsh/logs/gates-probe-phase04.log`（3078 B）；按 UTF-16 解码得 `G04: 5/17`，内容完好，sha256 与 DSH 记录一致 | DSH | 否 |

**正确值**（供 Codex 覆盖 `Z-D5`）：`deliverable_present_count = 2 / 6`（两份文档），**代码/数据/测试交付物 0/4**。`docs/handoffs/P04-02/dsh.md` 第 1 节同样把「6 个交付物」与其括号内实际列举的 4 项混同，措辞需修正。**其实质结论（0 个真实交付物）正确**，故 `Z-D5` 定为中而非阻断。

**我没有发现**：手写样本数据、假 `ImportReceipt`、伪造 `dataset_hash` 或伪造探针记录。DSH 在「不手造数据与回执类型」上的克制是**正确的**。

## 8. 修改前后候选与我改动的代码

- **候选实现：不存在**（0/4）。无「修改前后」可对比。
- **我改动的代码：无。** 我唯一写入的是本职角色的预期产出：
  - `artifacts/handoffs/P04-02/zcode/build-evidence.py`（可复算构建脚本）
  - `artifacts/handoffs/P04-02/zcode/evidence.json`、`precheck.json`（`status="BLOCKED"`）
  - `artifacts/handoffs/P04-02/zcode/logs/`（5 份 UTF-8 原始日志 + 构建日志）
- **未触碰**：`apps/`、`data/`、`tests/`、`uv.lock`、`apps/backend/pyproject.toml`、`docs/architecture/issues/`、`artifacts/gates/`、任何其他任务目录，以及 DSH 的报告与证据（**含其错误行**）。
- 供 Codex 独立查验：`python artifacts/handoffs/P04-02/zcode/build-evidence.py` 可重建记录并逐字段比对。

## 9. 契约版本与 revision

- 契约版本前/后：`1.0.0` → `1.0.0`（未触碰任何冻结契约文件）。
- 输入 hash：我记录 18 项 `verified_input_hashes`（现场复算），与 DSH 记录的共用键**逐项一致**；关键项：P04-02 Prompt `c584c3d6…d9db`、`TEST_FIXTURES.md` `25bd3ca9…927f`、`DATA_CONTRACTS.md` `1c77514c…f422e`、`apps/backend/pyproject.toml` `97c9e247…9344`、`uv.lock` `89f78a20…86c5`、`tests/conftest.py` `b4c985aa…c1f8`、P04-01 DSH 证据 `1bd668e7…c4de`、P04-01 交接 `b08ae850…99ab`。
- revision：内容哈希 `content-sha256:c627d4…f40526`（Phase 04 探针实测）。**自扰动**（覆盖 `artifacts/handoffs/**`、`.mimosa/**`、`tmp/**`），写入本记录即移动标签；`G01.json` 记录的 `ab054daf…` 已过期（`--check-only` 报 STALE）。**不能当 commit id。**
- 输出 hash：无实现产物（0/4）；我的 5 份日志 hash 见 `evidence_logs`。

## 10. 安全检查（基础项）

- **凭据**：任务文档、DSH 记录与仓库源码中**无可疑凭据字面量**；三方 vendored 目录之外无 `.env`/`.pem`/`.p12`/`id_rsa`。本任务的凭据面**只是一个变量名** `TEST_DATABASE_URL`，以 `--database-url-env` **按名传入**而非按值；任何 P04 文档与记录中**都没有其取值**，本环境该变量亦未设置。
- **注入面**：**本轮不适用**——seeder 不存在，无 SQL、无 shell 拼接、无 subprocess。Mimosa 约束（外部输入必须参数绑定；不得拼接/format/f-string 组装 SQL）**未被违反**：本任务没写任何数据访问代码。**重发验收清单已写入该约束**（每一条 insert 必须参数绑定，raw fixture 不得被插值进 SQL 文本）。凭据约束同样保持：只能从环境变量/密钥服务读取，源码、示例、测试都不得出现可用凭据字面量。
- **日志脱敏**：我的日志只含命令输出；无 secret、无个人数据、无模型内部推理。若存在数据库 URL 也会脱敏而非落盘。
- **依赖变化**：无。`uv.lock`（`89f78a20…86c5`）与 `apps/backend/pyproject.toml`（`97c9e247…9344`）与 DSH 审查时逐字节相同，`uv lock --check` exit 0。
- **已知依赖漏洞**：本仓库**尚未建立**漏洞扫描工具（`ci.yml` 无 pip-audit/npm audit 步骤），故**不声称扫描通过**，如实记「未运行」。**可复现漏洞：0；待验证告警：无（无扫描输出可分类）**。未对外部生产目标做任何扫描。

## 11. 已修复 / 未修复 / 未验证

**已修复（我）**：无（无可修的候选代码；仅产出记录与日志）。

**未修复（需他人决策）**：
1. `Z-D1` 屏障：4 份 Phase 01 记录 → 两个项目管理决定 → `P02-01..P02-04` → `G02` → `G03`。
2. `Z-D2` P04-01 fixture。
3. `Z-D3` 数据库环境：**两个项目管理决定须在 `G01` 最终签收之前完成**（允许 psycopg/SQLAlchemy/Alembic 入锁；补 Phase 01 环境手册定义隔离 PostgreSQL 与 `TEST_DATABASE_URL`），否则 `uv.lock`/`apps/backend/pyproject.toml` 变动会迫使 `G01` 重签。
4. `Z-D4` `ImportReceipt` 归属（并入 `ARCH-0006` 同一决定）。
5. `Z-D5`/`Z-D6` DSH 侧修正记录与日志编码。

**未验证（不得改述为通过或失败）**：
- Test Case 1（同数据导入两次 ⇒ 第二次 `inserted=0`）与 Test Case 2（第二个对象 FK 无效 ⇒ 本次全回滚）：**未运行**，且本机**不可能**运行。
- 入口 `python -m logistics_backend.cli.seed --scenario tiny_transport --database-url-env TEST_DATABASE_URL`：模块不存在。
- Business Rules（仅显式测试/演示库、禁止默认清库、fixture ID 稳定、已有关联事实不得被覆盖）与 Algorithm（schema/hash 校验后事务插入、同 hash 返回 `no_change`、内容变化要求新 `dataset_version`）。
- G04 属本任务的断言「同种子二次导入不重复，不清空既有库」：**零证据**。
- Edge Cases 全表；Observability（无种子运行，如实记 0；改报探针实测 4 条命令、合计 1030 ms）。
- 错误码映射（422/409/503）与 `If-Match`/`Idempotency-Key`：本任务暴露 CLI 入口，**不适用**。
- 候选/已验证/已确认三态与 `version_id`/`parent_version_id`/`snapshot_hash`：本任务不产生调度方案，**不适用**。
- 我**未**擅自往 `uv.lock` 添加数据库驱动或安装 PostgreSQL——那会变动 `G01` 的输入并使既有签收失效。

## 12. 给 Codex 的重点风险

1. **不要再下发 Phase 04（或 Phase 05+）**：两个声明依赖在**签发时**即未满足；阻塞集已跨两阶段 7 个 DSH 轮次。处置顺序见 `docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md`。
2. **数据库决定有签收时序陷阱**：`uv.lock` 与 `apps/backend/pyproject.toml` 是 `G01` 的输入。若在 `G01` 最终签收**之后**才加 psycopg 等依赖，`G01` 必须重签（`gates.py --check-only` 已实测会报 STALE）。
3. **`ARCH-0006` + `ImportReceipt` 必须一次定论**：否则重发的 P04-02 必然在「重复定义 Domain Model」与「返回未定义 dict」之间二选一。
4. **`Z-D5`：DSH 结构化记录不可直接用于自动比对**——它把两份存在的文档记为缺失。若下游有自动 diff/断言读取 `deliverable_presence`，先修正或改用本记录的 `2/6`、`0/4`。同时 `gates.py` 读的是 `precheck.json`，不是 `evidence.json`；本任务两份记录内容相同，但 DSH 目录**没有** `precheck.json`（本来也不该由 DSH 提供）。
5. **重发后的验收红线**：在**隔离真实 PostgreSQL** 上跑两次导入并**数真实行数**证明第二次 `inserted=0`；构造 FK 无效输入并核对**第一个对象也未落库、无残留行**；`dataset_hash`/`dataset_version` **由 fixture 重算**；默认**不清库**、只写显式命名的测试/演示库（**专门尝试对非测试库运行以验证拒绝**）；fixture ID 稳定；返回**类型化 `ImportReceipt`**。
6. **集成测试不得以 SQLite 替代或标关键 skip**：`tests/conftest.py` 在缺 `TEST_DATABASE_URL`/psycopg 时本就 fail 而非 skip——若重发后出现 skip，即视为未验收。
7. **`scripts/check_architecture.py` 的 exit 0 不可作证据**：本任务的两个 cmd2 输出与本任务 P04-01 **逐字节相同**，`logistics_backend.cli` 不在扫描范围。

## 13. 我的边界声明

本记录**不签收 Gate**（`signs_gate=false`、`gate_signed=null`），不生成 Codex review。我在本任务中**未修复任何代码**，Codex 无需针对我的改动做回归；只需按 §12 处理阻断决策。我**未**创建 `data/seed/`、样本数据或任何类型的回执定义——那会伪造 G04 依赖的证据。
