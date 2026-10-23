# P01-03 ZCode 独立预验收（N04 · 2026-10-04）

结论：**Z_PRECHECK_PASSED（缺陷在轮内已被处置并复验）。** 必需命令在轮内先因仓库根两个越权记忆文件（DSH 缺陷卡 DEF-N03-01）实测失败（2 failed / 72 passed），编排者将两文件移出工程根后复测 **74 passed / exit 0**，完整回归 **226 passed / exit 0**。未修改任何实现，未签 G01。

机器记录：[precheck.json](../../../artifacts/handoffs/P01-03/zcode/precheck.json)（sha256 `d3a69177c44de85371f7d31dfac8dee51cdd6fca9c36ac06df6b15de77f88c19`），本轮原始日志在 `artifacts/handoffs/P01-03/zcode/logs/2026-10-04/`。

## 验收身份与绑定

- 审查者：ZCode N04 独立预验收会话（ZCode CLI，GLM-5.3-Flash）；实际工作根 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，无 Git。
- 当前候选（本轮独立重算）：`content-sha256:23930f7ae4218778ecbfb33367210f821fb53a1e9d39a2dd195cf2b4f0616c4c`（77 项）；dirty-tree `content-sha256:89f1fe4cd1ec0fb04445390586e26534b2a73f71d4f47ebfde3c78626a1957e3`，与 GateRunner 交叉验证一致。被移走的记忆文件从来不在白名单内，清理前后候选字节一致。
- 前置 G00 有效（同 P01-01/P01-02 记录：25 项输入 0 漂移、日志哈希一致、runner 前置检查空问题；N02-R02 于 2026-10-04T14:48:59Z 真实记录）。
- DSH 证据：`artifacts/handoffs/P01-03/dsh/evidence.json`（2026-09-12 轮，READY_FOR_ZCODE；N03 因 DEF-N03-01 停写未刷新）。15 项记录哈希中 14 项与磁盘一致；唯一差异是其记录的 `OWNERSHIP.json` 旧哈希 `bc86773d…`——2026-10-01 治理修正已加入显式 `AGENTS.md: A`（当前 `782d695a…`），属已知候选演化；本轮一律绑定当前磁盘哈希。

## 缺陷与处置（本轮实测）

| 项 | 内容 |
| --- | --- |
| ID | ZC-N04-P01-03-F01（与 DSH `tmp/N03/defects/DEF-N03-01-workbuddy-ownership-pollution.md` 同根因，独立复现后于轮内处置） |
| 初测 | `uv run pytest tests/unit/test_p01_03_migration_governance.py tests/integration/test_p01_03_migration_governance.py -q` → **2 failed, 72 passed, exit 1**；`check_ownership --json` fallbacks = `['.workbuddy-ai/memory/2026-10-04.md', '.workbuddy/memory/2026-10-04.md']`。两文件由越权 WorkBuddy 并行会话于 07:47/07:48 创建（其任务卡仅允许 `tmp/workbuddy-dispatch/**`）。与 P01-03 实现无关：DSH evidence 其余 14 项哈希与磁盘一致 |
| 处置 | Codex 编排者（派发件 `artifacts/dispatch/2026-10-04/orchestration/dsh/N03-resume.md`）将两文件逐字节移出工程根；归档清单 `tmp/orchestration/archive/DEF-N03-01/archive-evidence.json`（源哈希 `5e39b3c7…`/`3a86cd9e…`，source_remaining=false）。`OWNERSHIP.json`、`check_ownership.py` 与测试断言均未被修改 |
| 复验 | `check_ownership --json` → passed=true、fallbacks=[]、violations=0；必需命令重跑 → **74 passed, exit 0**；完整回归 → **226 passed, exit 0** |
| 残留观察 | 空目录 `.workbuddy/`、`.workbuddy-ai/` 仍在仓库根；所有权检查器只统计文件，检查通过，但根目录并未完全清除该越权会话的目录 |

同轮其余验证：`scripts/check_architecture.py` exit 0（7 模块/7 层，violations=0）；G00 有效、候选无自扰动、demo 基线与显式所有权核验同 P01-01/P01-02 记录。

## 验证边界

- 本记录绑定候选 `23930f7a…`；相关文件再变动即失效。若再有越权会话在仓库根创建无归属文件，必需命令会再次失败，本判定须重新核验。
- 若 DSH 按 N03-resume 刷新自身交接，本记录对 DSH evidence 的哈希绑定需重新核验后再用于 G01 签收。
- Phase 01 无数据库、求解器、仿真、模型或浏览器验收。G01 的签收仍待独立 Codex N05（review 缺失，官方 G01 未签），P02 保持阻断。
