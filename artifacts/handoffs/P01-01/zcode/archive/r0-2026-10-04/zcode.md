# P01-01 ZCode 独立预验收（N04 · 2026-10-04）

结论：**Z_PRECHECK_PASSED。** 本任务实现候选在当前冻结输入下通过独立预验收；未修改任何实现，未签 G01。

机器记录：[precheck.json](../../../artifacts/handoffs/P01-01/zcode/precheck.json)（sha256 `c7fe05e4570c7332c57ad56088fc942aee9b249a0064e7aeb74d6f1533d9e49b`），本轮原始日志在 `artifacts/handoffs/P01-01/zcode/logs/2026-10-04/`。旧 9-28 r2 轮记录（evidence.json、r2 日志）已逐字节移入 `archive/r2-2026-09-28/`（见该目录 archive-manifest.json）；r2 precheck.json 当时输入已漂移（见本轮 `04-checkonly-run.log` 的 STALE 列表），在归档前已被本轮回原位替换，其旧字节未能单独留存，特此如实记录。

## 验收身份与绑定

- 审查者：ZCode N04 独立预验收会话（ZCode CLI，GLM-5.3-Flash）；实际工作根 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，无 Git。
- 当前候选（本轮独立重算，未沿用任何旧值）：`content-sha256:23930f7ae4218778ecbfb33367210f821fb53a1e9d39a2dd195cf2b4f0616c4c`（77 项相关文件）；dirty-tree `content-sha256:89f1fe4cd1ec0fb04445390586e26534b2a73f71d4f47ebfde3c78626a1957e3`。独立实现白名单公式，并与现行 `scripts/gates.py` 的 GateRunner 交叉验证：文件集合与两种哈希完全一致。
- 前置 G00 有效：本轮重算官方 `artifacts/gates/G00.json` 的 25 项输入哈希（0 缺失 / 0 漂移）、`G00-checks.log` sha256 一致（`55e1ad48…`）、依赖哈希为合法空集合，并以现行 runner `previous_gate_record_problems("G00", …)` 实测返回空。该 G00 由独立主审 Codex N02-R02 于 2026-10-04T14:48:59Z 真实执行 `--record-g00` 产生，旧记录已逐字节归档于 `artifacts/handoffs/N02-R02/codex/archive/`。
- DSH 证据：`artifacts/handoffs/P01-01/dsh/evidence.json`（2026-09-12 轮，READY_FOR_ZCODE；N03 因 DEF-N03-01 阻断停写、尚未刷新交接）。其记录的 14 项产物/日志哈希与磁盘全部一致；其记录的历史候选 `3a522f70…` 不再沿用。

## 实跑结果（本轮实测，非照抄）

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `uv run pytest tests/unit/test_p01_01_workspace_bootstrap.py tests/integration/test_p01_01_workspace_bootstrap.py -q` | 0 | **56 passed** |
| `uv sync --frozen` | 0 | Checked 39 packages |
| `npm ci`（第 1 次） | 0 | added 4 packages |
| `npm ci`（第 2 次） | 0 | package-lock.json sha256 `fae1a02c…` 前后不变，等于 P01-01 evidence 记录值 |
| 六包导入探针 | 0 | 六包各自解析到 `packages/*/src` |
| `uv lock --check` | 0 | Resolved 40 packages |
| 完整回归 `uv run pytest tests/unit tests/integration -q`（两次） | 1 → 0 | 污染文件在场时 **224 passed / 2 failed**（失败均为 DEF-N03-01 所有权兜底断言，与 P01-01 文件无关）；编排者移出两个记忆文件后复测 **226 passed / exit 0**（与历史基线一致，本轮自主实测） |

其他核验：旧 demo 未覆盖——`demo.zip` sha256 与 `demo.zip.sha256` 一致，`BASELINE_INVENTORY.json` 173/173 项哈希相符；`OWNERSHIP.json` 含显式 `AGENTS.md: A`；无自扰动——全部验收写入与 DEF-N03-01 清理之后，候选两种哈希、G00 输入与 demo 基线复算均不变（被移走的记忆文件从来不在 77 项白名单内）。

## 验证边界

- 本记录绑定上述候选；任何相关文件变动即失效，需按影响重新预验收。若 DSH 按 N03-resume 刷新自身交接，本记录对 DSH evidence 的哈希绑定需重新核验后再用于 G01 签收。
- Phase 01 无数据库、求解器、仿真、模型或浏览器验收。
- 三项任务本轮均已 Z_PRECHECK_PASSED；G01 的签收仍待独立 Codex N05（review 缺失，官方 G01 未签），P02 保持阻断。
