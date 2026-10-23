# P02-04 · ZCode → Codex 独立预验收报告

| 项目 | 值 |
| --- | --- |
| Task ID | `P02-04`（实现运行记录模型与 Schema 导出；Phase 02 最后一个任务，负责方 A） |
| 审查角色 | ZCode 独立预验收（**不是**开发方，DSH 的开发身份不覆盖本角色的审查职责） |
| 审查对象 | 仓库当前 candidate（`D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，与 DSH 同一项目、同一候选；本仓库无 `.git`，按整体内容哈希定位） |
| 本角色状态 | **`BLOCKED`** |
| 阶段 Gate | `G02`（未签收，且前置 `G01` 为 `failed`）；**本报告不签收任何 Gate** |
| 证据入口 | `artifacts/handoffs/P02-04/zcode/evidence.json`、`artifacts/handoffs/P02-04/zcode/logs/`（6 份命令日志） |
| 审查时间 | 2026-09-15（本机时区） |

## 0. 结论（先读这一段）

**P02-04 没有任何候选可验收：该任务的全部 10 个 Files 路径在仓库中都不存在，DSH 也未提交本任务的交接（`docs/handoffs/P02-04/dsh.md` 与 `artifacts/handoffs/P02-04/dsh/evidence.json` 均缺失）。**

两个声明的依赖也都不成立：`G01` 状态为 `failed`，`P02-03` 同样零交付（`TASK_MANIFEST.json` 声明 P02-04 的 deps 为 `[G01, P02-03]`，与 `TASK_GRAPH.md:49` 一致）。

因此判定 **`BLOCKED`**。我没有修改任何生产代码、测试或文档（详见第 7 节）。

**这个任务有一处与 P02-02/P02-03 不同的性质，请 Codex 特别注意**：P02-04 的 Files 里包含 `scripts/export_contracts.py` 与 `contracts/schemas.json` —— 也就是说**"Schema 确定性导出"本身就是本任务必须交付的能力，而不是"工具未建成、阶段未到"**。前几份报告里我把"Schema/OpenAPI/生成客户端一致性检查"记为"工具未建成"，那对 P02-02/P02-03 成立；**对 P02-04 不成立**：它的 Algorithm 段明确要求"导出确定排序 JSON Schema；生成文件只由脚本更新并提供 `--check`"，Test Case 2 就是"两次 export 字节一致"。所以这里缺的不是检查工具，而是**被测对象本身**。

复核者需要的最小动作：先让 Codex 补齐 `G01` 的 review 与 P01 任务预验收记录，再由 DSH 依序交付 `P02-01` → `P02-02` → `P02-03` → `P02-04`，再逐个提交预验收。第 4 节给出了一份可直接执行的复核清单，DSH 交付后无需重新推导。

## 1. 目标、白名单与契约核对

- **任务 Prompt 即验收需求**：`docs/prompts/02-domain/P02-04-runtime-contract-export.md`（哈希见 evidence.json 的 `verified_input_hashes`）。
- **白名单（Files，10 项）**：`contracts/schemas.json`、`docs/implementation/P02-04.md`、`docs/implementation/reports/P02-04.md`、`packages/contracts/src/logistics_contracts/common.py`、`packages/contracts/src/logistics_contracts/runtime.py`、`packages/domain/src/logistics_domain/execution.py`、`packages/domain/src/logistics_domain/runtime.py`、`scripts/export_contracts.py`、`tests/integration/test_p02_04_runtime_contract_export.py`、`tests/unit/test_p02_04_runtime_contract_export.py`。
- **存在性矩阵**：**10/10 缺失（0 存在）**。`contracts/` 目录下只有 `README.md` 与 `changes/README.md`（`contracts/README.md` 自称"本轮没有创建可执行 Schema"，与现状一致）。
- **白名单口径核对（避免误报不一致）**：`TASK_MANIFEST.json` 的 P02-04 条目 `files` 只列 6 个**生产**文件，另以 `task_doc`/`report`/`unit_test`/`integration_test` 四个字段列出其余 4 项，`allowed_files` 合计 10 —— 与 Prompt 的 10 项 Files **完全一致**。P02-01/02/03 同样一致（7/7/6）。因此**这里不存在 `ARCH-0005` 那种"任务书与冻结清单口径不一致"的问题**，我不为此虚报缺陷。
- **冻结接口核对**：`export_contracts() -> SchemaBundle; ErrorEnvelope(code, message, trace_id, details: tuple[ErrorDetail,...])`。实测：全仓（`apps/`、`packages/`、`scripts/`、`tests/`）搜索 `export_contracts`/`ErrorEnvelope`/`SchemaBundle`/`ErrorDetail` **只命中两行说明性文本**（`logistics_contracts/__init__.py` 的 `_PENDING_APIS` 里写着 `"export_schema": "P02-04: deterministic JSON Schema export via scripts/export_contracts.py"` 与 `"errors": "P05-01: typed ErrorEnvelope..."`），**无任何实现**。
- **依赖核对**（逐项实际检查）：`G01` = `failed`；`P02-03` 全部交付路径与 DSH 交接缺失，其预验收记录为 `BLOCKED`。evidence.json 的 `dependency_presence` 给出 13 个依赖产物的存在性：**0/13 存在**。

## 2. 强制命令实跑结果（原始日志逐条保留）

命令按 `docs/plan/TASK_MANIFEST.json` 的 P02-04 条目执行（与 Prompt 的 Validation Commands 一致），工作目录为仓库根，工具链走 `tools/bin/uv.exe`。

| 命令 | 实际结果 | exit code | 日志 |
| --- | --- | --- | --- |
| `uv run pytest tests/unit/test_p02_04_runtime_contract_export.py tests/integration/test_p02_04_runtime_contract_export.py -q` | `ERROR: file or directory not found: tests/unit/test_p02_04_runtime_contract_export.py`；`no tests ran in 0.00s` | **4** | `logs/cmd1-pytest.log` |
| `uv run python scripts/check_architecture.py` | `architecture-layers: scanned 7 module(s) across 7 layer(s); violations=0` | **0** | `logs/cmd2-architecture.log` |

**第二条命令的 exit 0 不构成通过证据**：它扫到的 7 个模块仍是 P01-01 的空壳 `__init__.py`，`violations=0` 只是因为本任务没有新增任何 domain/contracts 代码。这是"零用例/零新增即通过"的假信号，验收时不能引用。

**额外实跑的本任务关键检查**（不在强制清单内，但直接对应本任务能力）：

| 检查 | 结果 | exit code |
| --- | --- | --- |
| `uv run python scripts/export_contracts.py --check` | `can't open file 'scripts/export_contracts.py': [Errno 2] No such file or directory` | **2** |
| 四个冻结模块探测（`logistics_domain.execution`/`runtime`、`logistics_contracts.common`/`runtime`） | 全部 `ModuleNotFoundError` + `AttributeError` | — |

**未执行项（如实记录，不臆造成功）**：

- `npm ci`、前端工作区测试、`npm run test:e2e:list`：本轮**未重跑**——P02-04 的 Files 不涉及任何前端文件。相关缺陷 D3/D4 沿用 2026-09-14 的实跑证据，并在 evidence.json 中标注 `reverified_this_pass: false`。
- `uv run python scripts/gates.py --phase 02 --revision auto`：**未写入官方记录**。改用 `--out-dir tmp/zcode-g02-dryrun-p4` 的非官方沙箱运行，以免预验收动作污染 `artifacts/gates/G02.json`，也避免以任何形式代签 Gate。沙箱结果：`G02: 5/27 checks passed`。

## 3. 需求/用例覆盖情况

| 需求项（P02-04 Prompt） | 状态 |
| --- | --- |
| Objective / Files 交付对应 | **未交付**（0/10 文件） |
| Test Case 1：`Event(kind=vehicle_failure, payload 缺 vehicle_id)` → 校验失败 | **无法验证**（无实现、无测试） |
| Test Case 2：两次 export → 字节一致（确定性） | **无法验证**（生成器与 `contracts/schemas.json` 均不存在，没有可比对对象） |
| 10 个运行实体（Simulation…ExperimentResult）字段/状态/生命周期 | **未实现** |
| `export_contracts() -> SchemaBundle`、`ErrorEnvelope`/`ErrorDetail` | **未实现** |
| 边界 `extra=forbid`、payload discriminated union、业务 enum 只从 domain 引入 | **未实现** |
| P02 阶段须完整定义被引用的纯值类型（TwinState/ExecutionEvent/PendingEvent/RngState/AgentBudget/ExperimentSpec） | **未实现** |
| 生成文件只由脚本更新且提供 `--check` | **不存在该脚本** |
| domain 不导入框架（分层约束） | 当前 `violations=0`，但属空壳状态，不能代表交付 |
| Unit + Integration 两条测试命令零用例视为未验收 | 触发（0 用例，exit 4） |

用例覆盖率 **0/2**。按 Prompt"命令零用例或关键skip视为未验收"，本任务在任何解释下都不成立。

**独立复核（可复现，见 `logs/probe-interfaces.log`）**：四个本任务冻结的模块面全部不存在，且探测只得到裸 `AttributeError`：

```text
logistics_domain.execution      -> ModuleNotFoundError / AttributeError
logistics_domain.runtime        -> ModuleNotFoundError / AttributeError
logistics_contracts.common      -> ModuleNotFoundError / AttributeError
logistics_contracts.runtime     -> ModuleNotFoundError / AttributeError
scripts/export_contracts.py --check -> exit 2 (No such file or directory)
```

## 4. 交付后复核清单（DSH 交付 P02-04 时，Codex 可直接执行）

这一节的目的是把"下一次预验收要做什么"提前固化，减少往返：

1. `uv run python scripts/export_contracts.py --check` 必须 exit 0，且**连续跑两次生成物字节一致**（这就是 Test Case 2；确定性检查只有在真实生成器上才有意义）。
2. 负例：`Event(kind=vehicle_failure)` 的 payload 缺 `vehicle_id` 必须被拒绝，**错误信息要指出具体字段**，且**不得留下半成品产物**。
3. `contracts/schemas.json` 必须能由脚本重生成且与库中版本无差异（Prompt 明令"`contracts/*.json` 只能运行生成器更新，不得手改"），据此判断是否存在手改。
4. `DOMAIN_CATALOG.md` 的 32 个实体与辅助记录应都能在 bundle 中表达；边界模型 `extra=forbid`；payload 为判别联合。
5. `scripts/check_architecture.py` 仍须 `violations=0`（domain 不引入框架，contracts 不引入 adapters）。
6. **包 marker 检查**：Prompt 允许"确需导出本任务类型时"修改包 marker，但要求先在完成报告列出精确路径。请把 `packages/*/src/*/__init__.py` 的实际 diff 与该清单逐条比对，防止借 marker 越过接口边界。
7. 测试不得 mock 掉生成器或 schema 来源；确定性用例必须打在真实生成器上。

## 5. 相邻回归与工程基础检查（当前候选）

| 检查 | 命令 | 结果 | 日志 |
| --- | --- | --- | --- |
| 全量测试回归 | `uv run pytest -q` | **187 passed / 0 failed / 0 skipped**，exit 0 | `logs/regression-pytest.log` |
| 所有权/迁移检查 | `uv run python scripts/check_ownership.py --json` | `passed=true`，`violations=[]`，`default_owner_fallbacks=[]`，950 文件扫描，exit 0 | `logs/baseline-checks.log` |
| 依赖锁一致性 | `uv lock --check` | exit 0 | `logs/baseline-checks.log` |
| 冻结安装 | `uv sync --frozen` | exit 0 | `logs/baseline-checks.log` |
| Phase 02 Gate 沙箱运行 | `gates.py --phase 02 --out-dir tmp/zcode-g02-dryrun-p4` | exit 1，`G02: 5/27`；`P02-04-cmd1` exit 4；`P02-04` 的 DSH 证据/文档/报告/ZCode 记录全缺；`previous-gate:G01 status=failed` | `logs/gates-phase02-sandbox.log` |
| 白名单口径一致性 | 比对 manifest 与四份 Phase 02 Prompt | 一致（见第 1 节） | evidence.json `commands[manifest-prompt-consistency]` |

（`gates.py --phase 02 --check-only` 在从未签收的 Gate 上是**空操作**：打印 "nothing signed yet" 并 exit 0。**exit 0 不代表 Phase 02 就绪**，已在给 Codex 的风险项中列出。）

## 6. 确定缺陷清单（含路径与复现）

### D1 · P02-04 零交付，含必需的确定性 Schema 生成器【阻断本任务】

- 证据：第 1 节存在性矩阵（10/10 缺失）；`logs/cmd1-pytest.log`（exit 4）；`logs/probe-interfaces.log`（四个模块缺失、`scripts/export_contracts.py --check` exit 2）；`contracts/` 下无 `schemas.json`；`logs/gates-phase02-sandbox.log` 中 `P02-04-cmd1: exit_code=4`、`dsh-evidence:P02-04: missing`、两份 P02-04 文档 `missing`、`zcode-precheck:P02-04: missing`。
- 影响：本任务无候选。**Schema 确定导出与判别联合校验是本任务的验收对象本身**，不是"工具未建成"，所以不存在"检查通过但对象缺失"的解释空间。
- 归属：DSH / P02-04。

### D2 · 两个前置均未满足【阻断本任务】

- `G01` 未通过：`status=failed`，缺 `zcode-precheck:P01-01/02/03` 与 `codex-review`；`PHASE_GATES.md` 写明 G01 失败阻塞"Phase 02及以后"。
- `P02-03` 未交付：其全部交付路径、DSH 交接、任务文档缺失；`artifacts/handoffs/P02-03/zcode/precheck.json` 记录 `BLOCKED`；`packages/domain/src/logistics_domain/` 下仍只有 P01-01 的 `__init__.py` 空壳。
- `TASK_MANIFEST.json` 声明 deps `[G01, P02-03]`；evidence.json 的 `dependency_presence` 实测 **0/13 依赖产物存在**。
- 影响：即使 P02-04 立刻交付，也不满足"前置证据有效"的开工前提；按 Prompt"若前置缺失/失败，报告具体阻断，禁止跳 Gate"。

### D3 · 前端工作区声明了测试脚本但未安装 vitest【非阻断 P02-04，属 P01-01 范围】

- `apps/frontend/package.json` 声明 `"test": "vitest run"`，但该包**没有任何 `dependencies`/`devDependencies`**，而 `vitest.config.ts`、`src/test/setup.ts` 已存在。
- 复现（2026-09-14 实跑）：`npm --workspace @logistics/frontend run test --if-present` → **exit 1**（`'vitest' is not recognized`）。
- 影响：`.github/workflows/ci.yml:95` 是必跑步骤 → **CI 的 frontend job 必然失败**。本轮未重跑（P02-04 不涉及前端），已标注。

### D4 · `npm run test:e2e:list` 以非零退出，但 CI 当作必过步骤【非阻断 P02-04，属 P01-01/P01-02 范围】

- 复现（2026-09-14 实跑）：`Error: No tests found / Total: 0 tests in 0 files`，**exit 1**；`ci.yml:98` 是必跑步骤。
- `playwright.config.ts` 注释说明"无 spec 时列出 0 个用例是合法的"，但未处理非零退出码。建议 CI 显式接受空 `--list` 结果。本轮未重跑。

### D5 · Lint 未纳入 CI，且当前规则集与中文源码约定冲突【非阻断，工程配置问题】

- `pyproject.toml` 配置了 ruff 规则集，但**没有任何 CI 步骤或脚本调用它**。
- 2026-09-14 实测：目标树 39 errors，多数为 `RUF001/RUF002`（"含歧义全角标点"），与本项目通篇中文全角标点的约定直接冲突。
- 对 P02-04 的直接影响：本任务要交付的 `common.py`/`runtime.py`/`execution.py` 若带中文 docstring，启用 ruff 后会立刻触发同类告警。

### D6 · Gate revision 由易失的会话/暂存文件构成，记录一签即不可复现【非阻断，P01-02 范围】

- `scripts/gates.py:43` 的 `EXCLUDED_FROM_REVISION` 只排除 `artifacts/gates`、`artifacts/e2e`；`compute_revision()`（`scripts/gates.py:327-342`）遍历整棵树。2026-09-14 实测共 1167 行，其中 `.mimosa/**` 451 行、`tmp/**` 423 行。
- **根因（已定性、可复现）**：`.mimosa/hook-state/<session>.json` 被 Agent 宿主机**每次工具调用**重写；两次连续工具调用之间不碰源码，快照差异恰好只有这一项（`artifacts/handoffs/P02-02/zcode/logs/revision-volatility.log`）。
- **本轮再次被间接证实**：写入本次记录本身就会推动该标签（evidence.json 记的是"生成开始时"的值，写完后必然已变）。因此本次的 revision 标签同样由 `GateRunner.compute_revision()` **现场计算、不手抄**；G01 中记录的 `ab054daf…` 已永久不可复现，`--check-only` 恒报 `STALE recorded revision`。
- **已实测排除的假设**：曾怀疑"门禁自己跑 pytest 改 `.pytest_cache` 导致自我失效"，实测 62 用例跑前跑后哈希未变，**该假设不成立**（`pytest-cache-attribution.log`），请勿据此归因。

### D7 · 交接契约文档缺失（既有 `ARCH-0004`，本次继续成立）

- `docs/workflow/README.md`、`docs/workflow/02-ZCODE-PRECHECK.md`、`HANDOFF_CONTRACT.md` 均不存在；`scripts/gates.py:305-311` 的注释也承认并自行固定路径约定。我按其约定 + 用户指令落盘（第 8 节），但记录字段集合仍无契约来源。

### D8 · Node 基线漂移【观察项，非阻断】

- `.node-version` = `22`（CI 按此安装），而本机运行时与 `G01.json` 记录的 `environment_fingerprint.node` 均为 `v24.18.0`。CI 与本地不同基线，前端类任务（P24 起）可能出现"本地过、CI 挂"。

### D9 · `_PENDING_APIS` 登记了能力名但未登记 Phase 02 实际创建的模块名【观察项，非阻断，属 P01-01】

- 实测两份注册表：
  - `logistics_domain._PENDING_APIS` = `['entities','ids','ports','states','units']` —— 缺 `planning`（P02-03）、`execution`、`runtime`（P02-04）。
  - `logistics_contracts._PENDING_APIS` = `['dto','errors','export_schema','mapping']` —— 缺 `planning`（P02-03）、`common`、`runtime`（P02-04）。
- 一个值得注意的不对称：P02-04 的**能力名** `export_schema` **已被登记**（且确实抛 `NotImplementedError` 并指明 P02-04），但本任务将要创建的**模块名** `common`/`runtime` 没有登记。于是探测模块的人只拿到裸 `AttributeError`。
- 影响：仅一致性与可诊断性，不会静默返回错值（模块不存在，调用必然失败）。合计 5 个 Phase 02 模块名缺少"归属任务"提示。
- 建议：落地 P02-03/P02-04 时把 `planning`、`execution`、`runtime`、`common` 补进对应注册表。

## 7. 给 Codex 的重点风险与复核优先级

1. **Phase 02 是"连锁空仓"**：P02-01/02/03/04 四个任务全部零交付，G02 沙箱 5/27 且四个 `-cmd1` 全是 exit 4。逐个补预验收记录没有意义，必须从 `G01` 与 `P02-01` 开始整链补齐。
2. **不要把 P02-04 的 Schema 导出当成"工具未建成"**：它是本任务的验收对象；前几份报告里对 P02-02/P02-03 用过的"工具未建成（阶段未到）"措辞**不适用于这里**，第 0 节与 `not_verified` 都做了区分，请沿用该口径以免把缺失降级。
3. **不要用 `gates.py --check-only` 的 exit 0 判断 Phase 02 就绪**：从未签收的 Gate 上它是空操作。要看真实结论就用非官方 `--out-dir` 沙箱跑一次（我留了 `tmp/zcode-g02-dryrun-p4/G02.json`）。
4. **`G01` 是唯一的硬阻塞链源头**：缺 3 份 `artifacts/handoffs/P01-0X/zcode/precheck.json` 与 `artifacts/gates/G01-codex-review.json`；补记录前需先决定 revision 口径（D6），否则新签的 G01 会立刻再次变成 STALE。
5. **`check_architecture.py` 的 exit 0 在空壳状态下是假信号**：零新增代码时它必然通过。G02 断言里的"分层检查通过"必须与"实体/schema 已存在"联合判定。
6. **`contracts/*.json` 只能由生成器产出**：P02-04 落地后，判断 `contracts/schemas.json` 是否被手改的方法就是重跑 `export_contracts.py` 并比对差异（第 4 节第 3 条）。
7. **`demo/` 只读性**：只读旧基线 `demo/backend/app/` 下已有 `entities.py`、`states.py` 等 0.1 骨架；P02-04 必须新写于 `packages/`。旧骨架里可能已有 `Simulation`/`Event`/`Metric` 等同名概念，验收时需比对以防"搬运旧实现当交付"。

## 8. 我修改了什么（供 Codex 独立查验）

**修改的生产代码/测试/既有文档：无。** 本次为"无可验收对象"的阻断判定，不存在需要修复的白名单内错误；我没有改动 `packages/`、`tests/`、`scripts/`、`contracts/`、`apps/` 下任何文件，也没有补写缺失的实现或测试。

**新增文件（仅预验收记录，均为本角色产物）**：

- `docs/handoffs/P02-04/zcode.md`（本报告）
- `artifacts/handoffs/P02-04/zcode/evidence.json`
- `artifacts/handoffs/P02-04/zcode/precheck.json`（Gate 执行器约定的同内容记录，`status=BLOCKED`，fail-closed）
- `artifacts/handoffs/P02-04/zcode/build-evidence.py`（可复跑的证据生成脚本：只读仓库、不启进程、不拼 shell；revision 标签由执行器现场计算）
- `artifacts/handoffs/P02-04/zcode/logs/`（6 份命令日志）
- `tmp/zcode-g02-dryrun-p4/`（G02 非官方沙箱证据 + 日志，位于 `.gitignore` 忽略的 `tmp/` 下）

**DSH 原报告**：本任务不存在 DSH 报告可保留（`docs/handoffs/P02-04/dsh.md`、`artifacts/handoffs/P02-04/dsh/evidence.json` 均缺失），我未创建、未改写任何 DSH 侧记录。

## 9. 记录落盘约定（因 `ARCH-0004` 而需项目侧确认）

- 用户指令：`docs/handoffs/P02-04/zcode.md` + `artifacts/handoffs/P02-04/zcode/evidence.json` + 原始日志。
- Gate 执行器硬编码：`artifacts/handoffs/P02-04/zcode/precheck.json`，校验 `status == "Z_PRECHECK_PASSED"` 且 `verified_input_hashes` 未漂移。
- 两者不冲突，故我**同时落盘** `evidence.json` 与 `precheck.json`（内容一致）。`status` 取 `BLOCKED`：执行器会以 `status='BLOCKED' (expected 'Z_PRECHECK_PASSED')` 失败关闭，这正是期望行为。DSH 补交后需重新发起预验收，不能沿用本记录。
- P02-02/P02-03 两轮已实测该失败关闭生效（执行器正确识别路径与字段并按 `status` 判失败）；本任务记录采用完全相同的落盘方式与结构。

## 10. 已修复 / 未修复 / 未验证清单

**已修复**：无（无可修复对象；本角色不代替开发）。

**未修复（已定位、需责任方处理）**：

| 编号 | 摘要 | 责任任务 | 阻断 |
| --- | --- | --- | --- |
| D1 | P02-04 零交付（0/10），含必需的确定性 Schema 生成器 | DSH / P02-04 | 是（本任务） |
| D2 | G01 failed + P02-03 零交付（依赖 0/13 存在） | DSH / P02-03、P02-02、P02-01、P01-01~03 + Codex | 是（本任务） |
| D3 | 前端声明 `vitest run` 但未安装 vitest → CI frontend job 失败 | P01-01（或 P24-01） | 否 |
| D4 | `test:e2e:list` 空结果 exit 1 与 CI 必跑步骤矛盾 | P01-02 | 否 |
| D5 | ruff 未入 CI 且 `RUF001/002` 与中文标点约定冲突 | 工程配置 | 否 |
| D6 | Gate revision 由 `.mimosa/**`、`tmp/**` 等易失文件构成 | P01-02 | 否 |
| D7 | 交接契约文档缺失（`ARCH-0004` 延续） | 项目管理侧 + P01-03 | 否（阻断 G01 签收） |
| D8 | `.node-version` 钉 22 而本地/G01 指纹为 Node 24 | P01-01 / CI | 否（观察项） |
| D9 | `_PENDING_APIS` 未登记 `planning`/`execution`/`runtime`/`common` | P01-01（落地时同步） | 否（观察项） |

**未验证 / 无法验证（不臆造通过）**：

- **Schema 确定导出与生成物一致性：属本任务验收对象，缺失即 D1**，不是"工具未到阶段"。前端侧的客户端生成器（`apps/frontend/scripts/generate-contracts.mjs`，P24-02）仍属后续阶段，未执行。
- 静态类型检查：`pyproject.toml` 未配置 mypy/pyright；分层检查只覆盖导入方向。
- 真实 PostgreSQL / 真实 OR-Tools / SimPy / 浏览器 E2E：阶段未到。
- 确定性（两次 export 字节一致）与判别联合校验：没有生成器与四个模块，无法构造任何有效输入。
- 本轮未重跑前端类检查（D3/D4）与 ruff（D5），理由见第 2 节。
- CI 本体：本检出**无 `.git`**，`ci.yml` 的 `git ls-files`、`git grep`、`git diff --exit-code -- package-lock.json` 无法按其原文执行。

## 11. 基础安全检查（针对当前变更集）

当前变更集为空（P02-04 无文件），故按"对现状做最小基线核查"执行：

- **凭据**：目标树无 `.env`/`.env.*`/`*.pem`/`*.p12`/`id_rsa*`；`sk-…`/`AKIA…` 字面量 0 命中；`.gitignore` 覆盖 `.env*`、`tools/bin/`、`node_modules/`、`.venv/`（`logs/baseline-checks.log`）。
- **命令注入**：`apps/`、`packages/`、`scripts/`、`tests/` 中无 `shell=True`、`os.system`、`eval(`、`exec(`、`pickle.loads`；Gate 执行器以 argv 数组执行命令。
- **SQL 注入入口**：当前无数据库访问代码（P03+ 才有），无拼接/format/f-string 组装 SQL 的入口，**该验收条件在本任务范围内不适用，而非"已通过"**。
- **鉴权/对象范围/日志脱敏**：P02-04 是纯 domain/contracts 模型加一个 schema 导出脚本（domain 不引入框架、不引 telemetry）；`ErrorEnvelope` 的错误协议接线与脱敏属 P05-01/P37，无对象可测。
- **依赖变化**：本次无依赖变更；`uv lock --check` 与 `uv sync --frozen` 均 exit 0。
- **未对外部生产目标做任何扫描**。

## 12. 证据索引

| 证据 | 路径 |
| --- | --- |
| 机器证据（输入哈希、依赖存在性、命令与退出码、交付后复核清单、缺陷表、日志清单） | `artifacts/handoffs/P02-04/zcode/evidence.json` |
| Gate 执行器约定记录（同内容，`status=BLOCKED`） | `artifacts/handoffs/P02-04/zcode/precheck.json` |
| 证据生成脚本（可复跑复现全部哈希） | `artifacts/handoffs/P02-04/zcode/build-evidence.py` |
| P02-04 强制命令日志（2 条） | `artifacts/handoffs/P02-04/zcode/logs/cmd1-pytest.log`、`cmd2-architecture.log` |
| 冻结模块与生成器探测 | `logs/probe-interfaces.log`（含 `export_contracts.py --check` exit 2） |
| 回归与工程基础日志 | `logs/regression-pytest.log`、`logs/baseline-checks.log` |
| Gate 沙箱证据 | `logs/gates-phase02-sandbox.log`；`tmp/zcode-g02-dryrun-p4/G02.json`、`tmp/zcode-g02-dryrun-p4/G02-logs/` |
| D6 复现（上轮） | `artifacts/handoffs/P02-02/zcode/logs/revision-volatility.log`、`pytest-cache-attribution.log` |
| 上游任务状态 | `artifacts/gates/G01.json`（`status=failed`）、`artifacts/handoffs/P02-03/zcode/precheck.json`（`BLOCKED`） |
| P02-04 任务书 / 依赖图 / 冻结文档 | `docs/prompts/02-domain/P02-04-runtime-contract-export.md`、`TASK_GRAPH.md`、`docs/plan/{TASK_MANIFEST.json,PHASE_GATES.md,TEST_FIXTURES.md}`、`docs/architecture/{DOMAIN_CATALOG.md,DATA_CONTRACTS.md,CONTRACT_FREEZE.md}`、`contracts/README.md` |
| 架构问题登记 | `docs/architecture/issues/README.md`（`ARCH-0004`、`ARCH-0005` 与本报告相关） |
