# 架构问题登记 · Architecture Issues

本目录是开发过程中**唯一**记录架构问题的地方。依据架构约束第 5 条（原文）：发现架构问题先记录 `docs/architecture/issues/`；非阻断继续限定任务，阻断只做最小契约迁移并更新所有受影响调用方/测试/导出物，禁止大规模重构。

用途与边界：

- 只登记**架构/契约层面**的问题：冻结文档之间的语义差异、公共接口或单位口径冲突、职责/依赖方向被违反、生成物与契约漂移、Gate 证据缺口。
- 不登记普通实现缺陷、单个任务内的重构、求解质量调优；这些属于对应任务的完成报告与测试证据。
- 登记不等于批准变更：issue 记录事实、影响与决定，契约变更仍按 `docs/architecture/DATA_CONTRACTS.md` 兼容变更规则执行（先写 `contracts/changes/` 说明，再按 domain → DTO → ports → 调用方 → 测试 → 导出物 顺序迁移）。

## 记录格式

每条 issue 使用下列字段，写在 `docs/architecture/issues/ARCH-NNNN-<slug>.md`，并在本文件末尾的“当前登记”表中列出摘要行。

| 字段 | 必填 | 含义 |
| --- | --- | --- |
| `id` | 是 | `ARCH-NNNN`，四位递增编号；一经使用不再复用、不重新编号 |
| `status` | 是 | `open` / `decided` / `migrating` / `closed` / `accepted-as-is` |
| `discovered_by_task` | 是 | 发现该问题的任务 ID（如 `P00-02`）与发现方式（文档复核、测试失败、Gate 证据缺失等） |
| `title` | 是 | 一句话问题描述，不写结论或解决方案 |
| `evidence` | 是 | 具体文件、章节或命令输出；列出互相冲突的原文位置，引用而非转述 |
| `impact` | 是 | 一句话影响：影响哪些任务、Gate、调用方或导出物 |
| `blocking` | 是 | `yes` / `no`；`yes` 时必须说明阻塞哪个 Gate 或哪个任务的验收 |
| `decision` | 是 | 采用的处理方式与理由；若尚未决定写 `open` 并说明下一个决定者 |
| `owner` | 是 | 责任方（`A`/`B`）与责任任务 ID |
| `links` | 否 | 相关契约、issue、Gate 证据或变更说明的路径 |

## 格式模板（占位示例，非真实登记）

下列条目仅演示字段如何填写。它的 `id` 为 `ARCH-0000`，**该编号被保留**，不得用于真实问题；内容中的路径与结论均为格式示意，不作为事实引用。

```text
id:                  ARCH-0000（保留号，不得使用）
status:              open
discovered_by_task:  P00-00（示例）
title:               示例：某契约文件对同一字段给出两处不同单位
evidence:            示例：docs/... 第 N 节写 X；docs/... 第 M 节写 Y
impact:              示例：影响读取该字段的 Pxx-yy 与 Gyz 的断言口径
blocking:            no
decision:            示例：以来源文档为准，登记后由契约变更任务统一修改
owner:               A / P00-00（示例）
links:               示例：相关文件路径
```

对应的一行“当前登记”摘要格式：

| id | status | blocking | 标题 | 影响 | owner |
| --- | --- | --- | --- | --- | --- |
| `ARCH-0000` | 保留 | 格式模板 | 示例行，非真实问题 | 无 | — |

## 处理规则

1. **非阻断不扩 Scope**：非阻断问题只登记，继续执行当前限定任务；不得顺手重构、不得扩大本任务 Files 白名单、不得修改另一所有者的实现。
2. **阻断只做最小契约迁移**：阻断问题按最小必要范围迁移契约，并在**同一变更**内更新所有受影响调用方、测试与导出物（含生成的 JSON Schema/OpenAPI/TS 与 `contracts/changes/` 说明）；禁止大规模重构或以“顺便整理”扩大改动面。
3. **禁止跨所有者掩盖集成错误**：不得通过修改另一所有者（A/B）的实现来让问题消失；不得吞异常、不得把拒绝包装成成功、不得用测试替身装配正式运行。
4. **阻塞 Gate 必须被 Gate 证据引用**：任何阻塞某 Gate 的 issue，必须在该 Gate 的 `artifacts/gates/GNN.json` 证据的 `limitations` 中被引用（含 issue id 与状态）；Gate 未通过不得启动下一阶段，不能以修改日期或删减验收项恢复。
5. **决定留痕**：状态从 `open` 变更到 `decided`/`migrating`/`closed` 时，必须写明决定依据与被更新的文件清单；`accepted-as-is` 必须写明为何该差异可接受，以及它不会影响任何 Gate 断言。
6. **变更顺序**：契约类 issue 的修复顺序固定为 domain → DTO → ports → 调用方 → 测试 → 生成物；先写 `contracts/changes/` 说明，不通过聊天补交接。
7. **失效影响**：修复公共契约会使受影响 Gate 及其下游证据失效，必须回到相应任务重跑相关检查并重新签名，不能只改报告文字。

## 当前登记

以下表格是当前决定；后文原发现记录保留为历史，2026-10-03的补充决定优先于旧open描述。N01实施决定不是独立验收。

| id | status | blocking | 标题 | 影响 | owner |
| --- | --- | --- | --- | --- | --- |
| `ARCH-0001` | `open`（非阻断） | no | 需求追踪表 R08 行的验证 Gate 与其任务所属阶段不一致 | 只影响追踪表的 Gate 列；Phase 15/16 的完整性仍由 `G15`/`G16` 保证 | `P00-03` |
| `ARCH-0002` | `closed`（非阻断） | no | 旧基线清单只覆盖登记条目；已改为穷举覆盖并加覆盖闸门 | 曾影响清单可追溯性；现在由 `coverage.unregistered_file_count == 0` 闭环 | `P00-01` |
| `ARCH-0003` | `closed`（N01治理差异待N02独立复核） | no | Prompt未知能力错误码与冻结错误表不一致 | 改用INVALID_INPUT/422+UnsupportedDetail，开发未实现501/校验unsupported_codes语义保留 | A / N01 |
| `ARCH-0004` | `closed`（文档缺口已补，待N02复核） | no（G01仍缺独立审查记录） | 三份workflow交接契约缺失 | 已补实际路径/字段/职责/失效顺序，不代表G01签收 | A / N01 |
| `ARCH-0005` | `closed`（源与生成物已对齐，待独立复核） | no | P01-02四条用例与manifest不一致 | catalog回填，checker精确比对；规划1.0.2，不改实时状态 | A / N01 |
| `ARCH-0006` | `decided`（N01-R01完整设计待独立复核） | yes：G00，待N02裁定 | ScenarioBundle契约冻结缺口 | Ref/spec/input/hash/期望隔离完整决定，早期唯一来源 | A契约治理；实施P02-04 |
| `ARCH-0007` | `decided`（N01-R01完整设计待独立复核） | yes：G00，待N02裁定 | 早期类型和JobRequest前向依赖缺口 | 五kind/早期引用/Calendar/Actor/Resource及边界闭包已决定 | A契约治理 |
| `ARCH-0008` | `decided` | no | P36-02任务A与矩阵路径B冲突 | B矩阵贡献与缓存验证，A基准/回归/整合；路径权限不变 | A/B按文件；A整合 |

### ARCH-0001 需求追踪表 Gate 列与阶段屏障不严格对齐

- `id`：`ARCH-0001`
- `status`：`open`
- `discovered_by_task`：`P00-02`，在冻结文档复核阶段对照 `REQUIREMENTS_TRACEABILITY.md` 与 `PHASE_GATES.md` 时发现。
- `title`：需求追踪表 R08 行把验证 Gate 写为 `G29`，而该行列出的任务不全属于 Phase 29。
- `evidence`：`docs/plan/REQUIREMENTS_TRACEABILITY.md` 第 14 行 R08 行为 `P02-03, P03-04, P15-04, P16-03, P29-02` 与 `G29`；而 `TASK_GRAPH.md` 中 `P02-03` 属 Phase 02（出口 `G02`）、`P03-04` 属 Phase 03（出口 `G03`）、`P15-04` 属 Phase 15（出口 `G15`）、`P16-03` 属 Phase 16（出口 `G16`），只有 `P29-02` 属 Phase 29（出口 `G29`）。`docs/plan/PHASE_GATES.md` 明确写出每个 Gate 的必需任务仅为本阶段任务，且“每个 Gate 依赖本阶段全部 Task”。
- `impact`：追踪表的“Gate / 必需证据”列在语义上被读作“该需求由哪个 Gate 收口”，但实际列出的是最末一个覆盖该需求语义的 Gate。对新读者可能造成“R08 的版本不可覆盖性要到 `G29` 才验证”的错误印象，从而在 Phase 15/16 忽略其断言（`G15` 的“六项 diff 正确”、`G16` 的“V1 不覆盖”）。不影响任何已冻结字段、单位、enum 或接口语义。
- `blocking`：no。
- `decision`：`open`。建议由 `P00-03`（核验任务 DAG 与失败关闭的 Gate 规则）决定采用哪一种修法：(a) 在追踪表中显式列出该需求对应的多个阶段 Gate，或 (b) 在 `REQUIREMENTS_TRACEABILITY.md` 表头注明“Gate 列为该需求的主要收口 Gate，其任务所属各阶段的 Gate 同样必须通过”。本 issue 不做单方面裁决，也不修改任何冻结制品。
- `owner`：`A`（`P00-03`）；若判定需要修改冻结制品，则由契约变更任务在同一变更内更新追踪表与其生成物。
- `links`：`docs/plan/REQUIREMENTS_TRACEABILITY.md`、`docs/plan/PHASE_GATES.md`、`TASK_GRAPH.md`、`docs/architecture/CONTRACT_FREEZE.md`（第 7 节引用本 issue）。

冻结时未发现其他架构问题：`2026-09-12` 冻结复核未在 12 个冻结制品之间发现阻滞性矛盾，除上述 `ARCH-0001` 外没有登记任何 issue，也不存在阻断项；`CONTRACT_FREEZE.md` 因此记录 `unresolved_blocking_issues: []`。

### ARCH-0002 旧基线清单为“登记集合”而非“穷举集合”

- `id`：`ARCH-0002`
- `status`：`closed`
- `discovered_by_task`：`P00-01`，在登记旧 demo 资产时对照 `demo/` 实际文件树与生成器清单发现：清单最初逐条登记 87 条（80 个真实文件 + 7 条目录级冻结边界），而 `demo/` 下实际还存在 68 个既不在 `ENTRIES`、也不在排除集合中的普通文件（包 marker、`requirements*.txt`、`dist/` 构建产物、`demo/frontend/src/**` 等）。
- `title`：`docs/architecture/BASELINE_INVENTORY.json` 的登记集合与 `demo/` 实际文件树不相等，缺少可证明的覆盖闸门。
- `evidence`：`tools/ai_coding_plan/baseline_inventory_generate.py` 的 `ENTRIES`/`FROZEN_FILES` 是显式白名单；清单的 `coverage` 字段现在输出 `registered_file_count`、`unregistered_file_count` 与 `unregistered_files`；`artifacts/handoffs/P01-01/dsh/evidence.json` 的 `legacy_demo.tree_sha256` 记录 `demo/` 全树指纹（175 个文件，含派生目录）。
- `impact`：曾使清单只能证明“被登记资产”，不能证明“旧基线全部普通文件已处置”。不影响 G00 的三个文档契约断言（旧 demo 资产有逐项证据、单位/实体/错误/Protocol 冻结、DAG 与需求追踪无缺口），也不影响 G01 的“旧 demo 未被覆盖”断言——后者由 `demo/` 全树指纹直接验证。
- `blocking`：no。
- `decision`：`closed`。处理方式为把清单改为穷举覆盖：`demo/` 下每个普通文件必须有一条 `entries` 记录（当前 173 条，全部带现场计算的 `sha256`，无 `null`），生成器新增 `coverage.unregistered_file_count` 闸门，任何未登记普通文件都使生成器报告缺口；两个大型派生目录（`demo/frontend/node_modules/` 10984 个文件、`demo/.venv/` 1476 个文件）不作为逐文件条目，改为记录计数与树指纹，避免用构建产物淹没证据。缓存类目录（`__pycache__`、`.pytest_cache`、`.mypy_cache`、`.ruff_cache`、`.git`）按约定不登记。残余边界语义已写入 `docs/architecture/BASELINE_INVENTORY.md` 第 12 节。
- `owner`：`A`（`P00-01`）。
- `links`：`docs/architecture/BASELINE_INVENTORY.json`（`coverage`）、`docs/architecture/BASELINE_INVENTORY.md`（第 10 至 12 节）、`docs/architecture/MIGRATION_MAP.md`、`artifacts/handoffs/P01-01/dsh/evidence.json`。

### ARCH-0003 任务 Prompt 的 `UNSUPPORTED` 未登记在冻结错误表中

- `id`：`ARCH-0003`
- `status`：`open`
- `discovered_by_task`：`P00-01`，在核对旧能力边界并交叉检查错误语义时发现；`P00-02` 冻结复核确认该差异存在。
- `title`：全部 109 个任务 Prompt 的 Error Handling 段落要求"未知必需能力→`UNSUPPORTED`并拒绝有效结果"，但 `docs/architecture/DATA_CONTRACTS.md` 的错误表没有登记 `UNSUPPORTED` 这个错误码。
- `evidence`：`docs/architecture/DATA_CONTRACTS.md` 第 13 行的错误表为 `INVALID_INPUT/INVALID_TRANSITION/DEPENDENCY_CYCLE→422`、`UNAUTHENTICATED→401`、`FORBIDDEN/TOOL_FORBIDDEN→403`、`NOT_FOUND→404`、`STALE_SNAPSHOT/RESOURCE_CONFLICT/IDEMPOTENCY_CONFLICT/CONFIRMATION_EXPIRED→409`、`REQUEST_TOO_LARGE→413`、`RATE_LIMITED→429`、`PROVIDER_UNAVAILABLE/DEPENDENCY_UNAVAILABLE→503`、`INTERNAL_ERROR→500`；同段另写明 `MANUAL_REQUIRED`、`NO_FEASIBLE_CANDIDATE` 是"业务结果原因"，以及"未实现能力在开发期间 HTTP 501，禁止进入对应 Gate"。第 11 行的 `ErrorDetail` 判别联合含 `UnsupportedDetail(capability)`，但那是**明细类型**，不是错误码表项，且未规定其承载的 HTTP 状态码。各任务 Prompt（例如 `docs/prompts/01-foundation/P01-01-workspace-bootstrap.md` 第 138 行）仍要求 `UNSUPPORTED`。
- `impact`：实现 `error` 协议时可能自造一个未冻结的错误码与状态码组合（例如把"未知必需能力"做成 200/501/422 三者之一），造成 API_CONTRACT 与 DATA_CONTRACTS 漂移、前端无法稳定分类。**非阻断**：本差异只影响错误码命名的落点，不影响任何实体、单位、状态枚举或求解语义；在 P05-01 实现错误协议之前不会产生错误行为，因为当前没有任何 HTTP 边界实现。
- `blocking`：no。
- `decision`：`open`。候选处理方式：(a) 若确认 `UNSUPPORTED` 就是 `UnsupportedDetail` 所对应的错误码，则在 DATA_CONTRACTS 错误表中补登它及其状态码（按契约变更流程：先写 `contracts/changes/`，再更新受影响调用方/测试/导出物）；(b) 若确认"未知必需能力"应统一走既有错误码（如 422 `INVALID_INPUT` 或 501 未实现能力），则修订任务 Prompt 生成源，去掉 `UNSUPPORTED` 一词。本 issue 不单方面裁决；需在 `P05-01`（FastAPI 组合根、错误协议与基础鉴权）开始前决定，因为该任务会固定错误协议。
- `owner`：`A`（`P05-01`）；若判定需要改契约，则由契约变更任务在同一变更内更新 `DATA_CONTRACTS.md`、API_CONTRACT 与生成物，并重验受影响 Gate。
- `links`：`docs/architecture/DATA_CONTRACTS.md`（第 11、13 行）、`docs/api/API_CONTRACT.md`、`docs/architecture/CONTRACT_FREEZE.md`（第 7 节引用本 issue）、`docs/architecture/MIGRATION_MAP.md`（第 3 节限制已登记该待确认点）。

### ARCH-0004 交接契约文档缺失

- `id`：`ARCH-0004`
- `status`：`open`
- `discovered_by_task`：`P01-02`，在实现阶段 Gate 执行器时按任务书读取 `docs/workflow/HANDOFF_CONTRACT.md` 未找到该文件；随后对全仓检索（`*.md`、文件名）确认三个被引用的契约文档均不存在。
- `title`：`docs/workflow/README.md`、`docs/workflow/02-ZCODE-PRECHECK.md`、`docs/workflow/HANDOFF_CONTRACT.md` 在本仓库中从未存在。
- `evidence`：任务书 `P01-02` 的文档列表引用上述三份文件；全仓检索 `HANDOFF_CONTRACT|ZCODE-PRECHECK|Z_PRECHECK_PASSED` 只命中本任务与 P01-01 自己写的交接说明（`docs/handoffs/P01-01/dsh.md` 第 7、77–78 行已如实登记该缺口）。`docs/workflow/` 目录不存在。
- `impact`：Codex review 与 ZCode 预验收记录的**存放路径与字段格式无契约来源**。Gate 执行器必须先能识别这两类记录才能执行"缺失即不写 passed"的规则（Test Case 3）。本任务的处理是自行约定默认路径并把"缺失"判为失败（失败关闭），因此功能上安全，但**G01 因此无法签收**：真实运行中 `artifacts/gates/G01.json` 为 `failed`，`failed_checks` 明确包含 `codex-review` 与三个 `zcode-precheck:*`。这不阻断开发（P01-03 可继续），只阻断 Gate 签收。
- `blocking`：yes（阻断 `G01` 签收；不阻断同阶段开发）。
- `decision`：`open`。本任务采用的过渡约定（已写入 `docs/implementation/P01-02.md` 第 5 节）：
  - ZCode 预验收：`artifacts/handoffs/<TASK_ID>/zcode/precheck.json`，字段 `{schema_version, task_id, status: "Z_PRECHECK_PASSED", reviewer, verified_input_hashes: {path: sha256}}`；
  - Codex 阶段 review：`artifacts/gates/G<NN>-codex-review.json`，字段 `{schema_version, gate_id, status: "approved"|"passed", reviewer, code_revision, verified_input_hashes}`。
  待契约文档补齐后，应改为引用契约并同步更新 `scripts/gates.py` 与测试；若判定上述约定即为正式契约，则文档侧按此补写而不是新增第三套格式。
- `owner`：项目管理侧（契约文档补齐）；`A`（`P01-03` 落地路径一致性与所有权校验）。
- `links`：`docs/implementation/P01-02.md`（第 5 节限制）、`docs/handoffs/P01-01/dsh.md`（第 6 节流程缺口）、`scripts/gates.py`、`docs/plan/GATE_EXECUTION_CONTRACT.md`（第 2 节证据最小字段）。

### ARCH-0005 P01-02 的冻结 Test Case 与任务书不一致

- `id`：`ARCH-0005`
- `status`：`open`
- `discovered_by_task`：`P01-02`，在执行前用 `docs/plan/TASK_MANIFEST.json` 与 `docs/prompts/01-foundation/P01-02-checks-and-gate-runner.md` 逐项核验任务书时发现。
- `title`：仓库内的 P01-02 Prompt 与机器清单只列 2 条 Test Case，交付方任务书（计划 1.1.0）列 4 条。
- `evidence`：`docs/prompts/01-foundation/P01-02-checks-and-gate-runner.md` 第 142–149 行仅有 `命令 exit=1 => G01 failed 且进程非零` 与 `domain 导入 fastapi => 层边界检查失败`；`TASK_MANIFEST.json` 的 P01-02 `cases` 字段内容相同。任务书另要求 `Codex review 缺失或 ZCode 输入哈希过期 => 不写 passed` 与 `--check-only 全部成功 => 仅输出检查结果，不签收 Gate`。
- `impact`：两条额外用例没有冻结来源。若实现它们，Gate 证据覆盖面超过清单口径；若不实现，"Codex review 缺失不得写 passed"这一失败关闭要求将无测试保障。`docs/plan/PHASE_GATES.md` 的"缺证据/跳过测试均失败"原则与用例 3 一致，因此实现它们是**加强**而非削弱验收，但清单与证据口径需要对齐。
- `blocking`：no。
- `decision`：`open`。交付方决定（已在完成报告中披露）：实现全部 4 条用例，**不修改** `docs/plan/TASK_MANIFEST.json`（实现约定禁止为标状态改机器清单）；由规划侧决定后续是否把两条用例回填到 catalog/render 源并重新生成清单（按"改规划要改源、重新生成、静态检查、单独记录计划版本变更"的流程）。
- `owner`：规划版本对齐任务（catalog/render 源）；`A`（P01-02 证据已按 4 条记录）。
- `links`：`docs/prompts/01-foundation/P01-02-checks-and-gate-runner.md`、`docs/plan/TASK_MANIFEST.json`、`docs/implementation/reports/P01-02.md`、`tests/integration/test_p01_02_checks_and_gate_runner.py`。

### ARCH-0006 ScenarioBundle 无任何冻结归属

- `id`：`ARCH-0006`
- `status`：`open`
- `discovered_by_task`：`P04-01`（`canonical-fixtures`），在按任务书核对 `generate_scenario(spec: ScenarioSpec, seed: int) -> ScenarioBundle` 签名右侧类型的来源时发现。
- `title`：`ScenarioBundle` 出现在多处已冻结的接口签名中，但 `DATA_CONTRACTS.md` 只指派了 `ScenarioSpec` 的形状归属（`P02-04`），未指派 `ScenarioBundle`。
- `evidence`：需要它的签名有 `DATA_CONTRACTS.md:94`（`ScenarioEngine.load(ref:ScenarioRef)->ScenarioBundle`）、`docs/prompts/01-foundation/P04-01-canonical-fixtures.md:90`、`API_CONTRACT.md:47`。**已指派 `ScenarioSpec`**：`DATA_CONTRACTS.md:81` —— “`ScenarioSpec`的纯数据形状也在**P02-04**定义，P04负责生成；`ScenarioEngine`的加载实现可在P12-04装配。” **未指派 `ScenarioBundle`**：具名 Schema 表内没有该行，`DOMAIN_CATALOG.md` 只有 `Simulation` 与 `Experiment` 两个实体；`P11-01:69` 的模型清单列的是 `ScenarioSpec` 而非 `ScenarioBundle`；形状线索仅见于 `IMPLEMENTATION_CONVENTIONS.md:33` 的内部接口表，且该表描述的是 `ScenarioSpec`。详见 `docs/architecture/issues/ARCH-0006-scenario-bundle-ownership.md`。
- `impact`：`P04-01` 的白名单不含领域类型模块，却在签名右侧要求返回 `ScenarioBundle`；实现者只能在“自带第二份定义”（触犯 Constraint 6）与“返回未定义 `dict`”（触犯 Constraint 1）之间二选一。同类风险波及 `P04-02`、`P12-04`、`P16-04`、`P39-*`。
- `blocking`：no（`P04-01` 当前因 `G03` 未签收而 BLOCKED，本 issue 不是其当前阻断原因；但必须在 `P04-01` 重新下发前有结论）。
- `decision`：`open`。候选：(a) 把 `ScenarioBundle` 纯数据形状补入具名 Schema 表并归 `P02-04`（与同段 `ScenarioSpec` 的“被后续阶段引用的纯值类型必须由 P02 定义”规则一致）；(b) 若判定其属仿真域装配产物，则在契约中显式写明定义任务（如 `P11-01`）并在清单 `allowed_files` 给出承载模块；(c) 若判定 `P04-01` 应为定义者，须把承载文件加入其 `files`/`allowed_files`。任一项均属契约变更，先写 `contracts/changes/`，再按 domain → DTO → ports → 调用方 → 测试 → 生成物 顺序迁移并重验受影响 Gate。
- `owner`：契约所有者（`DATA_CONTRACTS.md` 维护方）决定归属；落地由被指派阶段任务执行，与 `P04-01` 重新下发存在时序依赖。
- `links`：`docs/architecture/issues/ARCH-0006-scenario-bundle-ownership.md`、`docs/architecture/DATA_CONTRACTS.md`（第 81、94 行）、`docs/architecture/IMPLEMENTATION_CONVENTIONS.md`（第 33 行）、`docs/api/API_CONTRACT.md`（第 47 行）、`docs/prompts/01-foundation/P04-01-canonical-fixtures.md`（第 90 行）、`artifacts/handoffs/P04-01/dsh/evidence.json`。

## 2026-10-03 N01治理决定（替代相关历史open结论）

- ARCH-0003：closed。renderer以DATA_CONTRACTS既有INVALID_INPUT/422、UnsupportedDetail、ValidationReport.unsupported_codes及开发501规则消除自造UNSUPPORTED错误码；全部109项prompt从源重生成。不新增业务ErrorCode或变更HTTP标准。独立核验交N02。
- ARCH-0004：closed（仅文档缺口）。补[workflow入口](../../workflow/README.md)、[ZCode步骤](../../workflow/02-ZCODE-PRECHECK.md)、[交接契约](../../workflow/HANDOFF_CONTRACT.md)，忠实记录执行器的phase_gate及四类必需输入，区分实际读取检查与人工/冻结规则要求。未修改执行器；G01仍因缺/失效证据阻断。
- ARCH-0005：closed（规划口径）。build_catalog增加缺review/输入漂移及check-only不签收两个案例，render重生成manifest/prompt；validate_plan增加案例逐项比对及正/负例，版本1.0.2。109项Task仍planned，40项Gate仍not_run。此前外部1.1.0任务书只作为缺口线索，没有复制另一工作根规划。
- ARCH-0006：decided；字段未决导致P02-04派发阻断。ScenarioBundle和ScenarioRef纯值归P02-04 domain/runtime.py，DTO映射同任务contracts/runtime.py；P04生成/导入、P12加载、P16视图均复用。完整成员/版本/引用语义证据不足，不填dict/Any或猜测字段。详见[独立issue](ARCH-0006-scenario-bundle-ownership.md)。
- ARCH-0007：open；Settings、ImportReceipt、MasterDataUpdate等承载已明确，字段及JobRequest未来请求union依赖仍未决。详见[逐项审计](../TYPE_DEFINITION_OWNERSHIP.md)和[issue](ARCH-0007-early-named-types.md)。A契约治理必须先决定并独立复核，再派发相应任务。
- ARCH-0008：decided；P36-02沿用路径归属，按B源码/缓存验证与A基准/回归/整合拆分，manifest贡献集合覆盖完整白名单。详见[issue](ARCH-0008-p36-02-ownership.md)。

修改清单及冻结迁移见[contracts change](../../../contracts/changes/N01-governance-1.0.1.md)。本轮不重写CONTRACT_FREEZE或G00，不冒签ZCode/Codex通过。未决项须由N02评估是否阻断本次冻结/G00；本登记不预先替独立审查者作通过决定。

N01同任务复核修正：1.0.1误列JobKind/JobStatus在runtime定义，1.0.2改为P02-01 states唯一定义并前移成员未决阻断；补主数据具名类型审计。G00常规流程例外在workflow明确。不是N02审查或Gate签收。


## N01-R01 本轮决定与阻断保留

独立N02已经把ARCH-0006/0007关键缺口裁定为G00冻结阻断，不是仅下游派发限制。N01-R01提交完整字段/枚举/引用/依赖/hash/期望隔离及正反例，状态decided待独立复核；本实施者没有写closed、恢复G00或更新冻结身份。当前登记表对应行优先于上文旧轮历史描述。全部新增选择明示本轮设计决定，完整差异及版本迁移见[changes](../../../contracts/changes/N01-R01-contract-freeze-2.0.0.md)，字段/来源见[DATA](../DATA_CONTRACTS.md#n01-r01-本轮完整契约决定)与[类型审计](../TYPE_DEFINITION_OWNERSHIP.md)。任务ID N01-R01为治理返工标识，不加入业务manifest。未决的唯一签收事项是N02对新设计与证据的独立判定；所有业务实施/外部smoke仍未运行。
