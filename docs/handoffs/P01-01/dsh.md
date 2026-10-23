# P01-01 · DSH → ZCode 交接说明

> **当前有效轮次：N03-R02 / 2026-10-04（P02-01 包 marker 变更后的 P01-01 刷新轮）。** 最新结论在文末「交接 · 刷新轮 `N03-R02`」小节；其上是 N03-R01 修复轮与 N03 刷新轮，最前为首轮。各轮交接原文、旧轮 `evidence.json` 与全部日志已逐字节归档到 `artifacts/handoffs/P01-01/dsh/archive-prior-rounds/`（`2026-10-04-pre-n03/`、`2026-10-04-pre-n03-r01/`、`n03-r02/`）。

| 项目 | 值 |
| --- | --- |
| Task ID | `P01-01` |
| 交付方 | DSH（初步开发） |
| 交接对象 | ZCode（独立预验收，按 `docs/workflow/02-ZCODE-PRECHECK.md`——该文件当前不存在，见"流程缺口"） |
| 本角色状态 | `READY_FOR_ZCODE` |
| 阶段 Gate | `G01`（未签收；Phase 02 及之后禁止启动） |
| 证据入口 | `artifacts/handoffs/P01-01/dsh/evidence.json`、`docs/implementation/reports/P01-01.md` |

## 1. 交付范围

只交付"目标 Monorepo 与可复现依赖环境"：uv workspace + npm workspace + 六个包与后端应用的 src-layout 骨架 + 真实锁文件 + Playwright 配置 + 两条 Test Case 的真实测试。**没有任何业务能力**。

## 2. 进入本任务时的前置阻断（必须先看清）

按 TASK_GRAPH 与 PHASE_GATES 逐项核验 `G00` 的依赖后，实际状态是：

| 前置项 | 核验结果 |
| --- | --- |
| `P00-01` 交付物（`docs/architecture/BASELINE_INVENTORY.json`/`.md`、`MIGRATION_MAP.md`、任务文档与报告） | 全部缺失 |
| `P00-02` 交付物（`CONTRACT_FREEZE.json`/`.md`、`issues/README.md`、任务文档与报告） | 全部缺失 |
| `P00-03` 交付物（`docs/plan/GATE_EXECUTION_CONTRACT.md`、任务文档与报告） | 全部缺失 |
| `artifacts/gates/G00.json` | 不存在（G00 未记录） |
| 目录 `docs/workflow/`、`docs/handoffs/`、`contracts/changes/` | 不存在 |

规划检查器给出的原始失败证据（在补齐交付物之前）：

```text
python tools/ai_coding_plan/validate_plan.py --self-test --record-g00
exit code 1
errors: ["G00 NOT recorded: Phase00 deliverables/reports missing:
  docs/architecture/BASELINE_INVENTORY.md, docs/architecture/MIGRATION_MAP.md,
  docs/implementation/P00-01.md, docs/implementation/reports/P00-01.md,
  docs/architecture/CONTRACT_FREEZE.json, docs/architecture/CONTRACT_FREEZE.md,
  docs/architecture/issues/README.md, docs/implementation/P00-02.md,
  docs/implementation/reports/P00-02.md, docs/implementation/P00-03.md,
  docs/implementation/reports/P00-03.md"]
```

因为 `P01-01.deps == ["G00"]` 且 G00 无有效证据而无法启动 Phase 01，本任务先按"前置缺失/失败 → 报告具体阻断并修复前置任务，禁止跳 Gate"执行了 Phase 00 的补齐，然后由**冻结的规划检查器**（`--record-g00`，唯一可写 `G00.json` 的入口）记录 G00。当前 `artifacts/gates/G00.json` 为 `status: passed`，`scope: "Phase00 document contract verification only"`，其 `limitations` 明确写着 "No application gate has been executed. G01 must establish the runtime gate runner."

请重点判定：该前置修复是否属于越权、`BASELINE_INVENTORY.json` 的覆盖口径是否可接受、以及是否应把 `tools/ai_coding_plan/` 下新增脚本收编到 `scripts/`。

## 3. 需要独立复核的边界

1. **六包导入必须来自真实安装**：`tests/integration/test_p01_01_workspace_bootstrap.py` 用 `python -I -c` 隔离子进程导入，并断言每个模块解析到本成员 workspace src 目录或 `.venv` 内，同时断言 `importlib.metadata.distribution(...).read_text('direct_url.json')` 存在。请独立复跑，并确认这不是"靠 cwd 生效"的假通过。
2. **锁文件不是手写**：`uv.lock`/`package-lock.json` 由真实安装生成；证据记录其 sha256，测试断言当前值等于证据值。请用 `uv lock --check` 与 `npm ci` 复核。
3. **用例 2 的真实性**：`npm ci` 连续执行两次，前后 `package-lock.json` sha256 必须一致。请确认执行的是 `npm ci` 而不是 `npm install`（后者可能重写锁）。
4. **旧 demo 未被覆盖**：`demo/` 173 个登记文件的路径+内容指纹与 `demo.zip` sha256 都在测试中核对。请另用 `docs/architecture/BASELINE_INVENTORY.json` 独立复算一次。
5. **失败显式化**：七个 `__init__.py` 对未交付名字抛 `NotImplementedError`。请确认没有 TODO 占位核心逻辑、没有返回固定成功、没有吞异常。

## 4. 未测试项（ZCode 不必重复 DSH 已做项，但需覆盖这些）

- Node **22** 上的实际行为（本机只有 24.18.0；`.node-version` 固定 22）。建议在 Node 22 复跑 `npm ci` 与 `npm run test:e2e:list`。
- `scripts/gates.py` 的失败关闭行为（P01-02 交付，本任务不存在）——G01 的"Gate 执行器非零命令必失败"断言目前**无法验证**。
- `scripts/check_architecture.py` 的分层检查（P01-02 交付）——本任务只在单元测试里做了依赖方向静态断言。
- 任何 HTTP/数据库/求解器/仿真/LLM/浏览器验收。
- CI（`.github/workflows/ci.yml`）从未运行（P01-02 交付）。

## 5. 证据索引

| 证据 | 路径 |
| --- | --- |
| 机器证据（锁 hash、工具版本、demo 指纹、三条命令） | `artifacts/handoffs/P01-01/dsh/evidence.json` |
| 原始命令日志 | `artifacts/handoffs/P01-01/dsh/logs/{pytest,uv_sync_frozen,npm_ci}.log` |
| 命令汇总（argv、exit_code、log hash、测试计数） | `artifacts/handoffs/P01-01/dsh/logs/validation-summary.json` |
| 任务文档 | `docs/implementation/P01-01.md` |
| 完成报告（含已知限制与剩余风险） | `docs/implementation/reports/P01-01.md` |
| 前置 Gate 证据 | `artifacts/gates/G00.json`、`artifacts/gates/G00-checks.log` |

## 6. 流程缺口（需要项目管理侧补齐）

以下路径由 `P01-01` 任务书引用，但在本检出中均不存在：

- `docs/workflow/README.md`、`docs/workflow/02-ZCODE-PRECHECK.md`（本任务书要求"下一步使用"该文件）
- `docs/workflow/HANDOFF_CONTRACT.md`（本任务书引用为交接证据规范）
- `docs/handoffs/`、`contracts/changes/`
- `docs/architecture/issues/` 在本任务中首次创建（P00-02 白名单包含其 `README.md`）

本任务的交接按任务书本身的要求执行：DSH 写 `docs/handoffs/P01-01/dsh.md` 与 `artifacts/handoffs/P01-01/dsh/evidence.json`；ZCode 的审查证据路径应由 `HANDOFF_CONTRACT` 规定，在该文件补齐前请与项目管理侧确认。


---

# 交接 · 刷新轮 `N03 / 2026-10-04`（当前有效）

> 本节取代上方首轮结论。首轮 `dsh.md` 原文（sha256 见 `archive-manifest`）与旧轮 `evidence.json`、全部日志已逐字节归档到 `artifacts/handoffs/P01-01/dsh/archive-prior-rounds/2026-10-04-pre-n03/`。

| 项 | 值 |
| --- | --- |
| Task ID / round | `P01-01` / `N03-2026-10-04` |
| 本轮主写者 | DSH-A（N03 交接整合者，本会话） |
| 本轮范围 | 仅刷新自身交接与证据；**未改任何源码、测试、锁、所有权、契约或规划** |
| 本角色状态 | **`READY_FOR_ZCODE`** |
| 阶段 Gate | `G01`（**仍未签收**：官方 `artifacts/gates/G01.json` `status=failed`，sha256 `4383ccac45dddcb465410ce4f4e2d0db7828d340e4d61ed49f87249d3f75c4d4`，本轮未写未改） |
| 证据入口 | `artifacts/handoffs/P01-01/dsh/evidence.json`、`artifacts/handoffs/P01-01/dsh/logs/n03-2026-10-04/` |
| 下一执行者 | ZCode N04（独立预验收；不签官方 Gate） |

## 0. 本轮绑定的候选与依赖证据

- 候选（本轮两次实测一致）：`code_revision = content-sha256:23930f7ae4218778ecbfb33367210f821fb53a1e9d39a2dd195cf2b4f0616c4c`，`dirty_tree_hash = content-sha256:89f1fe4cd1ec0fb04445390586e26534b2a73f71d4f47ebfde3c78626a1957e3`，77 个白名单文件；用 `scripts/gates.py` 的 `GateRunner.relevant_manifest_rows()` 独立复算（`tmp/N03/candidate/candidate-identity.py`）。
- `G00`：`artifacts/gates/G00.json` sha256 `c5e57a6d250ff83f9ceed524f6219a3b1cb9474697a3354b5f102fe24c3bb7e4`，`status=passed`，`finished_at=2026-10-04T14:48:59Z`，reviewer 为 N02-R02 独立会话；`G00-checks.log` sha256 `55e1ad48e648674703ffa0eaa0082757fc31e8c9f5c1c1662d48a5b70dc34488`。我用 `tmp/N03/precondition/g00-drift-audit.py` 独立复算 25/25 输入与日志 hash 全部新鲜（exit 0）。
- 上方首轮表格中"G00 未记录/交付物缺失"一类描述是 2026-09-13/14 的历史事实，已被取代；历史记录本身未删除。

## 1. 本轮实跑结果（真实计数与退出码，取自原始日志）

| 命令 | 退出码 | 实测结果 | 原始日志 |
| --- | --- | --- | --- |
| `uv run pytest tests/unit/test_p01_01_workspace_bootstrap.py tests/integration/test_p01_01_workspace_bootstrap.py -q` | 0 | **56 passed / 0 failed** | `logs/n03-2026-10-04/p01-01-cmd1-pytest.log` |
| `uv sync --frozen` | 0 | `Checked 39 packages`，锁未被重解析 | `logs/n03-2026-10-04/p01-01-cmd2-uv-sync-frozen.log` |
| `npm ci`（第 1 次） | 0 | 安装成功 | `logs/n03-2026-10-04/p01-01-cmd3-npm-ci-run1.log` |
| `npm ci`（第 2 次） | 0 | 安装成功；`package-lock.json` sha256 前后一致 `fae1a02cb4ed64be91e1af371021762bb5e5183c0312c39c0575ee91b0f01458`（Test Case 2） | `logs/n03-2026-10-04/p01-01-cmd3b-npm-ci-run2.log` |

`uv.lock` sha256 仍为 `89f78a20a840955fcfe5a13435b6aad9c5ebb09420123812c4728b9413fe86c5`，与首轮证据一致；本轮未改锁。

## 2. 阶段回归状态：当前红灯（外部并发写者，非本任务实现缺陷）

`uv run pytest tests/unit tests/integration -q` 本轮两次实测均为 **exit 1 / 225 passed / 1 failed**：

- 失败用例：`tests/integration/test_p01_03_migration_governance.py::test_test_case_2_unmapped_status_is_rejected_without_side_effects`
- 直接原因：该用例对整个工作根做字节快照并断言前后相等；并发运行的 WorkBuddy-AI 辅助会话正在持续改写 `tmp/orchestration/workbuddy-ai/reuse/.probe/sqlalchemy.json`，于是被记成"被拒转换改动了仓库"。失败日志里差异项恰好只有该文件。
- 原始失败日志（保留）：`logs/n03-2026-10-04/phase01-full-regression-attempt1.log`、`…-attempt2.log`。
- 本轮早些时候在该写者尚未活动时，同一命令曾实测 **226 passed / exit 0**；该次原始日志被后续 attempt 覆盖，**因此不作为证据**，仅如实记录。
- 已登记缺陷：`DEF-N03-02`（复现、责任方与限定修复范围见 `tmp/N03/defects/`）。本轮**未**修改该测试。

## 3. 实际作者与分区贡献

| 分区 | 实际作者 / 会话 | 角色 | 涉及文件 |
| --- | --- | --- | --- |
| `P01-01/impl` | DSH（A 范围）实现会话（首轮/返工轮） | 本任务主实现者（主写者） | manifest `allowed_files`；字节本轮未改动 |
| `P01-01/round-N03-2026-10-04` | DSH-A（N03 整合者，本会话） | 仅交接与证据刷新 | `docs/handoffs/P01-01/dsh.md`、`artifacts/handoffs/P01-01/dsh/**`、`tmp/N03/**` |
| `OWNERSHIP/AGENTS.md` | **Codex 治理会话（2026-10-01/03）** | 治理修复，**非 DSH 交付物** | `OWNERSHIP.json` |
| `DEF-N03-01` | **编排/Codex 会话（2026-10-04）** | 把两个越界记忆文件移出工程根；**未改** `OWNERSHIP.json`、检查脚本或测试断言 | `.workbuddy/**`、`.workbuddy-ai/**`（已移出） |
| `N02-R02/G00` | **Codex N02-R02 独立审查会话（2026-10-04）** | 按当前输入恢复官方 G00 | `artifacts/gates/G00.json`、`G00-checks.log`、`CONTRACT_FREEZE.*` |

## 4. 请 ZCode 独立复核的边界

1. **六包导入不是靠 cwd 生效**：`tests/integration/...` 用 `python -I -c` 隔离子进程导入并断言解析到成员 workspace 的 src 或 `.venv`，请独立复跑。
2. **锁可复现**：`uv lock --check` 与连续两次 `npm ci` 后 `package-lock.json` 不变。
3. **旧 demo 未被覆盖**：用 `docs/architecture/BASELINE_INVENTORY.json` 独立复算 `demo/` 173 项指纹与 `demo.zip` sha256。
4. **未实现即显式失败**：各包 `__init__.py` 对未交付名字抛 `NotImplementedError`，无 TODO 占位、无固定成功。

## 5. 失效条件与停止条件

- 任何白名单文件改动都会产生新候选，使本轮 `evidence.json`、日志绑定与 G00 引用失效；届时须重跑并重算。
- 官方 `G01.json` 仍为 `failed`；三份 ZCode precheck 与 `G01-codex-review.json` 只能由对应审查者写入，DSH 未写、未冒签。
- 本轮在写出上述产物后**停止修改该候选**，交 ZCode N04 独立预验收；不启动 P02，不签任何 Gate。


---

# 交接 · 修复轮 `N03-R01 / 2026-10-04`（当前有效）

> 本节取代上方 N03 刷新轮与首轮结论。上一轮（schema 不兼容的 N03 刷新）的 `evidence.json`、`dsh.md` 与全部日志已逐字节归档到 `artifacts/handoffs/P01-01/dsh/archive-prior-rounds/2026-10-04-pre-n03-r01/`；首轮记录仍保存在 `…/2026-10-04-pre-n03/`。

| 项 | 值 |
| --- | --- |
| Task ID / round | `P01-01` / `N03-R01-2026-10-04` |
| 本轮主写者 | DSH-A（限定交接修复，本会话） |
| 本轮范围 | 仅 `docs/handoffs/P01-01/dsh.md` 与 `artifacts/handoffs/P01-01/dsh/**`（归档、新日志、evidence） |
| 本角色状态 | **`READY_FOR_ZCODE`** |
| 阶段 Gate | `G01`（**仍未签收**；官方 `artifacts/gates/G01.json` `status=failed`，sha256 `4383ccac45dddcb465410ce4f4e2d0db7828d340e4d61ed49f87249d3f75c4d4`，本轮未写未改） |
| 证据入口 | `artifacts/handoffs/P01-01/dsh/evidence.json`（sha256 `0eb8782c1d602a1b5c2f9b2df023ce8dffe34f999d84c2e6246695cdac901b9e`） |
| 下一执行者 | ZCode N04-R01 受影响重验（不签官方 Gate） |

## 1. 缺陷 `ZC-N04-R01-P01-01-F01` 与修复

- **缺陷**：N03 刷新轮把 `evidence.json` 的 `artifacts` 由字典改成列表，并删除了 `python_workspace_members`、`dependencies_lock`、`tool_versions`、`legacy_demo`；而字节未变的 `tests/integration/test_p01_01_workspace_bootstrap.py` 仍从同一文件读取这些字段，于是必需命令实测 `7 failed / 49 passed`（exit 1）。N03 记录的 56 通过发生在重写 evidence **之前**，不能证明交付态通过。
- **修复**：在同一文件内恢复被消费的字段与形状，并保留 N03 的治理信息（`candidate`、`dependency_evidence`、`partition_contributions`、`prior_rounds_archive`、`limitations` 等）；N03 的列表形态改名为 `deliverable_files`，不再与 `artifacts` 冲突。
- **取值来源**：`uv.lock`/`package-lock.json`/`demo.zip` 逐字节哈希、`docs/architecture/BASELINE_INVENTORY.json` 登记的 173 项 demo 文件按冻结测试同一算法复算、已安装 distribution 版本、`node --version`、当前 Python 解释器版本。**未写任何历史过期值或虚假值。**
- **未改动**：测试断言、业务源码、锁、`OWNERSHIP.json`、契约、总计划/提示词、其他任务交接、ZCode/Codex 记录与官方 Gate。

## 2. 本轮实跑（真实计数、退出码、原始日志）

| 命令 | 退出码 | 实测结果 | 原始日志 |
| --- | --- | --- | --- |
| `uv run pytest tests/unit/test_p01_01_workspace_bootstrap.py tests/integration/test_p01_01_workspace_bootstrap.py -q` | 0 | **56 passed / 0 failed**（45 unit + 11 integration） | `logs/n03-r01-2026-10-04/required-56.log` |
| 同一命令，在**最终交付的 evidence 字节**上复跑确认 | 0 | **56 passed / 0 failed** | `logs/n03-r01-2026-10-04/required-56-confirm.log` |
| `uv run pytest tests/unit tests/integration -q`（安静窗口） | 0 | **226 passed / 0 failed** | `logs/n03-r01-2026-10-04/full-regression.log` |

安静窗口条件：运行前探测到仓库根下除本任务外**无任何写者活动 ≥120s**（原先持续改写 `tmp/orchestration/workbuddy-ai/reuse/.probe/sqlalchemy.json` 的并发会话已停止，该文件已不存在）。`DEF-N03-02` 本轮**未复现**，阶段基线恢复 226 全绿；`DEF-N03-02` 本身仍需治理决定（收窄 P01-03 的整仓快照断言或约定验证窗口），本轮未改测试。

## 3. 冻结测试消费的字段（逐项，取自最终 evidence）

| 消费位置 | 字段 | 当前值 |
| --- | --- | --- |
| L234 | `python_workspace_members` | `["logistics-agents","logistics-backend","logistics-contracts","logistics-domain","logistics-evaluation","logistics-optimization","logistics-simulation"]` |
| L238/265 | `artifacts.uv_lock.sha256` / `artifacts.package_lock.sha256` | `89f78a20…` / `fae1a02c…`（与磁盘一致） |
| L240/269 | `dependencies_lock.uv_lock_sha256` / `.package_lock_sha256` | 同上；`locked_package_count=40`、`npm_lockfile_version=3` |
| L283/290 | `tool_versions.node` / `.python` | `24.18.0` / `3.12.10`（与 `node --version`、`sys.version_info` 一致） |
| L297/307 | `legacy_demo.file_count` / `.tree_sha256` / `.hash_algorithm` / `.demo_zip.sha256` | `173` / `c9a1b33e4a0acf19e0b8c041d76f33b559c8843d76b3d0f8c23f7daf2687d337` / `sha256` / `e0350b75239807047b1dbdb25f69fed5c6c26e34929731d0658db83a58f0e904` |

## 4. 归档

| 轮次 | 归档位置 | 文件数 |
| --- | --- | --- |
| N03 刷新轮（不兼容，本次修复对象） | `artifacts/handoffs/P01-01/dsh/archive-prior-rounds/2026-10-04-pre-n03-r01/` | 13 |
| 首轮（2026-09-13） | `artifacts/handoffs/P01-01/dsh/archive-prior-rounds/2026-10-04-pre-n03/` | 6 |

## 5. 候选与依赖绑定

- 候选（未因本轮改变）：`code_revision = content-sha256:23930f7ae4218778ecbfb33367210f821fb53a1e9d39a2dd195cf2b4f0616c4c`，`dirty_tree_hash = content-sha256:89f1fe4cd1ec0fb04445390586e26534b2a73f71d4f47ebfde3c78626a1957e3`，77 个白名单文件。
- `G00`：`artifacts/gates/G00.json` sha256 `c5e57a6d250ff83f9ceed524f6219a3b1cb9474697a3354b5f102fe24c3bb7e4`，`status=passed`，`finished_at=2026-10-04T14:48:59Z`，reviewer 为 N02-R02 独立会话。

## 6. 失效条件与停止条件

- 任何白名单文件改动都会产生新候选，使本轮 evidence、日志绑定与 G00 引用失效。
- 本文件与 `evidence.json` 在最终写入后未再改动；确认跑的日志是额外新增文件，不影响 evidence 字节。
- 官方 `G01.json` 仍未签收；三份 ZCode precheck 与 `G01-codex-review.json` 只能由对应审查者写入，DSH 未写、未冒签。
- 本轮在写出上述产物后**停止修改该候选**，交 ZCode N04-R01 受影响重验；不启动 P02。


---

# 交接 · 刷新轮 `N03-R02 / 2026-10-04`（当前有效）

> 本节取代上方 N03-R01 / N03 / 首轮结论。N03-R01 记录已逐字节归档到
> `artifacts/handoffs/P01-01/dsh/archive-prior-rounds/n03-r02/`；更早两轮仍在
> `…/2026-10-04-pre-n03-r01/` 与 `…/2026-10-04-pre-n03/`。

| 项 | 值 |
| --- | --- |
| Task ID / round | `P01-01` / `N03-R02-2026-10-04` |
| 本轮主写者 | DSH-A（仅刷新受影响的自身交接，本会话） |
| 本轮范围 | 仅 `docs/handoffs/P01-01/dsh.md`、`artifacts/handoffs/P01-01/dsh/**`、`tmp/N03-R02/**`；**未改**源码、契约、测试、Gate 或他人交接 |
| 本角色状态 | **`READY_FOR_ZCODE`** |
| 阶段 Gate | `G01`：记录字节未变（sha256 `b7ac0c60de7438dc0cd88cc7f277b6ac2e93b8216ee05efdfb3124089c98dee8`），但其 40 项记录输入中**恰有 1 项漂移**（见 §0）；本轮不重签、不改写该记录 |
| 证据入口 | `artifacts/handoffs/P01-01/dsh/evidence.json`（sha256 `e22bf651be243fc7474c143ec44ee1d88716a0ddc11f98780c0fd48e68aa21c1`；F01 更正前的字节见 §8 归档） |
| 下一执行者 | ZCode N04-R03（P01-01 受影响重验） |

## 0. 触发原因（P02-01 的合法包 marker 修改）

P02-01 依原任务 §Files 授权修改了 `packages/domain/src/logistics_domain/__init__.py`（修复 `from logistics_domain import states` 抛 `NotImplementedError`）。该文件是阶段 1 候选的白名单成员，因此：

| 记录 | 记录输入数 | 漂移数 | 漂移项 |
| --- | --- | --- | --- |
| 官方 `artifacts/gates/G01.json` | 40 | **1** | `packages/domain/src/logistics_domain/__init__.py` |
| `artifacts/handoffs/P01-01/zcode/precheck.json` | 48 | **1** | 同上 |
| `artifacts/handoffs/P01-02/zcode/precheck.json` | 36 | **0** | — |
| `artifacts/handoffs/P01-03/zcode/precheck.json` | 33 | **0** | — |

该文件当前 sha256 = `21334c02c11a33f45445a12324be954187a5ed8ae775010158a0608946c50076`；漂移由 `tmp/N03-R02/verify-drift.py` 独立复算（日志 `tmp/N03-R02/verify-drift.log`）。
**如何处置这次漂移由独立审查者决定**；DSH 不改写、不重签任何 Gate 或 precheck。

- 当前候选：`code_revision = content-sha256:dadad19614a86a39ddf880c8ae8011e5fff889d1f02d12b7a0cfa28aaaad3cf8`，`dirty_tree_hash = content-sha256:2b8deb75aa6b28d7529b6f00e0fc958d9556792574a6b8de7018ac4aac20d297`，**82** 个白名单文件（上一轮 77）。
- 官方 `G00`：`c5e57a6d…`，`passed`，输入仍然新鲜（本轮未触碰）。

## 1. 本轮实跑（真实退出码与计数）

| 命令 | 退出码 | 实测结果 | 原始日志 |
| --- | --- | --- | --- |
| `uv run pytest tests/unit/test_p01_01_workspace_bootstrap.py tests/integration/test_p01_01_workspace_bootstrap.py -q` | 0 | **56 passed / 0 failed** | `logs/n03-r02-2026-10-04/affected-p01-01-suites.log` |
| `uv run python tmp/N03-R02/six_package_probe.py`（六个包在仓库外 cwd 的隔离解释器中导入） | 0 | **problems=0**：六包全部解析到各自 workspace src，`logistics_domain.states/primitives/errors` 可导入，未拉入任何第三方模块 | `…/six-package-isolated-import.log` |
| 同一对命令在**最终交付 evidence 字节**上复跑确认 | 0 / 0 | 56 passed；problems=0 | `…/affected-p01-01-suites-confirm.log`、`…/six-package-isolated-import-confirm.log` |

## 2. 明确复用（本轮**未**重跑）

安装与锁未变，故直接引用既有真实日志，并已核验依据：

| 日志 | 出处轮次 | 复用依据 |
| --- | --- | --- |
| `logs/n03-2026-10-04/p01-01-cmd2-uv-sync-frozen.log` | n03-2026-10-04 | `uv.lock` 与 `package-lock.json` 与该轮**逐字节相同**（本轮逐项复算，见 §4） |
| `logs/n03-2026-10-04/p01-01-cmd3-npm-ci-run1.log` | 同上 | 同上 |
| `logs/n03-2026-10-04/p01-01-cmd3b-npm-ci-run2.log` | 同上 | 同上 |

这些日志在 `evidence.json` 的 `reused_logs` 中标注 `reused_not_rerun: true` 及其依据；**不声称**本轮重跑过 `uv sync` 或 `npm ci`。

## 3. 引用而非重跑：272 全回归

`uv run pytest tests/unit tests/integration -q` 的 **272 passed / exit 0** 来自 **P02-01 轮**在当前候选上的实跑日志
`artifacts/handoffs/P02-01/dsh/logs/p02-01-2026-10-04/full-regression.log`（sha256 记录在 `evidence.json` 的
`current_candidate_regression_reference`，含 `provenance` 字段）。按本轮任务卡要求，**本轮不重复全仓回归**。

## 4. 冻结测试消费的字段（名称/形状/取值均未变，逐项核验）

| 消费位置 | 字段 | 状态 |
| --- | --- | --- |
| L234 | `python_workspace_members` | 未变（7 个连字符发行名） |
| L238/265 | `artifacts`（**字典**）/`uv_lock`/`package_lock` | 名称与形状保持；两个锁的 sha256 与磁盘一致且与上轮相同 |
| L240/269 | `dependencies_lock` | 未变 |
| L283/290 | `tool_versions.node` / `.python` | 未变（`24.18.0` / `3.12.10`） |
| L297/307 | `legacy_demo`（`file_count`/`tree_sha256`/`hash_algorithm`/`demo_zip`） | 未变；`demo.zip` 与随附校验文件一致 |

本轮只在 `artifacts` 字典中**新增**一个键 `domain_package_marker` 以记录受影响文件的当前哈希；被冻结测试读取的键未增删改。

## 5. 归档

旧轮（N03-R01）`evidence.json`、`seal.json`、`dsh.md` 与全部日志共 **16 个文件**已逐字节保存到
`artifacts/handoffs/P01-01/dsh/archive-prior-rounds/n03-r02/`，附 `archive-manifest.json`（含逐项 `sha256` 与 `byte_identical` 校验，0 处不一致）。

## 6. 待 ZCode N04-R03 复核的边界

1. §0 的漂移事实与"只有这一个文件"的结论（可用 `tmp/N03-R02/verify-drift.py` 复算）。
2. 交付态在最终 evidence 字节上复跑仍为 56 passed / probe problems=0。
3. §2 的复用是否成立（两个锁文件是否仍与该轮逐字节相同）；§3 的 272 日志是否确为当前候选上的实跑。
4. `artifacts` 仍是字典且被消费键的值与磁盘一致；新增键不影响冻结测试。

## 7. 失效条件与停止条件

- 任何白名单文件再变动都会产生新候选，使本轮实测、绑定的 G01 引用与本轮日志失效。
- 本轮交付后**停止修改该候选**；不签任何 Gate，不启动 P02-02；P01-02/P01-03 的 DSH 交接保持原字节。

## 8. `N03-R02-F01` 元数据更正（本轮，仅簿记）

上一版 `evidence.json` 的候选/命令/日志均已正确，但残留若干**旧快照文字**。本轮只更正这些元数据，未改源码/测试/契约/Gate，未重复全回归，未产生新测试结论：

| 更正项 | 更正前（旧快照） | 更正后（当前） |
| --- | --- | --- |
| `deliverable_files[14]`（`packages/domain/src/logistics_domain/__init__.py`） | `2129` B / `8093a7e57882419f…` | `2669` B / `21334c02c11a33f45445a12324be954187a5ed8ae775010158a0608946c50076` |
| `remaining_risks` | 要求复核 `23930f7a…` | 要求复核 `dadad196…`（82 文件）；旧文字保留并标注 historical |
| `limitations`「无 domain 类型」 | Phase 01 措辞 | 说明 P02-01 已交付 ID/单位/状态枚举类型（尚无实体/求解器/仿真/API）；旧措辞标注 historical |
| `limitations` 白名单规模 | 77 文件 | 82 文件（注明 N03 轮记录为 77） |
| `limitations`「G01 未签」 | 称缺少 precheck 与 review | G01 **已签**（`status=passed` 且有 `G01-codex-review.json`），但其 40 项记录输入恰有 1 项漂移；旧措辞标注 historical |
| `dependency_evidence.G01.note` | "NOT signed" | 已签且一项输入漂移；旧措辞移入 `historical_note` |

- 更正前的 `evidence.json` 与 `seal.json` 原字节保存在 `artifacts/handoffs/P01-01/dsh/archive-prior-rounds/n03-r02-f01/`（含 `archive-manifest.json`）。
- 被冻结测试消费的五组字段（`python_workspace_members`、`artifacts` 字典、`dependencies_lock`、`tool_versions`、`legacy_demo`）**名称/形状/取值均未改**。
- 在更正后的最终字节上复跑受影响套件：**56 passed / exit 0**（`logs/n03-r02-2026-10-04/affected-p01-01-suites-f01-confirm.log`）；未重复 272 全回归。
- 更正记录同时写入 `evidence.json` 的 `bookkeeping_round`，以及 `tmp/N03-R02/N03-R02-completion.json`。
