# P01-01 ZCode 独立预验收（N04-R01 · 2026-10-04）

结论：**FAILED（未通过预验收，未写 Z_PRECHECK_PASSED）。** 必需命令实测退出 1（**7 failed / 49 passed**），根因是 N03 刷新的 P01-01 evidence（round `n03-2026-10-04`，写于 2026-10-04T16:01:57Z）变更了 evidence schema，而冻结的 P01-01 集成测试仍按旧 schema 从同一文件读取。候选实现文件与本预验收会话均未改动。

机器记录：[precheck.json](../../../artifacts/handoffs/P01-01/zcode/precheck.json)（sha256 `ed092364c7f2754df567d82b2b5216f1a3e694201867883bca0604bc43f68c15`，status=`FAILED`），本轮原始日志在 `artifacts/handoffs/P01-01/zcode/logs/2026-10-04-r01/`。上一轮（r0）precheck 与 zcode.md 已归档于 `archive/r0-2026-10-04/`。

## 验收身份与绑定

- 审查者：ZCode N04-R01 独立预验收会话（ZCode CLI，GLM-5.3-Flash）；实际工作根 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，无 Git。
- 当前候选（本轮独立重算，与 N03 声明一致）：`content-sha256:23930f7ae4218778ecbfb33367210f821fb53a1e9d39a2dd195cf2b4f0616c4c`（77 项）；dirty-tree `content-sha256:89f1fe4cd1ec0fb04445390586e26534b2a73f71d4f47ebfde3c78626a1957e3`；与 GateRunner 交叉验证一致。
- 前置 G00 有效（25 项输入 0 漂移、日志哈希一致、runner 前置检查空问题）。
- 三份刷新后 DSH evidence 复算：P01-01 32 项、P01-02 14 项、P01-03 12 项产物/日志哈希 **0 漂移**；依赖 G00 门+日志哈希 OK。

## 缺陷 ZC-N04-R01-P01-01-F01（blocker）

- **复现**：`uv run pytest tests/unit/test_p01_01_workspace_bootstrap.py tests/integration/test_p01_01_workspace_bootstrap.py -q` → 7 failed / 49 passed，exit 1。日志 `10-p01-01-cmd1-pytest-FAILED.log`。
- **根因**：`tests/integration/test_p01_01_workspace_bootstrap.py`（候选内、字节未变）在 line 30 以 `EVIDENCE_PATH` 读 `artifacts/handoffs/P01-01/dsh/evidence.json`，消费 `evidence["python_workspace_members"]`(L234)、`evidence["artifacts"]["uv_lock"/"package_lock"]` 字典形态(L238/265)、`evidence["dependencies_lock"]`(L240/269)、`evidence["tool_versions"]["node"/"python"]`(L283/290)、`evidence["legacy_demo"]`(L297/307)。N03 新 evidence 把 `artifacts` 改为列表并删除上述键 → 7 例 KeyError/TypeError（installed_distributions、uv_lock_hash、npm_lock_hash、node_baseline、python_baseline、legacy_demo_tree、demo_zip）。
- **为何 N03 记录 56 通过**：其套件运行发生在重写 evidence 之前（旧 evidence 在盘）；重写后未复跑。交付态与自身验证脱节。
- **责任方**：DSH-A N03 刷新轮（`artifacts/handoffs/P01-01/dsh/evidence.json` 的写者）。与候选实现文件无关，与本预验收会话无关。
- **恢复**：由 DSH 重新交付与冻结测试契约兼容的 evidence（在新治理字段之外补回被消费字段，或将 `artifacts` 恢复为字典）；或经治理批准修改测试形成新候选（须全量重验）。随后重跑必需命令（预期 56 passed、exit 0）并重派 P01-03 式的新一轮 P01-01 预验收。本会话未改测试与候选。

## 本轮其余实测（全部通过）

`uv sync --frozen`（39 packages）；`npm ci` ×2 且 `package-lock.json` sha256 `fae1a02c…` 前后不变（=evidence 记录值）；`uv lock --check`；六包导入解析正确；demo 173/173 + `demo.zip` 哈希一致；G00 新鲜。严格安静窗口全回归（日志写系统临时目录、前后并发写者扫描均为空、DEF-N03-02 未复现）：**219 passed / 7 failed**，7 个失败即本缺陷。

## 停止状态

- 本会话未修复实现、未签任何 Gate、未启动下游；G01 因本 FAILED 与缺失 Codex review 保持阻断。
- 责任方恢复并重验后，需新一轮 P01-01 独立预验收；三项全 PASSED 后才可交 Codex N05 签收 G01。
