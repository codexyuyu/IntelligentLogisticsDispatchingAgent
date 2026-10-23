# P01-02 ZCode 独立预验收（N04 · 2026-10-04）

结论：**Z_PRECHECK_PASSED。** 四项限定返工的正反例与 96 例收集/运行均独立复核成立；未修改任何实现，未签 G01。

机器记录：[precheck.json](../../../artifacts/handoffs/P01-02/zcode/precheck.json)（sha256 `2bae5365570159970488de24fc3264d486856b4a533bf32859eb8ce544c3587b`），本轮原始日志在 `artifacts/handoffs/P01-02/zcode/logs/2026-10-04/`。

## 验收身份与绑定

- 审查者：ZCode N04 独立预验收会话（ZCode CLI，GLM-5.3-Flash）；实际工作根 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，无 Git。
- 当前候选（本轮独立重算，不沿用 DSH 旧 `afbc7e4c…`）：`content-sha256:23930f7ae4218778ecbfb33367210f821fb53a1e9d39a2dd195cf2b4f0616c4c`（77 项）；dirty-tree `content-sha256:89f1fe4cd1ec0fb04445390586e26534b2a73f71d4f47ebfde3c78626a1957e3`。独立公式实现并与 GateRunner 交叉验证一致。
- 前置 G00 有效：重算 25 项输入（0 缺失/0 漂移）+ 日志哈希一致 + runner `previous_gate_record_problems` 返回空；G00 由 N02-R02 独立主审 2026-10-04T14:48:59Z 真实记录，旧字节已归档。
- DSH 证据：`artifacts/handoffs/P01-02/dsh/evidence.json`（round `rework-2026-10-01`，READY_FOR_ZCODE）。20 项记录哈希中 19 项与磁盘一致；唯一差异是其中指向 `artifacts/gates/G00.json` 的 `previous_gate_evidence` 记录旧 G00（`cb1245e2…`）——因 N02-R02 今日合法重录 G00（旧字节已归档），属预期候选演化，非证据伪造；其余（gates.py、两份测试、任务文档、报告、交接、探针脚本及全部 10 份命令日志）逐项一致。

## 四项返工独立复核（不重复实现者自检）

96 例先收集后运行：`--collect-only` 实测 **96 collected**，实跑 **96 passed, 0 skipped, exit 0**（无空洞套件）。在此之上，本轮另写独立探针（`tmp/N04/probe_rework.py`，19/19 成立，日志 `12-p01-02-rework-probes.log`）：

| 返工项 | 独立验证 |
| --- | --- |
| 1 工作区依赖测试 → 受控临时仓库 | 现行 runner 在真实树上对 G00 返回空问题；status-only 前序记录被拒、完整 planner-schema 记录被接受、日志漂移/布尔退出码/缺日志哈希字段/自引用依赖均被拒 |
| 2 候选自扰动 | 受控沙箱内写 excluded 日志/报告/scratch 后 revision 不变；改动白名单源文件后 revision 必变；dirty-tree 与 revision 公式分离 |
| 3 空 precheck 哈希 | `{}` 拒绝；陈旧 digest 拒绝；缺必需输入拒绝；完整新鲜映射（含四类必需输入）接受 |
| 4 仅 status 前序 Gate | 仅 `{"status":"passed"}` 拒绝；F2/F3/F4/F6 字段、整数退出码、原始日志与哈希、冻结输入、依赖环全部实测 |

另实测任务 Test Case 4：`scripts/gates.py --phase 01 --revision auto --check-only` 运行前后官方 `G00.json`/`G01.json`/`G00-checks.log` 字节一致（日志 03/04/05），退出码 1 且未写任何记录；负例 `domain 导入 fastapi` 在受控临时仓库实测 checker 退出 1 并点名 ARCH-PURITY/fastapi（探针 E1/E2）。分层检查 `scripts/check_architecture.py` 实测 7 模块/7 层、violations=0。

## 实跑结果汇总

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `uv run pytest tests/unit/test_p01_02_checks_and_gate_runner.py tests/integration/test_p01_02_checks_and_gate_runner.py -q` | 0 | **96 passed**（收集亦 96） |
| `uv run python scripts/check_architecture.py` | 0 | violations=0 |
| `uv run python tmp/N04/probe_rework.py` | 0 | 19/19 探针成立 |
| `--check-only`（官方记录前后哈希） | 1 | 无写入、无签收；官方记录字节不变 |
| 完整回归 `uv run pytest tests/unit tests/integration -q`（两次） | 1 → 0 | 污染在场 **224 passed / 2 failed**（均为 DEF-N03-01，与 P01-02 文件无关）；清理后 **226 passed / exit 0** |

无自扰动：全部验收写入与 DEF-N03-01 清理后，候选两种哈希、G00 输入、demo 基线复算不变。

## 验证边界

- 本记录绑定候选 `23930f7a…`；相关文件再变动即失效，按影响重新预验收。若 DSH 按 N03-resume 刷新自身交接，本记录对 DSH evidence 的哈希绑定需重新核验后再用于 G01 签收。
- Phase 01 无数据库、求解器、仿真、模型或浏览器验收。
- 三项任务本轮均已 Z_PRECHECK_PASSED；G01 的签收仍待独立 Codex N05（review 缺失，官方 G01 未签），P02 保持阻断。
