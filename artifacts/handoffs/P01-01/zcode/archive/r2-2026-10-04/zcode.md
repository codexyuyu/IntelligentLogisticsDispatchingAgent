# P01-01 ZCode 独立预验收（N04-R02 · 2026-10-04）

结论：**Z_PRECHECK_PASSED。** DSH N03-R01 的 evidence 修复经独立复验成立：必需命令实测 **56 passed / exit 0**，安静窗口全回归 **226 passed / exit 0**；候选与测试从未改动。三项任务当前 precheck 闭包全部通过，交独立 Codex N05。

机器记录：[precheck.json](../../../artifacts/handoffs/P01-01/zcode/precheck.json)（sha256 `02184891a415742a6999482b6a8765cc6a1f3b0d02d4f0fe1a907c9b571d7c06`），本轮原始日志在 `artifacts/handoffs/P01-01/zcode/logs/2026-10-04-r02/`。r01 的 FAILED 记录原字节保留于 `archive/r1-2026-10-04/`（precheck `ed092364…`）。

## 验收身份与绑定

- 审查者：ZCode N04-R02 独立预验收会话（ZCode CLI，GLM-5.3-Flash）；实际工作根 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，无 Git。
- 当前候选（本轮独立重算，与 N03-R01 声明一致）：`content-sha256:23930f7ae4218778ecbfb33367210f821fb53a1e9d39a2dd195cf2b4f0616c4c`（77 项）；dirty-tree `content-sha256:89f1fe4cd1ec0fb04445390586e26534b2a73f71d4f47ebfde3c78626a1957e3`；独立公式与 GateRunner 交叉验证一致。
- 前置 G00 有效：25 项输入 0 漂移、日志哈希一致、runner `previous_gate_record_problems` 返回空。
- 三份 DSH evidence 复算：P01-01（round `n03-r01`，sha256 `0eb8782c…`）8 项、P01-02（`n03-2026-10-04`）14 项、P01-03 12 项产物/日志哈希 **0 漂移**；依赖 G00 门+日志哈希 OK。

## 缺陷 ZC-N04-R01-P01-01-F01：RESOLVED（本轮独立验证）

N03-R01 在同一 evidence 文件内恢复了冻结测试消费的契约：`artifacts` 恢复为 11 键字典（全部 sha256 与磁盘一致），`python_workspace_members`/`dependencies_lock`/`tool_versions`/`legacy_demo` 按实际值重建，原列表形态改名为 `deliverable_files`（26 项）不再冲突，`validation_commands` 指向真实存在的日志。本轮独立核对（`03-restored-evidence-fields-verify.log`）：

- `python_workspace_members` == 当前 venv `importlib.metadata` 实测的 7 个 workspace 成员；
- `tool_versions.python` == 运行解释器 3.12.10；node 24.18.0；
- `dependencies_lock` 的 uv/npm 哈希 == `uv.lock`/`package-lock.json` 磁盘值；
- `legacy_demo.file_count=173`，`demo_zip.sha256` == 随附 `demo.zip` 校验值。

## 实跑结果（本轮实测，日志先写系统临时目录再归档）

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `uv run pytest tests/unit/test_p01_01_workspace_bootstrap.py tests/integration/test_p01_01_workspace_bootstrap.py -q` | 0 | **56 passed**（45 unit + 11 integration） |
| `uv run pytest tests/unit tests/integration -q` | 0 | **226 passed**，exit 0；窗口前置/后置写者扫描均 0（`11/14`），DEF-N03-02 未复现，本运行日志在系统临时目录故快照窗口无任何仓库写入 |

复用上一轮有效证据（输入字节未变，见 `01/02` 日志哈希确认）：`uv sync --frozen`、`npm ci` ×2 锁稳定（`fae1a02c…` = evidence 值）、`uv lock --check`、六包导入、P01-02/P01-03 分套 96/74 及 19 项返工探针。demo 基线、`AGENTS.md: A` 显式所有权、G00 新鲜、候选全程无自扰动均复核。

## 三项 precheck 闭包（交 N05 前）

`20-three-precheck-closure.json`：三份记录 task_id/phase_gate/status/reviewer 匹配，全部 `verified_input_hashes` 与 `commands[].log_sha256` 逐项对盘复算 **0 问题**；P01-02/P01-03 记录字节未变（`4474dfeb…`/`d9ee646e…`）。现行 runner `check_zcode_precheck` 实测 **3× PASS**（48/36/33 项新鲜输入）。

## 验证边界

- 本记录绑定候选 `23930f7a…`；相关文件再变动即失效，按影响重新预验收。
- 回归依赖安静窗口：任何会话在回归期间写仓库根或 `tmp/` 会再触发快照误报（运行条件问题，非候选缺陷）。
- Phase 01 无数据库、求解器、仿真、模型或浏览器验收。G01 官方签收由独立 Codex N05 执行；本会话未签 Gate、未改实现或他人证据、未启动 P02。
