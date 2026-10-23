# P01-02 ZCode 独立预验收（N04-R01 · 2026-10-04）

结论：**Z_PRECHECK_PASSED。** 96 例收集=运行全过、四项返工判定经 19 项独立探针再次成立、`--check-only` 官方记录字节不变、分层检查零违规；未修改任何实现，未签 G01。

机器记录：[precheck.json](../../../artifacts/handoffs/P01-02/zcode/precheck.json)（sha256 `4474dfeb0169a8e5c7ac8ceddcf09e9b44ad0d45f368243766542bd48b3ecae4`），本轮原始日志在 `artifacts/handoffs/P01-02/zcode/logs/2026-10-04-r01/`。上一轮（r0）记录已归档于 `archive/r0-2026-10-04/`。

## 验收身份与绑定

- 审查者：ZCode N04-R01 独立预验收会话（ZCode CLI，GLM-5.3-Flash）；实际工作根 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，无 Git。
- 当前候选（本轮独立重算，与 N03 声明一致，不沿用任何旧值）：`content-sha256:23930f7ae4218778ecbfb33367210f821fb53a1e9d39a2dd195cf2b4f0616c4c`（77 项）；dirty-tree `content-sha256:89f1fe4cd1ec0fb04445390586e26534b2a73f71d4f47ebfde3c78626a1957e3`；独立公式与 GateRunner 交叉验证一致。
- 前置 G00 有效：25 项输入 0 漂移、日志哈希一致、runner `previous_gate_record_problems` 返回空（N02-R02 于 2026-10-04T14:48:59Z 真实记录，旧字节已归档）。
- N03 刷新 evidence（round `n03-2026-10-04`）复算：14 项产物/日志哈希与磁盘全部一致；其记录的两次全回归 225/1（DEF-N03-02）被本轮安静窗口实测取代。

## 实跑结果（本轮实测）

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `uv run pytest tests/unit/test_p01_02_checks_and_gate_runner.py tests/integration/test_p01_02_checks_and_gate_runner.py -q` | 0 | **96 passed**（`--collect-only` 亦 96，无空洞套件） |
| `uv run python scripts/check_architecture.py` | 0 | 7 模块/7 层，violations=0 |
| `uv run python tmp/N04/probe_rework.py` | 0 | **19/19 独立探针成立**（fail-closed；空/陈旧/缺必需 precheck 哈希拒绝、完整映射接受；仅 status 前序 Gate 拒绝、完整 planner-schema 记录接受、日志漂移/布尔退出码/缺日志哈希/自引用依赖拒绝；excluded 写入不动候选而白名单变更必动；domain 导 fastapi checker 退出 1） |
| `--check-only`（官方记录前后哈希） | 1 | 无写入、无签收；G00.json/G01.json/G00-checks.log 字节一致 |
| 完整回归（严格安静窗口，日志写系统临时目录） | 1 | **219 passed / 7 failed**；前后并发写者扫描均为空，DEF-N03-02 未复现；7 个失败全部是 P01-01 的 evidence-schema 缺陷（见 P01-01 记录），与 P01-02 文件无关 |

其他核验：旧 demo 未覆盖（173/173 + demo.zip）、`OWNERSHIP.json` 显式 `AGENTS.md: A`、仓库根无 `.workbuddy*` 文件、G00 输入新鲜、候选全程无自扰动。

## 验证边界

- 本记录绑定候选 `23930f7a…`；相关文件再变动即失效，按影响重新预验收。
- Phase 01 无数据库、求解器、仿真、模型或浏览器验收。
- G01 签收还需：P01-01 缺陷（ZC-N04-R01-P01-01-F01）由 DSH 恢复并重验 + 独立 Codex N05 review；P02 保持阻断。
