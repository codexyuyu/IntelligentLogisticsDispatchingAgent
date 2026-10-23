# P01-03 · DSH → ZCode 交接说明

> **当前有效轮次：N03 / 2026-10-04。** 下方「交接 · 刷新轮」小节取代首轮表格中的状态与前置结论；首轮交接原文、旧轮 `evidence.json` 与全部日志已逐字节归档到 `artifacts/handoffs/P01-03/dsh/archive-prior-rounds/2026-10-04-pre-n03/`。

| 项目 | 值 |
| --- | --- |
| Task ID | `P01-03`（Phase 01 最后一个任务） |
| 交付方 | DSH（初步开发） |
| 交接对象 | ZCode（独立预验收，按 `docs/workflow/02-ZCODE-PRECHECK.md`——该文件不存在，见 `ARCH-0004`） |
| 本角色状态 | `READY_FOR_ZCODE` |
| 阶段 Gate | `G01`（**未签收**；本任务交付后 P01-03 相关检查已全部转 PASS，剩余失败项只有审查记录） |
| 证据入口 | `artifacts/handoffs/P01-03/dsh/evidence.json`、`docs/implementation/reports/P01-03.md` |

## 1. 交付物与接口

- `resolve_owner(path: str) -> Literal["A","B"]`（`scripts/check_ownership.py`）：最长段感知前缀；未列出路径落 `default_owner`（A）；越界/绝对/盘符/UNC 路径**拒绝**。
- CLI：`--resolve`（逐条解析）、`--json`（完整报告）、`--verbose`、`--root`。
- `convert_legacy_status(kind, value)`：只按 `docs/architecture/LEGACY_ADAPTATION.md` 的表格转换，未映射取值抛 `LegacyConversionError`。
- `convert_legacy_minutes(minutes)`：v0.1 分钟 → v1 整数秒，返回记录 `legacy_version = 0.1.0`。
- `contracts/changes/README.md`：契约变更验收入口（何时必写 + 必填字段 + 验收标准）。
- 根 `OWNERSHIP.json`：60 条规则、2 个 owner、B 范围 8 条前缀。

## 2. 本阶段三任务的交付状态（供阶段签收参考）

| 任务 | 测试 | 检查 | 证据 |
| --- | --- | --- | --- |
| P01-01 workspace | 56 passed | `uv sync --frozen` / `npm ci` exit 0 | `artifacts/handoffs/P01-01/dsh/evidence.json` |
| P01-02 checks & gate runner | 57 passed | 分层检查 exit 0；Gate 执行器失败关闭 | `artifacts/handoffs/P01-02/dsh/evidence.json` |
| P01-03 migration governance | 74 passed | 所有权检查 exit 0（`fallbacks == []`） | `artifacts/handoffs/P01-03/dsh/evidence.json` |
| 阶段回归 | **187 passed / 0 failed / 0 skipped** | — | 见各任务日志 |

## 3. 需要独立复核的边界

1. **CLI 用例 1**：`uv run python scripts/check_ownership.py --resolve packages/simulation/src/logistics_simulation/engine.py` 必须输出恰好 `-> B (prefix: packages/simulation)`。
2. **拒绝语义**：任何未映射 v0.1 值必须抛 `LegacyConversionError`（含已知词表），且不得改动仓库任何文件（本任务用全仓字节快照断言过）。
3. **无意外兜底**：`--json` 的 `coverage.default_owner_fallbacks` 必须为空。
4. **旧前缀不复用**：`backend/app/adapters/routing/` 之类不得出现在 `OWNERSHIP.json` 的规则里。
5. **`demo/` 归属**：v1 把整个 `demo/` 归 A（只读基线），与旧 `demo/OWNERSHIP.json` 的 B 归属不同——请确认这是有意设计。
6. **契约变更入口**：请确认字段集合足以支撑后续 schema/OpenAPI/TS 变更验收。

## 4. 未执行/未覆盖（请重点覆盖）

- G01 签收：需你的预验收记录 + Codex review；`artifacts/gates/G01.json` 的 `failed_checks` 会明确列出缺哪几项。
- 真实 CI（GitHub Actions）、真实 PostgreSQL、Node 22、任何业务行为。
- `EventKind` 的精确字面量映射（待 `P13-01` 冻结）。

## 5. 证据索引

| 证据 | 路径 |
| --- | --- |
| 机器证据（产物 hash、覆盖统计、词表、两个用例断言） | `artifacts/handoffs/P01-03/dsh/evidence.json` |
| 两条强制命令日志 | `artifacts/handoffs/P01-03/dsh/logs/{pytest,check_architecture}.log` |
| 所有权检查日志 | `artifacts/handoffs/P01-03/dsh/logs/check_ownership.log` |
| 阶段 Gate 证据（本任务交付后重跑） | `artifacts/gates/G01.json`、`artifacts/gates/G01-logs/*.log` |
| 任务文档 / 完成报告 | `docs/implementation/P01-03.md`、`docs/implementation/reports/P01-03.md` |
| 转换权威 | `docs/architecture/LEGACY_ADAPTATION.md` |

## 6. 需要项目侧决策的事项（延续 P01-02 已登记项）

- `ARCH-0004`：交接契约文档缺失，审查记录路径/字段由 DSH 临时约定；请确认或补契约。
- `ARCH-0005`：任务书 Test Case 数与冻结清单不一致（P01-02 已登记）。
- `tools/ai_coding_plan/` 下三个取证脚本（P01-01/02/03）在任务白名单外，请判定归属。
- 是否把 P01-03 的 `OWN-B-PATH-PENDING` 六条在 Phase 02 前落地为真实目录。


---

# 交接 · 刷新轮 `N03 / 2026-10-04`（当前有效）

> 本节取代上方首轮结论。首轮 `dsh.md` 原文（sha256 见 `archive-manifest`）与旧轮 `evidence.json`、全部日志已逐字节归档到 `artifacts/handoffs/P01-03/dsh/archive-prior-rounds/2026-10-04-pre-n03/`。

| 项 | 值 |
| --- | --- |
| Task ID / round | `P01-03` / `N03-2026-10-04` |
| 本轮主写者 | DSH-A（N03 交接整合者，本会话） |
| 本轮范围 | 仅刷新自身交接与证据；**未改任何源码、测试、锁、所有权、契约或规划** |
| 本角色状态 | **`READY_FOR_ZCODE`** |
| 阶段 Gate | `G01`（**仍未签收**：官方 `artifacts/gates/G01.json` `status=failed`，sha256 `4383ccac45dddcb465410ce4f4e2d0db7828d340e4d61ed49f87249d3f75c4d4`，本轮未写未改） |
| 证据入口 | `artifacts/handoffs/P01-03/dsh/evidence.json`、`artifacts/handoffs/P01-03/dsh/logs/n03-2026-10-04/` |
| 下一执行者 | ZCode N04（独立预验收；不签官方 Gate） |

## 0. 本轮绑定的候选与依赖证据

- 候选（本轮两次实测一致）：`code_revision = content-sha256:23930f7ae4218778ecbfb33367210f821fb53a1e9d39a2dd195cf2b4f0616c4c`，`dirty_tree_hash = content-sha256:89f1fe4cd1ec0fb04445390586e26534b2a73f71d4f47ebfde3c78626a1957e3`，77 个白名单文件；用 `scripts/gates.py` 的 `GateRunner.relevant_manifest_rows()` 独立复算（`tmp/N03/candidate/candidate-identity.py`）。
- `G00`：`artifacts/gates/G00.json` sha256 `c5e57a6d250ff83f9ceed524f6219a3b1cb9474697a3354b5f102fe24c3bb7e4`，`status=passed`，`finished_at=2026-10-04T14:48:59Z`，reviewer 为 N02-R02 独立会话；`G00-checks.log` sha256 `55e1ad48e648674703ffa0eaa0082757fc31e8c9f5c1c1662d48a5b70dc34488`。我用 `tmp/N03/precondition/g00-drift-audit.py` 独立复算 25/25 输入与日志 hash 全部新鲜（exit 0）。
- 上方首轮表格中"G00 未记录/交付物缺失"一类描述是 2026-09-13/14 的历史事实，已被取代；历史记录本身未删除。

## 1. 本轮实跑结果（真实计数与退出码，取自原始日志）

| 命令 | 退出码 | 实测结果 | 原始日志 |
| --- | --- | --- | --- |
| `uv run pytest tests/unit/test_p01_03_migration_governance.py tests/integration/test_p01_03_migration_governance.py -q` | 0 | **74 passed / 0 failed** | `logs/n03-2026-10-04/p01-03-cmd1-pytest.log` |
| `uv run python scripts/check_architecture.py` | 0 | `scanned 7 module(s) across 7 layer(s); violations=0` | `logs/n03-2026-10-04/p01-03-cmd2-check-architecture.log` |

本轮开工时 `scripts/check_ownership.py --json` 为 `passed=true`、`violations=0`、`default_owner_fallbacks=[]`、`files_scanned=2688`，因此上面 74 例真实通过；这与 N03 首派轮实测的 `2 failed / 72 passed` 不同，差异原因是两个越界记忆文件已被移出工程根（见 §4），**不是** P01-03 代码被修改。

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
| `P01-03/impl` | DSH（A 范围）实现会话（首轮/返工轮） | 本任务主实现者（主写者） | manifest `allowed_files`；字节本轮未改动 |
| `P01-03/round-N03-2026-10-04` | DSH-A（N03 整合者，本会话） | 仅交接与证据刷新 | `docs/handoffs/P01-03/dsh.md`、`artifacts/handoffs/P01-03/dsh/**`、`tmp/N03/**` |
| `OWNERSHIP/AGENTS.md` | **Codex 治理会话（2026-10-01/03）** | 治理修复，**非 DSH 交付物** | `OWNERSHIP.json` |
| `DEF-N03-01` | **编排/Codex 会话（2026-10-04）** | 把两个越界记忆文件移出工程根；**未改** `OWNERSHIP.json`、检查脚本或测试断言 | `.workbuddy/**`、`.workbuddy-ai/**`（已移出） |
| `N02-R02/G00` | **Codex N02-R02 独立审查会话（2026-10-04）** | 按当前输入恢复官方 G00 | `artifacts/gates/G00.json`、`G00-checks.log`、`CONTRACT_FREEZE.*` |

## 4. 请 ZCode 独立复核的边界

1. **CLI 用例 1**：`uv run python scripts/check_ownership.py --resolve packages/simulation/src/logistics_simulation/engine.py` 必须输出恰好 `-> B (prefix: packages/simulation)`。
2. **拒绝语义**：未映射 v0.1 值必须抛 `LegacyConversionError` 且不改动仓库。
3. **无意外兜底**：`--json` 的 `coverage.default_owner_fallbacks` 必须为空（当前为 `[]`）。
4. **旧前缀不复用**：`backend/app/adapters/routing/` 之类不得出现在 `OWNERSHIP.json` 规则中。
5. **§2 的整仓不可变断言请勿按原样依赖**：见下方 §2 与 `DEF-N03-02`；在并发写者活动期间它会误报。

## 5. 失效条件与停止条件

- 任何白名单文件改动都会产生新候选，使本轮 `evidence.json`、日志绑定与 G00 引用失效；届时须重跑并重算。
- 官方 `G01.json` 仍为 `failed`；三份 ZCode precheck 与 `G01-codex-review.json` 只能由对应审查者写入，DSH 未写、未冒签。
- 本轮在写出上述产物后**停止修改该候选**，交 ZCode N04 独立预验收；不启动 P02，不签任何 Gate。
