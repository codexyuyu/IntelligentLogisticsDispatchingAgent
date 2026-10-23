# P02-03 · ZCode → Codex 独立预验收报告

| 项目 | 值 |
| --- | --- |
| Task ID | `P02-03`（实现任务、版本与优化结果领域模型；Phase 02，负责方 A） |
| 审查角色 | ZCode 独立预验收（**不是**开发方，DSH 的开发身份不覆盖本角色的审查职责） |
| 审查对象 | 仓库当前 candidate（`D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，与 DSH 同一项目、同一候选；本仓库无 `.git`，按整体内容哈希定位） |
| 本角色状态 | **`BLOCKED`** |
| 阶段 Gate | `G02`（未签收，且前置 `G01` 为 `failed`）；**本报告不签收任何 Gate** |
| 证据入口 | `artifacts/handoffs/P02-03/zcode/evidence.json`、`artifacts/handoffs/P02-03/zcode/logs/`（6 份命令日志） |
| 审查时间 | 2026-09-15（本机时区） |

## 0. 结论（先读这一段）

**P02-03 没有任何候选可验收：该任务的全部 6 个 Files 路径在仓库中都不存在，DSH 也未提交本任务的交接（`docs/handoffs/P02-03/dsh.md` 与 `artifacts/handoffs/P02-03/dsh/evidence.json` 均缺失）。**

两个**声明的**前置条件也都不成立：`G01` 状态为 `failed`，`P02-02` 同样零交付（`TASK_GRAPH.md:48` 规定 P02-03 依赖 `G01, P02-02`）。

因此本次不是"实现有缺陷"，而是"无可验收对象"，判定 **`BLOCKED`**。我没有修改任何生产代码、测试或文档（详见第 7 节）。

本任务是 Phase 02 的第 3 个任务，也是**依赖链上被双重阻断**的一个：它既需要 G01 通过（阶段屏障），又需要 P02-02 先交付（同一阶段内顺序依赖）。P02-02 已于本日（2026-09-15 早些时候）被独立预验收为 `BLOCKED`，因此 P02-03 在依赖链上不是"差一点"，而是**上游两格都还空着**。

复核者需要的最小动作：先让 Codex 补齐 `G01` 的 review 与 P01 任务的预验收记录，再由 DSH 依序交付 `P02-01` → `P02-02` → `P02-03`（各自带任务文档、完成报告、DSH 证据与两份测试文件），然后逐个重新提交预验收。

## 1. 目标、白名单与契约核对

- **任务 Prompt 即验收需求**：`docs/prompts/02-domain/P02-03-planning-entities.md`（哈希见 evidence.json 的 `verified_input_hashes`）。
- **白名单（Files）**：`docs/implementation/P02-03.md`、`docs/implementation/reports/P02-03.md`、`packages/contracts/src/logistics_contracts/planning.py`、`packages/domain/src/logistics_domain/planning.py`、`tests/integration/test_p02_03_planning_entities.py`、`tests/unit/test_p02_03_planning_entities.py`。
- **存在性矩阵**：**6/6 缺失（0 存在）**。
- **冻结接口核对**：Prompt 声明的唯一公开入口是
  `ScheduleVersion(parent_version_id: UUID | None, snapshot_id: UUID, tasks: tuple[ScheduleTask, ...])`。
  实测该名字在目标树中**完全不存在**（`grep ScheduleVersion|ScheduleTask|RescheduleResult|OptimizationRequest` 在 `apps/`、`packages/`、`tests/`、`scripts/` 下唯一命中是一行注释 `tests/unit/test_p01_03_migration_governance.py:256`，且该注释只是说明"确认由不可变 ScheduleVersion 生命周期表达"）。
- **依赖核对**（逐项实际检查，不按文件名认定完成）：
  - `G01`：`artifacts/gates/G01.json` 的 `status=failed`，`failed_checks` 缺 `zcode-precheck:P01-01/02/03` 与 `codex-review`。
  - `P02-02`：其 6 个交付路径全缺、DSH 交接缺失、`artifacts/handoffs/P02-02/zcode/precheck.json` 记录为 `BLOCKED`。
  - evidence.json 的 `dependency_presence` 字段给出 10 个依赖产物的存在性：**0/10 存在**。
- **契约文档**：`docs/workflow/README.md`、`HANDOFF_CONTRACT.md` 不存在（既有 `ARCH-0004`，`blocking: yes`，明确写"阻断 G01 签收"）。我按"用户指令 + Gate 执行器硬编码约定"两处落盘（第 8 节）。

## 2. 强制命令实跑结果（原始日志逐条保留）

命令按 `docs/plan/TASK_MANIFEST.json` 的 P02-03 条目执行，工作目录为仓库根，工具链走 `tools/bin/uv.exe`。

| 命令 | 实际结果 | exit code | 日志 |
| --- | --- | --- | --- |
| `uv run pytest tests/unit/test_p02_03_planning_entities.py tests/integration/test_p02_03_planning_entities.py -q` | `ERROR: file or directory not found: tests/unit/test_p02_03_planning_entities.py`；`no tests ran in 0.00s` | **4** | `logs/cmd1-pytest.log` |
| `uv run python scripts/check_architecture.py` | `architecture-layers: scanned 7 module(s) across 7 layer(s); violations=0` | **0** | `logs/cmd2-architecture.log` |

**第二条命令的 exit 0 不构成通过证据**：它扫到的 7 个模块仍是 P01-01 的空壳 `__init__.py`（每个包 1 个），`violations=0` 只是因为本任务没有新增任何 domain 代码。这是"零用例/零新增即通过"的假信号，验收时不能引用。

**未执行项（如实记录，不臆造成功）**：

- `npm ci`、前端工作区测试、`npm run test:e2e:list`：本轮**未重跑**——P02-03 的 Files 不涉及任何前端文件，重跑对本次结论没有增量信息。相关缺陷 D3/D4 沿用 2026-09-14 的实跑证据，并在 evidence.json 中显式标注 `reverified_this_pass: false`，不冒充本轮结果。
- `uv run python scripts/gates.py --phase 02 --revision auto`：**未写入官方记录**。改用 `--out-dir tmp/zcode-g02-dryrun-p3` 的非官方沙箱运行，以免预验收动作污染 `artifacts/gates/G02.json`，也避免以任何形式代签 Gate。沙箱结果：`G02: 5/27 checks passed`。

## 3. 需求/用例覆盖情况

| 需求项（P02-03 Prompt） | 状态 |
| --- | --- |
| Objective / Files 交付对应 | **未交付**（0/6 文件） |
| Test Case 1：`status=TIMEOUT` 且 `candidate=null` → 合法失败结果 | **无法验证**（无实现、无测试） |
| Test Case 2：`parent_version_id` 指向自身 → 拒绝 | **无法验证**（无实现、无测试） |
| 12 个实体（TransportTask…RescheduleResult）字段/状态/生命周期 | **未实现** |
| 版本内容不可变、lineage 无环、result 无 incumbent 时 candidate 为空 | **未实现** |
| 稳定 `task_id` 与 `version_id` 分离；候选/已验证/已确认分别表达 | **未实现** |
| domain 不导入框架（分层约束） | 当前 `violations=0`，但属空壳状态，不能代表交付 |
| Unit + Integration 两条测试命令零用例视为未验收 | 触发（0 用例，exit 4） |

用例覆盖率 **0/2**。按 Prompt"命令零用例或关键skip视为未验收"，本任务在任何解释下都不成立。

**独立复核（可复现，见 `logs/probe-interfaces.log`）**：直接探测本任务冻结的两个模块面：

```text
import logistics_domain.planning              -> ModuleNotFoundError: No module named 'logistics_domain.planning'
getattr(logistics_domain, 'planning')         -> AttributeError: module 'logistics_domain' has no attribute 'planning'
import logistics_contracts.planning           -> ModuleNotFoundError: No module named 'logistics_contracts.planning'
getattr(logistics_contracts, 'planning')      -> AttributeError: module 'logistics_contracts' has no attribute 'planning'
```

这里有一个**与 P02-02 不同的细节**，值得 P01-01 的负责人注意（已登记为 D9）：P01-01 为"未交付能力"设计了一个失败即报的注册表 `_PENDING_APIS`，但**两份注册表都没有登记 `planning`**：

```text
logistics_domain._PENDING_APIS keys    = ['entities', 'ids', 'ports', 'states', 'units']      # 无 planning
logistics_contracts._PENDING_APIS keys  = ['dto', 'errors', 'export_schema', 'mapping']        # 无 planning
```

注意 P02-02 的 `entities` **被登记了**，而 P02-03 的 `planning` 没有。后果是：探测 P02-03 能力的人得到的是裸 `AttributeError`/`ModuleNotFoundError`，而不是 P01-01 刻意设计的"未实现 + 责任人"提示。这不会造成静默错误（模块确实不存在，调用必然失败），只是**所有权提示不一致**，属观察项。

## 4. 相邻回归与工程基础检查（当前候选）

| 检查 | 命令 | 结果 | 日志 |
| --- | --- | --- | --- |
| 全量测试回归 | `uv run pytest -q` | **187 passed / 0 failed / 0 skipped**，exit 0 | `logs/regression-pytest.log` |
| 所有权/迁移检查 | `uv run python scripts/check_ownership.py --json` | `passed=true`，`violations=[]`，`default_owner_fallbacks=[]`，930 文件扫描，exit 0 | `logs/baseline-checks.log` |
| 依赖锁一致性 | `uv lock --check` | exit 0 | `logs/baseline-checks.log` |
| 冻结安装 | `uv sync --frozen` | exit 0 | `logs/baseline-checks.log` |
| Phase 02 Gate 沙箱运行 | `gates.py --phase 02 --out-dir tmp/zcode-g02-dryrun-p3` | exit 1，`G02: 5/27`；`P02-03-cmd1` exit 4；`P02-03` 的 DSH 证据/任务文档/报告/ZCode 记录全缺；`previous-gate:G01 status=failed` | `logs/gates-phase02-sandbox.log` |

（`gates.py --phase 02 --check-only` 在从未签收的 Gate 上是**空操作**：打印 "nothing signed yet" 并 exit 0。**exit 0 不代表 Phase 02 就绪**，这点容易误读，已在给 Codex 的风险项中列出。）

## 5. 确定缺陷清单（含路径与复现）

### D1 · P02-03 零交付【阻断本任务】

- 证据：第 1 节存在性矩阵（6/6 缺失）；`logs/cmd1-pytest.log`（exit 4）；`logs/gates-phase02-sandbox.log` 中 `P02-03-cmd1: exit_code=4`、`dsh-evidence:P02-03: missing`、`docs:docs/implementation/P02-03.md: missing`、`docs:docs/implementation/reports/P02-03.md: missing`；`logs/probe-interfaces.log`。
- 影响：本任务无候选，无法做任何实质预验收（不变性、lineage 无环、TIMEOUT/INFEASIBLE 语义、失败副作用均无对象）。
- 归属：DSH / P02-03。

### D2 · 两个前置均未满足【阻断本任务】

- `G01` 未通过：`status=failed`，缺 `zcode-precheck:P01-01/02/03` 与 `codex-review`；`PHASE_GATES.md` 写明 G01 失败阻塞"Phase 02及以后"。
- `P02-02` 未交付：其全部 6 个交付路径、DSH 交接、任务文档均缺失；`artifacts/handoffs/P02-02/zcode/precheck.json` 记录为 `BLOCKED`；`packages/domain/src/logistics_domain/` 下仍只有 P01-01 的 `__init__.py` 空壳。
- `TASK_GRAPH.md:48` 规定 `P02-03` 依赖 `G01, P02-02`；evidence.json 的 `dependency_presence` 实测 **0/10 依赖产物存在**。
- 影响：即使 P02-03 立刻交付，也不满足"前置证据有效"的开工前提；按 Prompt"若前置缺失/失败，报告具体阻断，禁止跳 Gate"。

### D3 · 前端工作区声明了测试脚本但未安装 vitest【非阻断 P02-03，属 P01-01 范围】

- `apps/frontend/package.json` 声明 `"test": "vitest run"`，但该包**没有任何 `dependencies`/`devDependencies`**；`apps/frontend/vitest.config.ts`、`apps/frontend/src/test/setup.ts` 却存在。
- 复现（2026-09-14 实跑）：`npm --workspace @logistics/frontend run test --if-present` → `'vitest' is not recognized...`，**exit 1**。
- 影响：`.github/workflows/ci.yml:95` 的 "Frontend tests" 是必跑步骤，`--if-present` 只在脚本缺失时跳过，此处脚本存在 → **CI 的 frontend job 必然失败**。
- 本轮**未重跑**（P02-03 不涉及前端），证据沿用上轮，已在 evidence.json 标注 `reverified_this_pass: false`。

### D4 · `npm run test:e2e:list` 以非零退出，但 CI 当作必过步骤【非阻断 P02-03，属 P01-01/P01-02 范围】

- 复现（2026-09-14 实跑）：`Error: No tests found / Total: 0 tests in 0 files`，**exit 1**；`ci.yml:98` 的 "List end-to-end specs" 是必跑步骤。
- `playwright.config.ts` 注释已说明"无 spec 时列出 0 个用例是合法的"，但没有处理非零退出码，二者矛盾。建议 CI 侧显式接受 `--list` 的空结果，并把"零用例不得当验收证据"继续交给 Gate 执行器把关。
- 本轮未重跑，标注同上。

### D5 · Lint 未纳入 CI，且当前规则集与中文源码约定冲突【非阻断，工程配置问题】

- `pyproject.toml` 声明 `ruff>=0.9` 并配置 `select = ["E","F","I","UP","B","SIM","RUF"]`，但 `.github/workflows/ci.yml` 与仓库脚本中**没有任何步骤调用 ruff**。
- 实测（2026-09-14）：目标树 39 errors，绝大多数是 `RUF001/RUF002`（"含歧义全角标点"）——本项目注释、docstring 与错误文案**通篇使用中文全角标点**，该规则与项目语言约定直接冲突。
- 本轮未重跑（无 lint 门禁，且 P02-03 无文件）。提醒：P02-03 要交付的 `planning.py` 必然带中文 docstring，若届时启用 ruff 会立刻触发同类告警。

### D6 · Gate revision 由易失的会话/暂存文件构成，记录一签即不可复现【非阻断，P01-02 范围】

- `scripts/gates.py:43` 的 `EXCLUDED_FROM_REVISION` 只排除 `artifacts/gates`、`artifacts/e2e`；`compute_revision()`（`scripts/gates.py:327-342`）遍历整棵树。2026-09-14 实测该枚举共 1167 行，其中 `.mimosa/**` 451 行（约 39%）、`tmp/**` 423 行（约 36%）。
- **根因（已定性、可复现）**：`.mimosa/hook-state/<session>.json` 由 Agent 宿主机**每次工具调用**重写；两次连续工具调用之间不碰任何源码，快照差异恰好只有这一项（`artifacts/handoffs/P02-02/zcode/logs/revision-volatility.log`）。
- **本轮的又一次实证**：写入本次预验收记录本身就会推动该标签——evidence.json 记录的是"生成开始时"的值，而写完 `evidence.json`/`precheck.json` 后标签必然已变。这不是我的转录错误（本次已改为**由 `GateRunner.compute_revision()` 现场计算**，不再手抄哈希），而是 D6 在记录层面的直接体现：**任何 `--revision auto` 的 Gate 证据都无法在事后复现**。G01 中记录的 `ab054daf…` 因此永久不可复现，`--check-only` 恒报 `STALE recorded revision`。
- 同时**已被实测排除的假设**：曾怀疑"门禁自己跑 pytest 会改 `.pytest_cache` 从而自我失效"，实测 62 用例跑前跑后 `nodeids`/`lastfailed` 哈希未变，该假设**不成立**（`pytest-cache-attribution.log`），请勿据此归因。
- 建议：把 revision 输入收敛为真正的源码/契约/锁文件清单，或把 `.mimosa/**`、`tmp/**`、`.pytest_cache/**` 一并排除。

### D7 · 交接契约文档缺失（既有 `ARCH-0004`，本次继续成立）

- 仓库不存在 `docs/workflow/README.md`、`docs/workflow/02-ZCODE-PRECHECK.md`、`HANDOFF_CONTRACT.md`；`scripts/gates.py:305-311` 的注释也承认这点并自行固定路径约定。我按其约定 + 用户指令落盘（第 8 节），但**记录字段集合仍无契约来源**。

### D8 · Node 基线漂移【观察项，非阻断】

- `.node-version` = `22`，`package.json` 的 `engines` 为 `>=22 <25`，`ci.yml` 用 `node-version-file: .node-version` 装 Node 22；而本机运行时与 `G01.json` 记录的 `environment_fingerprint.node` 均为 `v24.18.0`。CI 与本地不同基线，前端类任务（P24 起）可能出现"本地过、CI 挂"。

### D9 · `_PENDING_APIS` 未登记 `planning`，P02-03 的能力探测拿不到责任人提示【观察项，非阻断，属 P01-01】

- 见第 3 节复现。`entities`（P02-02）被登记而 `planning`（P02-03）没有，P01-01 想要的"失败即报 + 归属任务"设计对 P02-03 失效，探测者只会看到裸 `AttributeError`。
- 影响：仅一致性与可诊断性，不会静默返回错值（模块不存在，调用必然失败）。
- 建议：落地 P02-03 时把 `planning` 补进两份注册表；`P02-04` 若要新增模块亦同。

## 6. 给 Codex 的重点风险与复核优先级

1. **Phase 02 是"连锁空仓"，不是单点缺失**：P02-01/02/03/04 四个任务全部零交付，G02 沙箱 5/27 且四个任务的 `-cmd1` 全是 exit 4。逐个补预验收记录没有意义，必须从 G01 与 P02-01 开始整链补齐。
2. **不要用 `gates.py --check-only` 的 exit 0 判断 Phase 02 就绪**：从未签收的 Gate 上它是空操作。要看真实结论就用非官方 `--out-dir` 沙箱跑一次（我留了 `tmp/zcode-g02-dryrun-p3/G02.json`）。
3. **`G01` 是唯一的硬阻塞链源头**：缺 3 份 `artifacts/handoffs/P01-0X/zcode/precheck.json` 与 `artifacts/gates/G01-codex-review.json`。补记录前需先决定 revision 口径（D6），否则新签的 G01 会立刻再次变成 STALE。
4. **`check_architecture.py` 的 exit 0 在空壳状态下是假信号**：零新增代码时它必然通过。G02 断言里的"分层检查通过"必须与"实体已存在"联合判定，否则会出现"空仓也通过"。
5. **`demo/` 只读性**：只读旧基线 `demo/backend/app/` 下已有 `entities.py`、`states.py` 等 0.1 骨架；P02-03 必须新写于 `packages/`，不得从教学探针导入或复制。验收时需比对以防"搬运旧实现当交付"——尤其 `ScheduleVersion`/`OptimizationResult` 这类旧骨架里可能已有同名概念。
6. **D3/D4 会让 CI 的 frontend job 红**，会掩盖后续真实失败；建议 Phase 02 开工前先修。
7. **D9 虽小但同类问题会复现**：每新增一个领域子模块（P02-04 的 runtime 等）都要同步 `_PENDING_APIS`，否则"未实现即报错"的设计在 Phase 02 逐格失效。

## 7. 我修改了什么（供 Codex 独立查验）

**修改的生产代码/测试/既有文档：无。** 本次为"无可验收对象"的阻断判定，不存在需要修复的白名单内错误；我没有改动 `packages/`、`tests/`、`scripts/`、`apps/` 下任何文件，也没有补写缺失的实现或测试（那是 DSH 的任务，且我不得为通过而放松验收项）。

**新增文件（仅预验收记录，均为本角色产物）**：

- `docs/handoffs/P02-03/zcode.md`（本报告）
- `artifacts/handoffs/P02-03/zcode/evidence.json`
- `artifacts/handoffs/P02-03/zcode/precheck.json`（Gate 执行器约定的同内容记录，`status=BLOCKED`，fail-closed）
- `artifacts/handoffs/P02-03/zcode/build-evidence.py`（可复跑的证据生成脚本：只读仓库、不启进程、不拼 shell；revision 标签由执行器现场计算而非手抄）
- `artifacts/handoffs/P02-03/zcode/logs/`（6 份命令日志）
- `tmp/zcode-g02-dryrun-p3/`（G02 非官方沙箱证据 + 日志，位于 `.gitignore` 忽略的 `tmp/` 下）

**DSH 原报告**：本任务不存在 DSH 报告可保留（`docs/handoffs/P02-03/dsh.md`、`artifacts/handoffs/P02-03/dsh/evidence.json` 均缺失），我未创建、未改写任何 DSH 侧记录。

**一处自我更正（留痕）**：本次首版 evidence.json 的 revision 标签是我手工转录的，漏了 4 个字符。发现后我改为在生成脚本里调用 `GateRunner.compute_revision()` 现场计算，并对生成物做了"记录值与计算值一致性"的校验，重跑后通过。如需复核该过程，`artifacts/handoffs/P02-03/zcode/build-evidence.py` 的 `current_revision()` 即为修正点。

## 8. 记录落盘约定（因 `ARCH-0004` 而需项目侧确认）

- 用户指令：`docs/handoffs/P02-03/zcode.md` + `artifacts/handoffs/P02-03/zcode/evidence.json` + 原始日志。
- Gate 执行器硬编码：`artifacts/handoffs/P02-03/zcode/precheck.json`，校验 `status == "Z_PRECHECK_PASSED"` 且 `verified_input_hashes` 未漂移。
- 两者不冲突，故我**同时落盘** `evidence.json` 与 `precheck.json`（内容一致）。`status` 取 `BLOCKED`：执行器会以 `status='BLOCKED' (expected 'Z_PRECHECK_PASSED')` 失败关闭，这正是期望行为——本任务确实未通过预验收。DSH 补交后需重新发起预验收，不能沿用本记录。
- P02-02 那轮已实测该失败关闭生效（执行器正确识别路径与字段并按 `status` 判失败）；本任务的记录采用完全相同的落盘方式与结构。

## 9. 已修复 / 未修复 / 未验证清单

**已修复**：无（无可修复对象；本角色不代替开发）。

**未修复（已定位、需责任方处理）**：

| 编号 | 摘要 | 责任任务 | 阻断 |
| --- | --- | --- | --- |
| D1 | P02-03 零交付（0/6） | DSH / P02-03 | 是（本任务） |
| D2 | G01 failed + P02-02 零交付（依赖 0/10 存在） | DSH / P02-02、P01-01~03 + Codex | 是（本任务） |
| D3 | 前端声明 `vitest run` 但未安装 vitest → CI frontend job 失败 | P01-01（或 P24-01） | 否 |
| D4 | `test:e2e:list` 空结果 exit 1 与 CI 必跑步骤矛盾 | P01-02 | 否 |
| D5 | ruff 未入 CI 且 `RUF001/002` 与中文标点约定冲突 | 工程配置 | 否 |
| D6 | Gate revision 由 `.mimosa/**`、`tmp/**` 等易失文件构成 | P01-02 | 否 |
| D7 | 交接契约文档缺失（`ARCH-0004` 延续） | 项目管理侧 + P01-03 | 否（阻断 G01 签收） |
| D8 | `.node-version` 钉 22 而本地/G01 指纹为 Node 24 | P01-01 / CI | 否（观察项） |
| D9 | `_PENDING_APIS` 未登记 `planning` | P01-01（落地 P02-03 时同步） | 否（观察项） |

**未验证 / 无法验证（工具或阶段未到，不臆造通过）**：

- 求解/容量/时间窗/温控/仓储占用/库存/交接等业务语义：Phase 06+ 才有引擎；P02-03 只涉及计划聚合与版本 lineage，本次无对象。
- Schema/OpenAPI/生成客户端一致性：生成器尚未建立（`scripts/export_contracts.py` 属 P02-04，`apps/frontend/scripts/generate-contracts.mjs` 属 P24-02），**记为"工具未建成（所属阶段未到）"，不是"检查通过"**。
- 静态类型检查：`pyproject.toml` 未配置 mypy/pyright；分层检查只覆盖导入方向。
- 真实 PostgreSQL / 真实 OR-Tools / SimPy / 浏览器 E2E：阶段未到。
- CI 本体：本检出**无 `.git`**，`ci.yml` 的 `git ls-files`、`git grep`、`git diff --exit-code -- package-lock.json` 无法按其原文执行。
- 本轮未重跑前端类检查（D3/D4）与 ruff（D5），理由见第 2 节，未冒充为通过。

## 10. 基础安全检查（针对当前变更集）

当前变更集为空（P02-03 无文件），故按"对现状做最小基线核查"执行：

- **凭据**：目标树无 `.env`/`.env.*`/`*.pem`/`*.p12`/`id_rsa*`；`sk-…`/`AKIA…` 字面量 0 命中；`.gitignore` 覆盖 `.env*`、`tools/bin/`、`node_modules/`、`.venv/`（`logs/baseline-checks.log`）。
- **命令注入**：`apps/`、`packages/`、`scripts/`、`tests/` 中无 `shell=True`、`os.system`、`eval(`、`exec(`、`pickle.loads`；Gate 执行器以 argv 数组执行命令。
- **SQL 注入入口**：当前无数据库访问代码（P03+ 才有），无拼接/format/f-string 组装 SQL 的入口，**该验收条件在本任务范围内不适用，而非"已通过"**。
- **鉴权/对象范围/日志脱敏**：P02-03 是纯领域模型（domain 不引入框架、不引 telemetry、不落日志）；HTTP 边界与脱敏属 P05-01/P37，无对象可测。
- **依赖变化**：本次无依赖变更；`uv lock --check` 与 `uv sync --frozen` 均 exit 0。
- **未对外部生产目标做任何扫描**。

## 11. 证据索引

| 证据 | 路径 |
| --- | --- |
| 机器证据（输入哈希、依赖存在性、命令与退出码、缺陷表、日志清单） | `artifacts/handoffs/P02-03/zcode/evidence.json` |
| Gate 执行器约定记录（同内容，`status=BLOCKED`） | `artifacts/handoffs/P02-03/zcode/precheck.json` |
| 证据生成脚本（可复跑复现全部哈希） | `artifacts/handoffs/P02-03/zcode/build-evidence.py` |
| P02-03 强制命令日志（2 条） | `artifacts/handoffs/P02-03/zcode/logs/cmd1-pytest.log`、`cmd2-architecture.log` |
| 回归与工程基础日志 | `logs/regression-pytest.log`、`logs/baseline-checks.log` |
| Gate 沙箱证据 | `logs/gates-phase02-sandbox.log`；`tmp/zcode-g02-dryrun-p3/G02.json`、`tmp/zcode-g02-dryrun-p3/G02-logs/` |
| 接口缺失与 D9 复现 | `logs/probe-interfaces.log` |
| D6 复现（上轮） | `artifacts/handoffs/P02-02/zcode/logs/revision-volatility.log`、`pytest-cache-attribution.log` |
| 上游任务状态 | `artifacts/gates/G01.json`（`status=failed`）、`artifacts/handoffs/P02-02/zcode/precheck.json`（`BLOCKED`） |
| P02-03 任务书 / 依赖图 / 冻结文档 | `docs/prompts/02-domain/P02-03-planning-entities.md`、`TASK_GRAPH.md`、`docs/plan/{TASK_MANIFEST.json,PHASE_GATES.md,TEST_FIXTURES.md}`、`docs/architecture/{DOMAIN_CATALOG.md,DATA_CONTRACTS.md,CONTRACT_FREEZE.md}` |
| 架构问题登记 | `docs/architecture/issues/README.md`（`ARCH-0004`、`ARCH-0005` 与本报告相关） |
