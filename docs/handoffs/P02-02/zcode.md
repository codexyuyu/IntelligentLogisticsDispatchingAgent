# P02-02 · ZCode → Codex 独立预验收报告

| 项目 | 值 |
| --- | --- |
| Task ID | `P02-02`（实现订单、货物与运仓资源领域模型；Phase 02，负责方 A） |
| 审查角色 | ZCode 独立预验收（**不是**开发方，DSH 的开发身份不覆盖本角色的审查职责） |
| 审查对象 | 仓库当前 candidate（`D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，与 DSH 同一项目、同一候选；本仓库无 `.git`，按整体内容哈希定位） |
| 本角色状态 | **`BLOCKED`** |
| 阶段 Gate | `G02`（未签收，且前置 `G01` 为 `failed`）；**本报告不签收任何 Gate** |
| 证据入口 | `artifacts/handoffs/P02-02/zcode/evidence.json`、`artifacts/handoffs/P02-02/zcode/logs/`（28 份原始日志） |
| 复核轮次 | 第 1 轮 2026-09-14 23:42；第 2 轮 2026-09-15（同一候选、未变更；两轮结论一致） |
| 审查时间 | 2026-09-15（本机时区；同日复核） |

## 0. 结论（先读这一段）

**P02-02 没有任何候选可验收：该任务的全部 7 个 Files 路径在仓库中都不存在，DSH 也未提交本任务的交接（`docs/handoffs/P02-02/dsh.md` 与 `artifacts/handoffs/P02-02/dsh/evidence.json` 均缺失）。**

同时两个前置条件都不成立：`P02-01` 同样零交付，`G01` 的 Gate 状态为 `failed`，而 `docs/plan/PHASE_GATES.md` 明确 `G01` 失败阻塞 Phase 02 及以后。

因此本次不是"实现有缺陷"，而是"无可验收对象"，判定 **`BLOCKED`**。我没有修改任何生产代码、测试或文档（详见第 7 节），因为无交付物可修，且我不得代替 DSH 实现任务、不得为通过而放松验收项。

**第 2 轮复核（2026-09-15）**：因本任务被再次指派，我没有沿用上一轮结论，而是重新核查并**重跑了全部强制命令与相邻检查**，结果逐项一致（`cmd1` exit 4、`cmd2` exit 0 空壳通过、回归 187 passed、G02 沙箱 5/27、`previous-gate:G01` 仍 `failed`）。同时把上一轮记录的 **29 条 `verified_input_hashes` 全部重算，逐条字节一致**——说明任务书、清单、冻结契约、锁文件与 Gate 记录自上轮以来没有任何漂移，本次给出的仍是"无候选"而非"候选变差"。结论不变：**`BLOCKED`**。

复核者需要的最小动作：先按第 6 节把 `G01` 三个任务的预验收记录与 Codex review 补齐并重跑 Gate，再由 DSH 依序交付 `P02-01`、`P02-02`（各自带 `docs/implementation/P02-0X.md`、`docs/implementation/reports/P02-0X.md`、`artifacts/handoffs/P02-0X/dsh/evidence.json` 与两份测试文件），然后重新提交预验收。

## 1. 目标、白名单与契约核对

- **任务 Prompt 即验收需求**：`docs/prompts/02-domain/P02-02-master-entities.md`（哈希见 evidence.json 的 `verified_input_hashes`）。
- **白名单（Files）**：`docs/implementation/P02-02.md`、`docs/implementation/reports/P02-02.md`、`packages/contracts/src/logistics_contracts/entities.py`、`packages/domain/src/logistics_domain/orders.py`、`packages/domain/src/logistics_domain/resources.py`、`tests/integration/test_p02_02_master_entities.py`、`tests/unit/test_p02_02_master_entities.py`。
- **存在性矩阵**：7/7 缺失（0 存在）。全仓（排除 `node_modules`/`.venv`/`demo/`/`tmp/`）搜索 `entities.py`、`orders.py`、`resources.py`、`primitives.py`、`states.py`、`ids.py`、`units.py`、`*p02_02*` 仅命中只读旧基线 `demo/backend/app/...` 与文件包校验副本 `tmp/package-verification/...`，**新目标树 `packages/`、`apps/` 下 0 命中**。
- **接口核对**：Prompt 冻结入口为 `OrderDTO.to_domain() -> Order; ResourceDTO.to_domain() -> Resource`。全仓搜索 `OrderDTO`/`ResourceDTO` 只命中规划文档（`docs/prompts/`、`docs/plan/TASK_MANIFEST.json`、`docs/api/API_CONTRACT.md`）与 `.mimosa` 会话基线快照，**无任何实现**。
- **契约文档**：本次要求的 `docs/workflow/README.md`、`HANDOFF_CONTRACT.md` 在仓库中不存在（已登记的 `ARCH-0004`，状态 `open`、`blocking: yes`，明确写"阻断 G01 签收"）。我按"用户指令 + Gate 执行器硬编码约定"两处落盘（见第 8 节）。

## 2. 强制命令实跑结果（原始日志逐条保留；第 1、2 轮分别实跑，结果一致）

命令按 `docs/plan/TASK_MANIFEST.json` 的 P02-02 条目执行，工作目录为仓库根，工具链走 `tools/bin/uv.exe`（`uv 0.12.13`）。

| 命令 | 实际结果 | exit code | 日志 |
| --- | --- | --- | --- |
| `uv run pytest tests/unit/test_p02_02_master_entities.py tests/integration/test_p02_02_master_entities.py -q` | `ERROR: file or directory not found: tests/unit/test_p02_02_master_entities.py`；`no tests ran in 0.00s` | **4** | `logs/cmd1-pytest.log` |
| `uv run python scripts/check_architecture.py` | `architecture-layers: scanned 7 module(s) across 7 layer(s); violations=0` | **0** | `logs/cmd2-architecture.log` |

**第二条命令的 exit 0 不构成通过证据**：它扫描到的 7 个模块仍是 P01-01 的空壳 `__init__.py`（每个包 1 个模块），`violations=0` 只是因为本任务没有新增任何 domain 代码。这是"零用例/零新增即通过"的假信号，验收时不能引用。

**未执行项（如实记录，不臆造成功）**：

- `npm ci`：未重跑（会重建 `node_modules`）；`G01` 证据中该命令已 exit 0，本次以非破坏性前端检查替代（第 4 节）。
- `uv run python scripts/gates.py --phase 02 --revision auto`：**未写入官方记录**。我改用 `--out-dir tmp/zcode-g02-dryrun` 做非官方沙箱运行（该记录被标记为非官方、不覆盖阶段记录），以免预验收动作污染 `artifacts/gates/G02.json`，也避免以任何形式代签 Gate。沙箱结果：`G02: 5/27 checks passed`。

## 3. 需求/用例覆盖情况

| 需求项（P02-02 Prompt） | 状态 |
| --- | --- |
| Objective / Files 交付对应 | **未交付**（0/7 文件） |
| Test Case 1：需求 1001g 与车辆 1000g → 数据可表示、分配规则判容量违规 | **无法验证**（无实现、无测试） |
| Test Case 2：`cargo.temperature=[80,20]` → 输入无效 | **无法验证**（无实现、无测试） |
| 每实体 id/status/UTC 时间/row_version/schema_version；单位 g/cm³/m/分/decic | **未实现** |
| `extra=forbid`、非法枚举/单位/负值拒绝 | **未实现** |
| domain 不导入框架（分层约束） | 当前 `violations=0`，但属空壳状态，不能代表交付 |
| Unit + Integration 两条测试命令零用例视为未验收 | 触发（0 用例，exit 4） |

用例覆盖率 **0/2**。按 Prompt"命令零用例或关键skip视为未验收"，本任务在任何解释下都不成立。

**独立复核（可复现）**：直接访问本应由 P02-01/P02-02 提供的公开名字，全部显式 `NotImplementedError`（这是 P01-01 刻意的失败即报设计，值得肯定）：

```text
logistics_domain.entities       -> NotImplementedError (P02-02/P02-03: 32 domain entities per DOMAIN_CATALOG)
logistics_domain.states/units/ids -> NotImplementedError (P02-01)
logistics_contracts.dto/mapping/export_schema -> NotImplementedError (P02-04/P05-01/P06-01)
```

## 4. 相邻回归与工程基础检查（当前候选）

下表为第 1 轮结果；第 2 轮在 2026-09-15 重跑了同一批检查（回归 `uv run pytest -q` → 187 passed、所有权 `violations=0`、`uv lock --check` exit 0、G02 沙箱仍 5/27），逐项一致，原始输出见 `logs/reverify-*.log`。

| 检查 | 命令 | 结果 | 日志 |
| --- | --- | --- | --- |
| 全量测试回归 | `uv run pytest -q` | **187 passed / 0 failed / 0 skipped**，exit 0 | `logs/regression-pytest.log` |
| 分层检查（verbose） | `uv run python scripts/check_architecture.py --verbose` | 7 层 7 模块，`violations=0`，exit 0 | `logs/cmd2-architecture-verbose.log` |
| 所有权/迁移检查 | `uv run python scripts/check_ownership.py --json` | `passed=true`，`violations=[]`，`default_owner_fallbacks=[]`，865 文件扫描，exit 0 | `logs/ownership.log` |
| 依赖锁一致性 | `uv lock --check` | exit 0 | `logs/lock-check.log` |
| 冻结安装 | `uv sync --frozen` | exit 0 | `logs/uv-sync.log` |
| 存量 Gate 复核 | `gates.py --phase 01 --check-only` | exit 1，`status=failed`，`failed_checks=['zcode-precheck:P01-01','zcode-precheck:P01-02','zcode-precheck:P01-03','codex-review']` | `logs/gates-phase01-check-only.log` |
| Phase 02 Gate 沙箱运行 | `gates.py --phase 02 --out-dir tmp/zcode-g02-dryrun` | exit 1，`G02: 5/27`；4 条 `P02-0X-cmd1` 全 exit 4；`previous-gate:G01 status=failed`；4 任务 DSH 证据/文档/报告/ZCode 记录全缺；`codex-review` 缺失 | `logs/gates-phase02-dryrun.log` |

（`gates.py --phase 02 --check-only` 在从未签收的 Gate 上是**空操作**：打印 "nothing signed yet" 并 exit 0。**exit 0 不代表 Phase 02 就绪**，这点容易误读，已在给 Codex 的风险项中列出。）

## 5. 确定缺陷清单（含路径与复现）

### D1 · P02-02 零交付【阻断本任务】

- 证据：第 1 节存在性矩阵；`logs/cmd1-pytest.log`（exit 4）；`logs/gates-phase02-dryrun.log` 中 `P02-02-cmd1: exit_code=4`、`dsh-evidence:P02-02: missing`、`docs:docs/implementation/P02-02.md: missing` 等 6 项 P02-02 失败。
- 影响：本任务无候选，无法做任何实质预验收（求解/边界/失败副作用/错误码均无对象）。
- 归属：DSH / P02-02。

### D2 · 前置未满足【阻断本任务】

- `P02-01` 零交付：`packages/domain/src/logistics_domain/` 下只有 `__init__.py`（P01-01 空壳），无 `ids.py`/`units.py`/`states.py`；`docs/implementation/P02-01.md`、`reports/P02-01.md`、`artifacts/handoffs/P02-01/dsh/evidence.json` 均缺失。`TASK_GRAPH.md:46-47` 规定 `P02-02` 依赖 `G01, P02-01`。
- `G01` 未通过：`artifacts/gates/G01.json` 的 `status=failed`，`failed_checks` 缺 `zcode-precheck:P01-01/02/03` 与 `codex-review`；`PHASE_GATES.md` 写明 `G01` 失败阻塞"Phase 02及以后"。
- 影响：即使 P02-02 立刻交付，也不满足"前置证据有效"的开工前提；按 Prompt"若前置缺失/失败，报告具体阻断，禁止跳 Gate"。

### D3 · 前端工作区声明了测试脚本但未安装 vitest【非阻断 P02-02，属 P01-01 范围】

- `apps/frontend/package.json` 声明 `"test": "vitest run"`，但该包**没有任何 `dependencies`/`devDependencies`**，且存在 `apps/frontend/vitest.config.ts`、`apps/frontend/src/test/setup.ts`。`node_modules/vitest` 不存在。
- 复现：`npm --workspace @logistics/frontend run test --if-present` → `'vitest' is not recognized...`，**exit 1**（`logs/frontend-test.log`）。
- 影响：`.github/workflows/ci.yml:95` 的 "Frontend tests" 步骤是必跑步骤，`--if-present` 只在脚本缺失时跳过，此处脚本存在 → **CI 的 frontend job 必然失败**。注意这不是 P02-02 引入的，且本任务未触及前端。

### D4 · `npm run test:e2e:list` 以非零退出，但 CI 当作必过步骤【非阻断 P02-02，属 P01-01/P01-02 范围】

- 复现：`npm run test:e2e:list` → `Error: No tests found / Total: 0 tests in 0 files`，**exit 1**（`logs/frontend-e2e-list.log`）；`ci.yml:98` 的 "List end-to-end specs" 是必跑步骤。
- `playwright.config.ts` 注释已说明"无 spec 时列出 0 个用例是合法的"，但没有处理非零退出码，二者矛盾。建议 CI 侧显式接受 `--list` 的空结果（或该步骤标记 `continue-on-error` 并在 P24-01 后再收紧），并把"零用例不得当验收证据"继续交给 Gate 执行器把关。

### D5 · Lint 未纳入 CI，且当前规则集与中文源码约定冲突【非阻断，工程配置问题】

- `pyproject.toml` 声明 `ruff>=0.9`（dev 组）并配置 `select = ["E","F","I","UP","B","SIM","RUF"]`，但 `.github/workflows/ci.yml` 与仓库脚本中**没有任何步骤调用 ruff**，即"配了不跑"。
- 实测（仅目标树 `apps/*/src packages/*/src tests scripts`）：`uv run ruff check ...` → **39 errors**，exit 1（`logs/lint-ruff-scoped.log`）。其中绝大多数是 `RUF001/RUF002`（"字符串/文档串含歧义全角标点"）——本项目源码注释、docstring 与错误文案**通篇使用中文全角标点**，该规则与项目语言约定直接冲突；其余为 `RUF022`（`__all__` 未排序）、`UP017`、`UP031`、`SIM300`、`F401`、`F841`、`RUF005`，全部落在 P01-01/P01-02/P01-03 的既有文件里，**无一条来自 P02-02**（该任务无文件）。
- 全仓范围运行 `uv run ruff check .` 会额外扫入只读旧基线 `demo/`，输出 1.5MB、数千条，信噪比为零（`logs/lint-ruff.log`，保留原始输出供查证）。
- 结论：lint 目前**不是该项目的强制检查**，因此不构成 P02-02 的验收项；但若后续要把 ruff 纳入 CI，必须先解决"扫描范围 + 中文标点规则"两件事，否则会引入大批与业务无关的阻断。

### D6 · Gate revision 由易失的会话/暂存文件构成，导致记录一签即过期【非阻断，P01-02 范围】

- `scripts/gates.py:43` 的 `EXCLUDED_FROM_REVISION` 只排除 `artifacts/gates`、`artifacts/e2e`；`compute_revision()`（`scripts/gates.py:327-342`）实际遍历整棵树，其中**三分之二以上的行来自非源码**：本次实测该枚举共 1167 行，`.mimosa/**` 451 行（约 39%）、`tmp/**` 423 行（约 36%）、其余源码与文档约 293 行。`demo/`（只读基线）被显式排除，但 `tmp/package-verification/**/demo/**` 这类同样只读的副本没有被排除。
- **已定性的根因（可复现）**：`.mimosa/hook-state/<session>.json` 由 Agent 宿主机在**每次工具调用**时重写。两次连续工具调用之间不碰任何源码，快照差异恰好只有这一项（外加我本轮新增的证据文件）：

  ```text
  delta since the previous tool call (no source file touched by hand):
    added  : 5 {'artifacts': 3, 'tmp': 2}
    changed: 1 {'.mimosa': 1}
    sample changed: ['.mimosa/hook-state/sess_b3dd4ebe-....json']
  ```

  （`logs/revision-volatility.log`；快照用执行器自身的 `GateRunner.compute_revision()` 生成。）
- **实测量级**：本轮审查中 G02 的 revision 标签先后为 `content-sha256:13321610…` → `94eafe09…` → `f9ba8e61…`，每次移动都只对应"我多跑了一条命令/多写了一份日志"。这直接解释了 `G01.json` 记录的 `content-sha256:ab054daf…` 为何无法复现、`--check-only` 为何恒报 `STALE recorded revision`。
- **同时被实测排除的假设**：我原先怀疑"门禁自己跑 pytest 会改 `.pytest_cache` 从而自我失效"。实测在单次 bash 调用内跑 62 个用例前后，`.pytest_cache/v/cache/nodeids` 与 `lastfailed` 的哈希**未变**（`logs/pytest-cache-attribution.log`），故该假设**不成立**，请勿据此归因。真正的驱动因素是上面的 `.mimosa` 会话状态。
- 影响：任何 `--revision auto` 记录的 Gate 证据，在下一步 Agent 动作后即不可复现；`dependency_evidence_hashes` 与其余哈希绑定也随之失去意义。这不是 P02-02 的缺陷，但它会让"重跑 Gate 即恢复"的做法永远得不到一致结果。
- 缓解：预验收记录自身通过 `status` + `verified_input_hashes` 校验，**不**依赖 Gate revision，所以写入 ZCode 记录不会让记录本身失效。建议把 revision 输入收敛为真正的源码/契约/锁文件清单（或把 `.mimosa/**`、`tmp/**`、`.pytest_cache/**` 一并加入排除），否则阶段 Gate 的 `code_revision` 只能是"一次性快照"而非可核对指纹。

### D7 · 交接契约文档缺失（既有 `ARCH-0004`，本次继续成立）

- 仓库不存在 `docs/workflow/README.md`、`docs/workflow/02-ZCODE-PRECHECK.md`、`HANDOFF_CONTRACT.md`；`scripts/gates.py:305-311` 的注释也承认这点并自行固定路径约定。我按其约定 + 用户指令落盘（第 8 节），但**记录字段集合仍无契约来源**，请项目侧尽快决定。

### D8 · Node 基线漂移【观察项，非阻断】

- `.node-version` = `22`，`package.json` 的 `engines` 为 `>=22 <25`，`ci.yml` 用 `node-version-file: .node-version` 安装 Node 22；而本机运行时与 `artifacts/gates/G01.json` 记录的 `environment_fingerprint.node` 均为 `v24.18.0`。
- 影响：CI 与本地不是同一个 Node 基线，前端类任务（P24 起）可能出现"本地过、CI 挂"或反之。当前的 `engines` 区间不构成违规，但在 P01-01 声称"Node 22 兼容基线"的语境下应显式对齐或记录为何可接受。
- 归属：P01-01 / CI。

## 6. 给 Codex 的重点风险与复核优先级

1. **不要用 `gates.py --check-only` 的 exit 0 判断 Phase 02 就绪**：从未签收的 Gate 上它是空操作（见第 4 节）。需要真实结论就用非官方 `--out-dir` 沙箱跑一次（我留了 `tmp/zcode-g02-dryrun/G02.json`）。
2. **`G01` 是当前唯一的硬阻塞链源头**：缺 3 份 `artifacts/handoffs/P01-0X/zcode/precheck.json` 与 `artifacts/gates/G01-codex-review.json`。只补 P02-02 不解决任何问题；`G01` 记录中 `code_revision` 已与当前树不一致（D6），补记录前需先决定 revision 口径。
3. **`check_architecture.py` 的 exit 0 在空壳状态下是假信号**：本任务零新增代码时它必然通过。Gate 断言里"分层检查通过"在 Phase 02 必须与"实体已存在"联合判定，否则会出现"空仓也通过"。
4. **D3/D4 会让 CI 的 frontend job 红**，虽与 P02-02 无关，但会掩盖后续真实失败；建议在 Phase 02 开工前先修 `apps/frontend/package.json`（补 vitest/vite 依赖或先移除 `test` 脚本并同步 `package-lock.json`）与 CI 的 e2e list 步骤。
5. **D5**：若打算在 P02-02 之后启用 ruff，请先定范围与中文标点规则，否则新交付的 `orders.py`/`resources.py`/`entities.py` 只要写中文 docstring 就会立刻触发 `RUF001/RUF002`。
6. **`demo/` 只读性**：`resources.py`/`entities.py`/`states.py` 在只读旧基线 `demo/backend/app/` 下已存在同名文件（0.1 骨架），P02-02 必须新写于 `packages/`，不得从教学探针导入或复制；验收时需比对以防"搬运旧实现当交付"。
7. **测试数据的时效**：`docs/plan/TEST_FIXTURES.md` 的正例规范已冻结（T1 载重 400000g×2 对车容 800000g 等），但 `data/scenarios/` 目前只有 `README.md`，生成物属 `P04-01`。P02-02 的测试允许按该文档局部声明字段，**不应**以"缺数据文件"为由跳过 Test Case 1/2。

## 7. 我修改了什么（供 Codex 独立查验）

**修改的生产代码/测试/既有文档：无。** 本次为"无可验收对象"的阻断判定，不存在需要修复的白名单内错误；我刻意不改 `apps/frontend/package.json`（D3，不在 P02-02 Files 白名单内，且改动会牵动 `package-lock.json`，应先由责任任务决定口径），也不补写任何缺失的实现或测试。

**新增文件（仅预验收记录，均为本角色产物）**：

- `docs/handoffs/P02-02/zcode.md`（本报告）
- `artifacts/handoffs/P02-02/zcode/evidence.json`
- `artifacts/handoffs/P02-02/zcode/precheck.json`（Gate 执行器约定的同内容记录，`status=BLOCKED`，fail-closed）
- `artifacts/handoffs/P02-02/zcode/logs/`（28 份原始日志，含第 2 轮 `reverify-*.log` 5 份）
- `artifacts/handoffs/P02-02/zcode/build-evidence.py`（可复跑的证据生成脚本：只读仓库、不启进程、不拼 shell；重跑即可复现 evidence.json/precheck.json 的全部哈希）
- `tmp/zcode-g02-dryrun/`、`tmp/zcode-g02-dryrun-p2/`（两轮 G02 非官方沙箱证据 + 日志，位于 `.gitignore` 忽略的 `tmp/` 下）

**DSH 原报告**：本任务不存在 DSH 报告可保留（`docs/handoffs/P02-02/dsh.md`、`artifacts/handoffs/P02-02/dsh/evidence.json` 均缺失），我未创建、未改写任何 DSH 侧记录。

## 8. 记录落盘约定（因 `ARCH-0004` 而需项目侧确认）

- 用户指令：`docs/handoffs/P02-02/zcode.md` + `artifacts/handoffs/P02-02/zcode/evidence.json` + 原始日志。
- Gate 执行器硬编码：`artifacts/handoffs/P02-02/zcode/precheck.json`，校验 `status == "Z_PRECHECK_PASSED"` 且 `verified_input_hashes` 未漂移。
- 两者不冲突，故我**同时落盘** `evidence.json` 与 `precheck.json`（内容一致）。`status` 取 `BLOCKED`：执行器会以 `status='BLOCKED' (expected 'Z_PRECHECK_PASSED')` 失败关闭，这正是期望行为——本任务确实未通过预验收。DSH 补交后需重新发起预验收，不能沿用本记录。
- **已实测该失败关闭生效**：重新用沙箱跑 G02 后，执行器对该文件的判定为
  `[FAIL] zcode-precheck:P02-02: artifacts/handoffs/P02-02/zcode/precheck.json: status='BLOCKED' (expected 'Z_PRECHECK_PASSED')`
  ——说明路径与字段被正确识别，且不会被我这份"未通过"的记录误判为通过（原始输出见 `logs/gates-phase02-precheck-recognized.log`）。

## 9. 已修复 / 未修复 / 未验证清单

**已修复**：无（无可修复对象；本角色不代替开发）。

**未修复（已定位、需责任方处理）**：

| 编号 | 摘要 | 责任任务 | 阻断 |
| --- | --- | --- | --- |
| D1 | P02-02 零交付 | DSH / P02-02 | 是（本任务） |
| D2 | P02-01 零交付 + G01 failed | DSH / P02-01、P01-01~03 + Codex | 是（本任务） |
| D3 | 前端声明 `vitest run` 但未安装 vitest → CI frontend job 失败 | P01-01（或 P24-01） | 否 |
| D4 | `test:e2e:list` 空结果 exit 1 与 CI 必跑步骤矛盾 | P01-02 | 否 |
| D5 | ruff 未入 CI 且 `RUF001/002` 与中文标点约定冲突 | 工程配置 | 否 |
| D6 | Gate revision 由 `.mimosa/**`、`tmp/**` 等易失文件构成，记录一签即不可复现 | P01-02 | 否 |
| D7 | 交接契约文档缺失（`ARCH-0004` 延续） | 项目管理侧 + P01-03 | 否（阻断 G01 签收） |
| D8 | `.node-version` 钉 22 而本地/G01 指纹为 Node 24 | P01-01 / CI | 否（观察项） |

**未验证 / 无法验证（工具或阶段未到，不臆造通过）**：

- 求解/容量/时间窗/温控/仓储占用/库存/交接等业务语义：Phase 06+ 才有引擎，P02-02 只涉及领域模型与单位表示，本次无对象。
- Schema/OpenAPI/生成客户端一致性：生成器尚未建立（`scripts/export_contracts.py` 属 P02-04，`apps/frontend/scripts/generate-contracts.mjs` 属 P24-02），**本次记为"工具未建成（所属阶段未到）"，不是"检查通过"**。
- 静态类型检查：`pyproject.toml` 未配置 mypy/pyright，Phase 01 尚未建立类型检查工具；分层检查只覆盖导入方向。
- 真实 PostgreSQL / 真实 OR-Tools / SimPy / 浏览器 E2E：阶段未到。
- CI 本体：本检出**无 `.git`**，`ci.yml` 的 `git ls-files`、`git grep`、`git diff --exit-code -- package-lock.json` 无法按其原文执行；我改跑等价的无 git 版本（见下）。
- `npm ci`：未重跑（避免重建 `node_modules`），沿用 G01 的 exit 0 记录。

## 10. 基础安全检查（针对当前变更集）

当前变更集为空（P02-02 无文件），故按"对现状做最小基线核查"执行：

- **凭据**：目标树无 `.env`/`.env.*`/`*.pem`/`*.p12`/`id_rsa*`；`sk-…`/`AKIA…` 字面量 0 命中；`.gitignore` 覆盖 `.env*`、`tools/bin/`、`node_modules/`、`.venv/`（`logs/secret-hygiene.log`）。CI 的 `secret-hygiene` job 因无 git 不能原样运行，此为等价替代，已在第 9 节声明。
- **命令注入**：`apps/`、`packages/`、`scripts/`、`tests/` 中无 `shell=True`、`os.system`、`eval(`、`exec(`、`pickle.loads`；Gate 执行器以 argv 数组执行命令（`logs/security-injection-scan.log`）。
- **SQL 注入入口**：当前无数据库访问代码（P03+ 才有），无拼接/format/f-string 组装 SQL 的入口，**该验收条件在本任务范围内不适用，而非"已通过"**。
- **鉴权/对象范围/日志脱敏**：P02-02 是纯领域模型（domain 不引入框架、不引 telemetry、不落日志），HTTP 边界与脱敏属 P05-01/P37；无对象可测。
- **依赖变化**：本次无依赖变更；`uv lock --check` exit 0。
- **未对外部生产目标做任何扫描**。

## 11. 证据索引

| 证据 | 路径 |
| --- | --- |
| 机器证据（输入哈希、命令与退出码、缺陷表、日志清单） | `artifacts/handoffs/P02-02/zcode/evidence.json` |
| Gate 执行器约定记录（同内容，`status=BLOCKED`） | `artifacts/handoffs/P02-02/zcode/precheck.json` |
| 证据生成脚本（可复跑复现全部哈希） | `artifacts/handoffs/P02-02/zcode/build-evidence.py` |
| 预验收记录被识别且失败关闭 | `logs/gates-phase02-precheck-recognized.log` |
| P02-02 强制命令日志（2 条） | `artifacts/handoffs/P02-02/zcode/logs/cmd1-pytest.log`、`cmd2-architecture.log` |
| 回归与工程基础日志 | `logs/regression-pytest.log`、`cmd2-architecture-verbose.log`、`ownership.log`、`lock-check.log`、`uv-sync.log` |
| Gate 复核日志 | `logs/gates-phase01-check-only.log`、`gates-phase02-check-only.log`、`gates-phase02-dryrun.log`、`gates-phase02-precheck-recognized.log` |
| Lint 日志 | `logs/lint-ruff-scoped.log`（目标树，39 errors）、`logs/lint-ruff.log`（全仓，含只读 `demo/`） |
| 前端与安全日志 | `logs/frontend-test.log`、`frontend-e2e-list.log`、`secret-hygiene.log`、`security-injection-scan.log` |
| 接口缺失复现 | `logs/probe-interfaces.log` |
| D6 复现数据与自失效实验 | `logs/revision-volatility.log`、`logs/pytest-cache-attribution.log`、`logs/self-staleness-experiment.log`、`logs/self-staleness-attribution.log`；快照原始数据 `tmp/rows-{before,after,now}.json`、`tmp/pc-before.json` |
| 第 2 轮复核日志 | `logs/reverify-cmd1-pytest.log`、`reverify-cmd2-architecture.log`、`reverify-regression.log`、`reverify-gates-phase02.log`、`reverify-baseline-checks.log` |
| G02 非官方沙箱证据 | `tmp/zcode-g02-dryrun/G02.json`、`tmp/zcode-g02-dryrun/G02-logs/` |
| 既有 Gate 状态 | `artifacts/gates/G01.json`（`status=failed`） |
| P02-02 任务书 / 依赖图 / 冻结文档 | `docs/prompts/02-domain/P02-02-master-entities.md`、`TASK_GRAPH.md`、`docs/plan/{TASK_MANIFEST.json,PHASE_GATES.md,TEST_FIXTURES.md}`、`docs/architecture/{DOMAIN_CATALOG.md,DATA_CONTRACTS.md,CONTRACT_FREEZE.md}` |
| 架构问题登记 | `docs/architecture/issues/README.md`（`ARCH-0004`、`ARCH-0005` 与本报告相关） |
