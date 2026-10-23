# P01-03 · DSH → ZCode 交接说明

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
