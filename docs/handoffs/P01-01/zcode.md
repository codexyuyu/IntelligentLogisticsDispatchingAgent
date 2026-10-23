# P01-01 ZCode 独立预验收（P01-01-IMPACT-F01-M01 · 2026-10-05）

结论：**Z_PRECHECK_PASSED。** 本卡（M01）仅两处元数据纠正，未重跑任何测试；上轮 56 passed 套件、六包导入/纯度/loud-failure、分层 0 违规的原日志与结论全部保留。交独立 Codex N05。

机器记录：[precheck.json](../../../artifacts/handoffs/P01-01/zcode/precheck.json)（sha256 `f044a885c622d17d320cb5cd9f6ce247d6f6434d9163f16cf63e377acb56790e`，54 项输入、14 条命令），M01 日志在 `artifacts/handoffs/P01-01/zcode/logs/p02-f01-impact-m01/`；上轮(p02-f01-impact)命令日志仍在 `logs/p02-f01-impact/` 原位。原字节归档：`archive/p02-f01-impact/metadata-m01/before/`（precheck `2be58c74…`、zcode.md）。

## 验收身份与绑定

- 审查者：ZCode P01-01-IMPACT-F01-M01（原独立 N04 会话延续；GLM-5.3-Flash）；实际工作根 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，无 Git。
- 当前候选（本轮以现行 GateRunner 复算）：`content-sha256:477a883d2a29deb5cb60f8269c8712693d9e7aedeb3a620ba4953a630289158c`（82 项）；**完整 dirty-tree** `content-sha256:eaea942624f00e5da16e89a3e744d3a2c1c659fcf9eeda0a23787116681d636f`。
- 前置：G00 有效（25 项输入 0 漂移）；G01 历史记录（40 项直接输入在本轮开始时全部新鲜）——见下述改绑说明。

## M01 两处纠正

1. **dirty_tree_hash 截断补全**：上轮记录只含 `eaea942624f00e5da16e89a3e744d3`（截断）。本轮用现行 GateRunner 实际相关清单复算完整值 `content-sha256:eaea942624f00e5da16e89a3e744d3a2c1c659fcf9eeda0a23787116681d636f`（复算而非沿用卡片预计；code_revision 不变）。
2. **G01 绑定改挂不可变历史归档**：上轮绑定活跃 `artifacts/gates/G01.json`，N05 合法重签 G01 会使该绑定失效并造成前置 precheck 与 G01 的循环。本轮先把活跃 G01（`a7eed6ae…`）逐字节复制到 `archive/p02-f01-impact/metadata-m01/G01-historical.json`（复算哈希与原文件一致），绑定改为该归档路径；语义明确为**仅证明本轮开始时历史 G01 的 40 项直接输入新鲜**，不构成对未来新 G01 的签收。原 G01.json 未被覆盖或修改；G00 及全部真实当前源码/规则/导入依赖绑定保留，未删依赖、未弱化断言。

## 保留的实际证据（未重跑）

上轮 p02-f01-impact 的实测结论原样有效：必需套件 **56 passed / exit 0**（56 collected）、`check_architecture.py` 10 模块 0 违规、隔离探针六包导入/零第三方/`entities·ids·units·ports` NotImplementedError/delivered→draft 拒绝、F01 落点确认；安装与锁检查（`uv sync --frozen`、`npm ci` ×2 锁不变、`uv lock --check`）按字节验证复用 r01 原日志；P01-02/03 precheck 复算后原字节复用。本轮 commands[] 共 14 条：11 条沿用上轮原日志（哈希未变），3 条为本卡实跑（归档+哈希、dirty 复算、输入/日志前后核验与 runner 机械校验）。

## 漂移机器事实与元数据说明（承接上轮）

- 旧 precheck(r03f01) 5 项漂移、G01 review 8 项漂移、G01 直接输入 40 项全鲜——本轮开始时复算，事实不变。
- DSH 轮元数据三处摘要误差（evidence `1ff843…` vs 实际 `eac21615…`、seal previous_candidate 拼写、review 漂移清单 5 文 vs 8 计数）已按机器事实绑定，未改写 DSH 记录。

## 验证边界

- 本记录绑定候选 `477a883d…`；相关文件再变动即失效，按影响重新预验收。
- 本卡只写自己的记录/归档/日志；未改代码/测试/Gate/规则/DSH 记录，未重跑 56 项或全仓回归，未启动 P02-02，未签任何 Gate。
