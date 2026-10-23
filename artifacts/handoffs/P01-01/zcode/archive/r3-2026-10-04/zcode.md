# P01-01 ZCode 独立预验收（N04-R03 · 2026-10-04）

结论：**Z_PRECHECK_PASSED。** P02-01 的合法包 marker 变更使候选从 `23930f7a…`(77 文件)演进为 `dadad196…`(82 文件)；受影响的 P01-01 套件实测 **56 passed / exit 0**，六包导入与域层隔离纯度独立成立。P01-02/03 precheck 输入未变、字节未动。本记录只刷新 P01-01，交独立 Codex N05-R01 重新签收 G01。

机器记录：[precheck.json](../../../artifacts/handoffs/P01-01/zcode/precheck.json)（sha256 `5fd3d521073d81919726d601761356997401c1b7bb00123f83cde61da3746e37`），本轮原始日志在 `artifacts/handoffs/P01-01/zcode/logs/2026-10-04-r03/`。r02 记录原字节归档于 `archive/r2-2026-10-04/`（precheck `02184891…`，其失效原因仅为 marker 输入漂移）。

## 验收身份与绑定

- 审查者：ZCode N04-R03 独立预验收会话（ZCode CLI，GLM-5.3-Flash）；实际工作根 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，无 Git。
- 当前候选（本轮独立重算，与 P02-01/N03-R02 声明一致）：`content-sha256:dadad19614a86a39ddf880c8ae8011e5fff889d1f02d12b7a0cfa28aaaad3cf8`（**82** 项）；dirty-tree `content-sha256:2b8deb75aa6b28d7529b6f00e0fc958d9556792574a6b8de7018ac4aac20d297`；独立公式与 GateRunner 交叉验证（文件集合一致）。
- 前置 G00 有效：25 项输入 0 漂移、日志哈希一致、runner 前置检查空问题。
- DSH 交接时序：等侯至 N03-R02 实际封存停写（`tmp/N03-R02/N03-R02-completion.json`，DELIVERED_READY_FOR_ZCODE）后才刷新本记录；其触发核验（marker `21334c02…`、G01 唯一漂移输入）与本轮独立复算一致。

## Marker 例外核验（原任务规则对照）

- **授权**：原 P01-01 任务允许「包 marker 只有确需导出本任务类型时可修改，须先在完成报告列出精确路径」——`docs/implementation/reports/P02-01.md` 已列精确路径 `packages/domain/src/logistics_domain/__init__.py` 与理由（修复 `from logistics_domain import states` 因 `_PENDING_APIS` 误报 NotImplementedError 且依赖导入顺序）。
- **Loud failure 未削弱**（本会话亲自复现）：`entities`/`units` 仍抛 `NotImplementedError`（含责任任务指针）；未知名抛 `AttributeError`；已交付子模块 `states`/`primitives`/`errors` 确定性解析。
- **域层纯净**：隔离解释器（`-I`，系统临时 cwd）导入 `logistics_domain` 全家后第三方模块加载为 **0**（`12-isolated-domain-purity-probe.log`）。

## 实跑结果（本轮实测）

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `uv run pytest tests/unit/test_p01_01_workspace_bootstrap.py tests/integration/test_p01_01_workspace_bootstrap.py -q` | 0 | **56 passed**（受影响套件，新候选上） |
| 六包导入 + domain 导出探针 | 0 | 六包各自解析到 `packages/*/src`；`__all__` 新增 `errors/primitives/states` |
| 隔离纯度探针 | 0 | 零第三方模块 |

按派发**未重复全回归**：DSH 当前候选实跑 272 passed / exit 0（round `p02-01-2026-10-04`）作为有来源的依赖证据引用；G01 重新签收由 N05-R01 实际执行。复算核验：G00 25 项输入 0 漂移、demo 173/173、锁未动、三份 DSH evidence（P01-01 n03-r02 / P01-02 / P01-03）产物与日志哈希 0 漂移、全程无自扰动。G01 现状：已签记录 `b7ac0c60…`(passed) 绑定旧候选，唯一漂移输入即本 marker——由 N05-R01 重签解决。

## 三项 precheck 闭包（交 N05-R01 前）

`20-three-precheck-closure.json`：P01-01(r03, 57 输入) / P01-02(r01, 36 输入, 字节未变 `4474dfeb…`) / P01-03(r01, 33 输入, 字节未变 `d9ee646e…`) 全部 status/reviewer 匹配、输入与日志哈希对盘 **0 问题**；runner `check_zcode_precheck` 实测 **3× PASS**。

## 验证边界

- 本记录绑定候选 `dadad196…`(82 文件)；相关文件再变动即失效，按影响重新预验收。
- P02-01 的业务验收属 G02，不在本记录范围；本会话未改代码/测试/他人证据/官方 Gate，未启动 P02-02。
