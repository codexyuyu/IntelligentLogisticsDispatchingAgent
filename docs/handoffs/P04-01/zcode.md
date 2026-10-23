# P04-01 · 生成可手算的合成场景与反例数据 · ZCode 独立预验收

- **Task ID**：`P04-01`（phase 4 `canonical-fixtures`，owner `A`，出口 Gate `G04`）
- **本角色**：ZCode，独立预验收（不覆盖 DSH 开发身份；不签收任何 Gate）
- **判定**：**BLOCKED**
- **候选**：工作根 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，与 DSH 同一项目、同一文件状态；本仓库**无 `.git`**，revision 为 `scripts/gates.py` 的内容哈希（自扰动，见 §9）
- **记录**：本文件；结构化证据 `artifacts/handoffs/P04-01/zcode/{evidence.json,precheck.json}`（同内容）；原始日志 `artifacts/handoffs/P04-01/zcode/logs/`（全部 UTF-8）
- **DSH 报告**：`docs/handoffs/P04-01/dsh.md` 与 `artifacts/handoffs/P04-01/dsh/evidence.json` **原样保留，未修改**

## 1. 结论

**P04-01 无可验收候选，判定 BLOCKED。** 我独立复核了全部载荷性结论，DSH 的 BLOCKED 判定**成立**；但发现 4 条缺陷（1 条为证据可读性、1 条为报告时点效应），其中**没有一条是 DSH 造成的实现缺陷**——因为本任务没有任何实现。

具体：

| 事实 | 我的实测 |
| --- | --- |
| 交付物 | **2/9 存在，且两份都是文档**（`docs/implementation/P04-01.md`、`reports/P04-01.md`，记录 BLOCKED 状态）；**7 个实现/数据/测试交付物 0 个存在** |
| 唯一声明依赖 `G03` | `artifacts/gates/G03.json` **不存在**；Phase 04 探针 `[FAIL] previous-gate:G03: missing`；`G03` 自身 13/28 且 8 条 pass 全为 BLOCKED 文档行 |
| 强制命令 1（pytest） | **exit 4**，`0 passed / 0 failed / 0 skipped` —— 零用例不是验收证据 |
| 强制命令 2（architecture） | exit 0，但**空洞通过**：`--verbose --json` 实测只扫到 7 个未改动的 P01-01 占位 `__init__.py`（每层 1 个） |
| 冻结接口 | `generate_scenario(spec: ScenarioSpec, seed: int) -> ScenarioBundle` **两侧都不可达**：入参类型归 P02-04（未交付），返回类型**无归属**（`ARCH-0006` 仍 `open`） |
| 测试用例 | Test Case 1、2 **均未运行**（fixture、生成器、测试文件都不存在） |

**根因是屏障而非实现质量问题**：`G01 failed` → `G02` 无记录 → `G03` 无记录 → `G04` 无法组装。本任务已耗两轮，两轮结论相同；再次下发前必须先修屏障（`docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md`）。

## 2. 本次验收范围与同一候选确认

- 读取：`docs/prompts/01-foundation/P04-01-canonical-fixtures.md`（验收需求）、`TASK_MANIFEST.json` 的 P04-01 条目、`TASK_GRAPH.md:70`、`docs/plan/PHASE_GATES.md:25-26`、`docs/plan/TEST_FIXTURES.md`、`docs/architecture/DATA_CONTRACTS.md`、`ARCH-0006`、`docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md`、DSH 交接与证据。
- **同一候选确认**：我与 DSH 使用同一工作根；我重跑的每条命令产生的文件状态判断与 DSH 记录一致。DSH 的 `input_hashes` **20/20 逐字节复算一致**，`output_hashes` 中 7 份日志 **7/7 一致**——说明 DSH 审查的冻结输入就是我这次审查的输入，两轮之间无冻结契约漂移。
- 说明：`docs/workflow/README.md` 与 `HANDOFF_CONTRACT.md` **在本仓库中不存在**（已登记为 `ARCH-0004`，`blocking: yes` 阻断 G01）。故本记录格式沿用 `scripts/gates.py` 硬编码路径（`artifacts/handoffs/<task>/zcode/precheck.json`，要求 `status` 与 `verified_input_hashes`）与 P02/P03 既有记录风格。

## 3. 独立核验（不读 DSH 总结即可复现）

| 前置 | 我的实测 | 判定 |
| --- | --- | --- |
| `G00` | `G00.json` status=passed，sha256 `cb1245e2…39a1c` | 有效 |
| `G01` | status=**failed**，sha256 `4383ccac…5c4d4`，`failed_checks` = 3 份 P01 预验收 + `codex-review`，我复核四者仍全部缺失 | **无效（阻断）** |
| `G02` | `G02.json` 不存在 | **无效（阻断）** |
| `G03` | `G03.json` 不存在（`artifacts/gates/` 只有 `G00-checks.log`、`G00.json`、`G01.json`） | **无效（阻断，唯一声明依赖）** |
| `P03-01..04` | DSH 证据与 ZCode precheck **全部 BLOCKED**，声明交付文件 0 个存在 | **无效（阻断）** |
| `P02-04`（类型层） | `artifacts/handoffs/P02-04/dsh/` **目录不存在**；其 zcode precheck = `BLOCKED` | **无效（阻断）** |

**接口不可实现性（独立于 Gate 链的第二阻断）**：

- 入参：`DATA_CONTRACTS.md:81` 原文指派「`ScenarioSpec` 的纯数据形状也在 **P02-04** 定义，P04 负责生成」；实测 `logistics_domain.planning` / `logistics_domain.runtime` 均 `ModuleNotFoundError`，`logistics_domain/__init__.py` 只导出层常量并自述 "Nothing is implemented yet"。
- 返回：我**穷尽核对** `DATA_CONTRACTS.md` 具名 Schema 表，**无** `ScenarioBundle` 行（`CommitReceipt`→P02-03、`JobRequest/JobRef`→P05-03 均有行，故属遗漏而非隐含继承）；`ScenarioBundle` 只出现在 `DATA_CONTRACTS.md:94`、`API_CONTRACT.md:47`、本任务 Prompt 第 90 行的**签名右侧**。`ARCH-0006` 仍 `open`。
- 本任务白名单**不含任何领域类型模块** ⇒ 实现者只能在「重复定义 Domain Model（违反 Constraint 6）」与「返回未定义 dict（违反 Constraint 1）」之间二选一。**即使 G03 签收，本任务仍不可实现。**

## 4. 强制命令实跑结果

工作目录统一为仓库根；`uv` 不在 PATH，使用 `tools/bin/uv.exe`（`uv 0.12.13`）；CPython 3.12.10；Windows 11。

| # | 命令 | exit | 结果 | 原始日志 |
| --- | --- | --- | --- | --- |
| 1 | `uv run pytest tests/unit/test_p04_01_canonical_fixtures.py tests/integration/test_p04_01_canonical_fixtures.py -q` | **4** | `ERROR: file or directory not found`；`no tests ran in 0.00s`（0/0/0/0） | `cmd1-pytest.log` |
| 2 | `uv run python scripts/check_architecture.py` | 0 | `scanned 7 module(s) across 7 layer(s); violations=0`（空洞，见 §5） | `cmd2-architecture.log` |
| 3 | `uv run python scripts/gates.py --phase 04 --revision auto --out-dir tmp/zcode-p04/probe-g04` | 1 | `G04: 7/17`；`previous-gate:G03: missing`；两条 cmd1 皆 exit 4；两条 dsh-evidence 状态非预期；两条 zcode-precheck 缺失；codex-review 缺失 | `gates-probe-phase04.log` |
| 4 | `uv run pytest tests/unit tests/integration -q`（相邻回归基线） | 0 | `187 passed` | `regression-full-pytest.log` |

Log 路径与实时 sha256 见 `artifacts/handoffs/P04-01/zcode/evidence.json` 的 `evidence_logs`（构建脚本复算，未手抄）。命令 3 写入 gitignored `tmp/`，**未创建或覆盖任何 Gate 记录**：`artifacts/gates/` 复查仍只有 3 个文件。

**与 DSH 记录的数字差异（已对账）**：DSH 两轮探针均记 `G04: 5/17`，我实测 **7/17**。差异恰为 P04-02 的两份文档检查项——DSH 的 P04-01 探针在 21:27:57、P04-02 探针在 21:34:15，而 `docs/implementation/P04-02.md`（21:36:27）与 `reports/P04-02.md`（21:36:46）写于其后。**两个数字各自都是诚实的时点快照，不是错报**；仅因 DSH 报告未标注该计数随时点变化，故记为缺陷 `Z-D4`（低）。

## 5. 适用范围检查（本项目 CI 契约 + 阶段适用项）

`uv.lock` 为 `apps/backend/pyproject.toml` 等的冻结输入，均未改动。

| 检查 | 来源 | exit | 结果 |
| --- | --- | --- | --- |
| `uv lock --check` | `.github/workflows/ci.yml` | 0 | `Resolved 40 packages in 2ms` |
| `scripts/check_architecture.py --verbose` | ci.yml | 0 | **空洞通过**：`modules_per_layer = {domain:1, contracts:1, optimization:1, simulation:1, agents:1, evaluation:1, backend:1}`，全部是 P01-01 占位包 |
| `scripts/check_ownership.py` | P01-02 交付 | 0 | `files=1250 rules=60 violations=0` |
| `scripts/gates.py --phase 01 --check-only` | ci.yml（CI 模式） | 0 | `recorded status=failed`，4 份记录缺失，`gate not signed` |
| `ruff check apps/backend/src packages/*/src tests scripts` | pyproject dev 依赖（不在强制命令集、也不在 ci.yml） | 1 | **39 errors，全部落在既有 P01 文件**（`scripts/gates.py` 11、`scripts/check_ownership.py` 7、`tests/*` 14、7 个包 `__init__.py` 各 1）；**无一条属于 P04-01**（本任务未写代码）。属既有欠债，不计入本任务缺陷 |
| Schema / OpenAPI / 生成客户端一致性 | 任务 Prompt | — | **本轮不适用**：本任务只产出文件，不暴露 HTTP 路由、不做 Schema 导出（导出属 P02/P05）。未臆造漂移检查 |
| 受影响相邻模块回归 | 验收要求 | 0 | 本任务未写代码 ⇒ 可跑的回归就是整套既有套件：187 passed，其中**无任何 P04-01 用例**，反向印证交付测试缺失 |

## 6. 测试区分力审查与我补充的独立校验

**测试区分力**：无测试文件可审（不存在）。不存在「mock 掉核心路径」或「关键 skip 掩盖缺失实现」的情形——`pytest` 因文件缺失直接 exit 4，`tests/conftest.py` 亦规定数据库用例在缺 `TEST_DATABASE_URL` 时 **fail 而非 skip**。

**我补充的独立校验（最有区分力的部分）**：本任务无求解器，但它的两条 Test Case 依赖 `TEST_FIXTURES.md` 的**手算 oracle**。我从冻结矩阵出发独立重算全套数值（脚本与输出留档 `tmp/zcode-p04/oracle-arithmetic-check.txt`），结果**全部自洽**：

- `D-A-B-D = 3000+2000+4000 = 9000 m`；反向 `D-B-A-D = 7000+6000+5000 = 18000 m`（注意 `B→A=6000` 而非 2000，与文档一致）
- 行驶 `300+200+400 = 900 s`；A 到/开始/离开 `300/300/360`；B `560/620`；回仓 `1020 s`；`900+120 = 1020 s` 自洽
- 逐段载荷 `800000 → 400000 → 0 g`；成本 `9 km × 100 分/km + 500 分 = 1400 分`
- `A 窗 [350,350]` 变体：A `350/410`、B `610/670`、回仓 `1070 s`；再令 B `latest_start=600` ⇒ 不可行（到达 610）
- W1：无 setup `makespan 20`；完整规则 `A[0,10) setup[10,15) B[15,25) → makespan 25`
- S1：`t10 入库 3 单位 → 峰值 11 > 容量 10`（超容）；`t20 入库 → 8 ≤ 10`（可行）

**结论**：oracle 可独立复现 ⇒ 重发后两条用例**确实可判定**，且我给出的验收口径不依赖 DSH 的自述。边界与失败面（空/重复/非法枚举与单位/负值/溢出/缺失关联/边界时间相等/过期 revision/取消/超时/依赖不可用）**当前全部 UNVERIFIED**，不得读作通过或失败。

## 7. 确定缺陷（含路径与证据）

| ID | 级别 | 缺陷 | 证据 | 归属 | 我是否修复 |
| --- | --- | --- | --- | --- | --- |
| `Z-D1` | **阻断（继承）** | 唯一声明依赖 `G03` 无记录且无法拼装 | `artifacts/gates/` 仅 3 文件；Phase 04 探针 `previous-gate:G03: missing`；P03-01..04 全 BLOCKED 且交付文件 0 个存在；`G01` failed | 项目管理侧 + P01-03 | 否 |
| `Z-D2` | **阻断（契约缺口）** | 冻结接口不可实现：入参类型 `ScenarioSpec` 未交付、返回类型 `ScenarioBundle` 无归属、白名单无承载模块 | `DATA_CONTRACTS.md:81/94`、`API_CONTRACT.md:47`、Prompt:90、`ARCH-0006` open、`P02-04` 无 dsh 证据且 precheck BLOCKED、两个 `logistics_domain.*` 模块 `ModuleNotFoundError` | 契约所有者 + Phase 02 | 否 |
| `Z-D3` | 低（证据可读性） | DSH 7 份日志中 **3 份为 UTF-16-BOM**，标准 UTF-8 工具读不出文本 | `r2-gates-probe-phase03.log`（4582 B）、`r2-gates-probe-phase04.log`（3082 B）、`P04-02/.../gates-probe-phase04.log`（3078 B）；DSH 只披露并重存了第 1 轮的 `cmd1-pytest.log`/`cmd2-architecture.log`。**内容完好**：按 UTF-16 解码得 `G03: 13/28`、`G04: 5/17`，且字节数与 sha256 与 DSH 记录**完全一致** | DSH | 否（改写他人证据会破坏审计链） |
| `Z-D4` | 低（报告时点） | DSH 记 `G04: 5/17`，重跑为 `7/17`，差异源于探针后补写 P04-02 文档；报告未标注计数随时点变化 | DSH 两份探针日志时间 21:27:57 / 21:34:15；`P04-02.md` 21:36:27；`reports/P04-02.md` 21:36:46 | DSH | 否（两个数字都诚实，本记录做对账） |

**我没有发现**：手写 fixture 冒充生成产物、把期望方案装入运行实现、伪造 hash、伪造探针记录或未披露的契约改动。DSH 在「0/7 且刻意不手写 fixture」上的克制是**正确的**——手造 fixture 会伪造 G04 依赖的确定性证据。

## 8. 修改前后候选与我改动的代码

- **候选实现：不存在**（0/7）。因此无「修改前后」可对比——没有候选被修改，也没有被掩盖的问题。
- **我改动的代码：无。** 我唯一写入的是本职角色要求的记录与日志，均在验收白名单之外属**预期产出**：
  - `artifacts/handoffs/P04-01/zcode/build-evidence.py`（可复算构建脚本）
  - `artifacts/handoffs/P04-01/zcode/evidence.json`、`precheck.json`（`status="BLOCKED"`）
  - `artifacts/handoffs/P04-01/zcode/logs/`（4 份 UTF-8 原始日志 + 构建日志）
  - `tmp/zcode-p04/`（gitignored 探针输出与 oracle 复算留档）
- **未触碰**：`scripts/`、`data/`、`tests/`、`docs/architecture/issues/`、`artifacts/gates/`、任何其他任务的交接目录，以及 DSH 的报告与证据（全部保留原哈希）。
- 供 Codex 独立查验：`python artifacts/handoffs/P04-01/zcode/build-evidence.py` 可重建记录并逐字段比对（所有 hash 现场复算）。

## 9. 契约版本与 revision

- 契约版本前/后：`1.0.0` → `1.0.0`（我未触碰任何冻结契约文件；`ARCH-0006` 属登记缺口，不应由本角色单方面改契约）。
- 输入 hash：我记录 18 项 `verified_input_hashes`（现场复算），与 DSH 记录的共用键**逐项一致**；关键项：P04-01 Prompt `64633b4f…edbc`、`TEST_FIXTURES.md` `25bd3ca9…927f`、`DATA_CONTRACTS.md` `1c77514c…f422e`、`TASK_MANIFEST.json` `aa8dfad3…12e5`、`ARCH-0006` `28bd3e76…2a13`、`issues/README.md` `924e579f…3f20`、`G00.json` `cb1245e2…39a1c`、`G01.json` `4383ccac…5c4d4`。
- revision：内容哈希 `content-sha256:c627d4…f40526`（Phase 04 探针实测）。**自扰动**：`compute_revision()` 覆盖 `artifacts/handoffs/**`、`.mimosa/**`、`tmp/**`，写入本记录本身就会移动标签，故只能作文件集指纹，**不能当 commit id**；`G01.json` 记录的 `ab054daf…` 已过期（`--check-only` 亦报 STALE）。
- 输出 hash：无实现产物（0/7）；我的 4 份日志 hash 见 `evidence_logs`。

## 10. 安全检查（基础项）

- **凭据**：本任务相关路径与仓库源码中**无可疑凭据字面量**；`demo/demos` 与 `tmp/package-verification` 的三方 vendored 目录之外的 `.env`/`.pem`/`.p12`/`id_rsa` **不存在**。本任务不涉及凭据。
- **注入面**：**本轮不适用**——交付物不存在，无 SQL、无 shell 拼接、无 subprocess、无 HTTP 边界。参数绑定要求已写入重发验收清单（未来的 fixture 载入器适用）。Mimosa 约束（参数绑定、凭据只从环境/密钥服务读取）**未被违反**：本任务没写任何数据访问代码，文档也未出现可用凭据字面量。
- **日志脱敏**：我的日志只含命令输出；无 secret、无个人数据、无模型内部推理。
- **依赖变化**：无。`uv.lock`（`89f78a20…86c5`）与 `apps/backend/pyproject.toml`（`97c9e247…9344`）与 DSH 审查时逐字节相同，`uv lock --check` exit 0。
- **已知依赖漏洞**：本仓库**尚未建立**漏洞扫描工具（`ci.yml` 无 pip-audit/npm audit 步骤），故**不声称扫描通过**，如实记「未运行」；最近似的 CI 秘密卫生任务在无 `.git` 环境下无法本地复现。**可复现漏洞：0；待验证告警：无（因无扫描输出可分类）**。未对外部生产目标做任何扫描。

## 11. 已修复 / 未修复 / 未验证

**已修复（我）**：无（无可修的候选代码；仅产出记录与日志）。

**未修复（需他人决策，均超出本任务白名单与本角色权限）**：
1. `Z-D1` 屏障：按 `BARRIER_REMEDIATION_G01_G02_G03.md` 写 4 份 Phase 01 记录 → 两个项目管理决定 → 交付 `P02-01..P02-04` → 签 `G02` → 重发并签 `G03`。
2. `Z-D2` 契约：`ARCH-0006` 定论（建议与 P04-02 的 `ImportReceipt` 缺口并入同一决定）。
3. `Z-D3` UTF-16 日志：DSH 侧重存为 UTF-8。
4. `Z-D4` 探针计数：DSH 侧标注为时点值。

**未验证（不得改述为通过或失败）**：
- Test Case 1（`tiny_transport` 最短距离 9000 m）与 Test Case 2（同 seed=42 同 generator version ⇒ 文件 hash 一致）：**未运行**。
- 接口本身、Business Rules（严格使用 `TEST_FIXTURES.md` 精确数据、明确 `synthetic`、稳定 `uuid5`、不得把期望方案装入运行实现）、规范化序列化（与 dict 迭代顺序无关）、生成器版本戳、`invalid_cases.json` 的「唯一触发规则」标注。
- G04 属本任务的断言：「T1/W1/I1/M1 数据 hash 可复现」「反例各有原因」：**零证据**。
- Edge Cases 全表；Observability（无生成器运行，如实记 0；改报探针实测 4 条命令、合计约 1078 ms）。
- 错误码映射（422/409/503）与 `If-Match`/`Idempotency-Key`：本任务无 HTTP 边界，**不适用**（记为不适用而非通过）。
- 我**未**确认 `uv.lock` 是否允许 psycopg 等数据库依赖（属 P04-02/项目管理侧，未越界代决）。

## 12. 给 Codex 的重点风险

1. **不要再下发 Phase 04（或 Phase 05+）**：`G02`、`G03`、`G04` 全未签收；`P04-01` 已耗两轮、两轮结论完全相同，重发只会再产出一份 BLOCKED 记录。先修屏障。
2. **`G01` 只差 4 份记录**：3 份 Phase 01 预验收 + `G01-codex-review.json`。注意重算 hash、写 `precheck.json` **必须为 `Z_PRECHECK_PASSED`** 且现场重算 `verified_input_hashes`，`code_revision` 必须等于写入那一刻（否则 `gates.py` 会报 STALE，我已实测该机制生效）。
3. **`ARCH-0006` 必须在重发前定论**，否则重发必然触发「重复定义 Domain Model / 返回未定义 dict」二选一。同时核对 `ImportReceipt` 是否也缺具名 Schema 行（同一决定）。
4. **重发后的验收红线**：四份 fixture 数值须与 oracle 一致（我已独立复算，全部自洽，尤其 `tiny_transport` 9000 m）；UUID 必须稳定 `uuid5`；序列化必须规范化；生成器必须带**版本戳**；`invalid_cases.json` 每条反例标注**唯一触发规则**；**不得有手写 fixture**。Test Case 2 应由验收方自行跑两次逐字节比对，而非采信单次 hash。
5. **`scripts/check_architecture.py` 的 exit 0 不可作证据**（7 个占位模块的空洞通过）；它无法发现本任务要防的「跨边界传未定义 dict」。
6. **ruff 有 39 条既有告警**（全在 P01 文件）。它不在强制命令集也不在 CI；若后续阶段把它纳入 CI，会立刻红——需在纳入前清理或显式例外，别误记为本任务引入。
7. **DSH 的 3 份 UTF-16 探针日志**（`Z-D3`）会让 grep/diff 类自动比对漏读它们；若下游有自动证据校验，先要求重存为 UTF-8。

## 13. 我的边界声明

本记录**不签收 Gate**（`signs_gate=false`、`gate_signed=null`），不生成 Codex review，不代替 Codex 的独立复查。我在本任务中**未修复任何代码**，因此 Codex 无需针对我的改动做回归；只需按 §12 处理阻断决策。
