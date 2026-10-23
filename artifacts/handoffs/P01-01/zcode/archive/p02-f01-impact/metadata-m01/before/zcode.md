# P01-01 ZCode 独立预验收（P01-01-IMPACT-F01 · 2026-10-05）

结论：**Z_PRECHECK_PASSED。** DSH P02-01-F01（reservation 修复，evidence `eac21615…`/seal `32d2a882…` 封存停写）使候选自 `dadad196…` 移至 `477a883d…`（82 文件）；受影响的 P01-01 导入预验收本轮独立刷新：必需套件 **56 passed / exit 0**，隔离六包导入/域纯度/loud-failure 全部成立，分层检查 0 违规。P01-02/03 记录复算后原字节复用。交独立 Codex N05。

机器记录：[precheck.json](../../../artifacts/handoffs/P01-01/zcode/precheck.json)（sha256 `2be58c74702e222ee9b69204b6846e459debeb97dd880d5dd0bad6d3842ebfe9`，54 项输入），本轮日志在 `artifacts/handoffs/P01-01/zcode/logs/p02-f01-impact/`（活跃日志先写卡内系统 TEMP，再归档）。旧 r03f01 记录及其采用的日志已逐字节归档于 `archive/p02-f01-impact/`（precheck `7ae3e9d6…`）。

## 验收身份与绑定

- 审查者：ZCode P01-01-IMPACT-F01（原 N04 独立会话，未参与实现；GLM-5.3-Flash）；实际工作根 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`（已核对），无 Git。
- 当前候选（本轮独立重算，与卡片锚点一致）：`content-sha256:477a883d2a29deb5cb60f8269c8712693d9e7aedeb3a620ba4953a630289158c`（82 项）；dirty-tree `content-sha256:eaea9426…`；独立公式与 GateRunner 交叉验证一致。
- 前置：G00 有效（25 项输入 0 漂移、runner 前置检查空问题）；G01 `a7eed6ae…`(passed) 40 项直接输入全部新鲜——历史签收不因 revision 不同而无效。

## 漂移机器事实（本轮复算，与卡片一致）

| 对象 | 漂移 |
| --- | --- |
| 旧 P01-01 precheck（r03f01, `7ae3e9d6…`） | **5 项**：P02-01 dsh evidence、P02-01 报告、`states.py`、两份 P02-01 测试 |
| G01 codex review（`c41888a…`） | **8 项**（上述 5 + dsh seal、dsh.md、implementation 文档） |
| G01 直接输入 | **0 项**（40/40 新鲜） |

## 本轮实跑（新候选上）

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `uv run pytest tests/unit/test_p01_01_workspace_bootstrap.py tests/integration/test_p01_01_workspace_bootstrap.py -q` | 0 | **56 passed**（collect 亦 56，无 skip） |
| `uv run python scripts/check_architecture.py` | 0 | 10 模块/7 层，violations=0 |
| 隔离探针（`-I`，卡内系统 TEMP cwd） | 0 | 六包各自解析正确；第三方模块 **0**；`entities/ids/units/ports` 仍 `NotImplementedError`；delivered→draft 仍拒绝；F01 落点确认（RELEASED 已入联合词汇、committed→{expired,released}）——仅作上下文，Reservation 业务验收归 G02 |

**复用（逐项核验后引用原日志，非本轮重跑）**：`uv sync --frozen`、`npm ci` ×2（锁前后不变）、`uv lock --check`（r01 轮原日志；`uv.lock`/`package-lock.json` 本轮复算仍与 evidence 值字节一致）、demo 基线 173/173、G00、P01-02/03 precheck（36/33 输入 0 漂移）。P01-01 DSH evidence 的 **26 项 deliverable_files 0 漂移**（states.py 属 P02-01 文件，非 bootstrap 交付物）。

## 新读取闭包与逐项理由

- **保留**：四类必需输入；P01-01 全部交付物文件；`states.py`/`primitives.py`/`errors.py` 与 marker（bootstrap 包现导入它们，为六包检查的活跃导入依赖）；两份 P01-01 测试+conftest；`check_architecture.py`；G00/G01；P02-01 dsh evidence+seal（变更来源封存证明，非业务验收）；P01-02/03 precheck（本轮闭包复验）；锁/demo/所有权/规则文档。
- **移出**（相对旧集合）：两份 P02-01 业务测试与 P02-01 报告——P02 业务验收及其业务交接不作为 bootstrap 正确性证明；本轮以 bootstrap 套件+导入探针覆盖实际导入影响。
- **元数据机器事实**（不改他人交接）：dsh-f01.md 首表 evidence `1ff843…` 为旧摘要，actual `eac21615…`；seal 的 previous_candidate 有拼写误差（真实旧值 `dadad196…`）；seal review 漂移清单正文 5 项而计数 8——以实算 8 项清单为准。

## 验证边界

- 本记录绑定候选 `477a883d…`；相关文件再变动即失效，按影响重新预验收——本次裁剪不豁免后续相关源码/导入变化的复核。
- G01 review 的 8 项漂移由 N05 处理重绑；未签 G01/G02，未启动 P02-02，未跑全仓回归，未改源码/官方 Gate/正确性断言。
