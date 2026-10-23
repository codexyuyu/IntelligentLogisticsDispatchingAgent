# P01-01 ZCode 独立预验收（N04-R03-F01 · 2026-10-04）

结论：**Z_PRECHECK_PASSED。** DSH N03-R02-F01 的元数据修正（bookkeeping only）经独立复验成立：候选仍为 `dadad196…`(82 文件)字节未变，修正后交付字节上受影响套件实测 **56 passed / exit 0**，26 项 deliverable_files 哈希 0 漂移，修正字段与当前事实及日期相符。交独立 Codex N05-R01 重签 G01。

机器记录：[precheck.json](../../../artifacts/handoffs/P01-01/zcode/precheck.json)（sha256 `7ae3e9d6f22c86c4b6a62679dcebdbab291317bfc2901147437ec331afa8180b`），本轮日志在 `artifacts/handoffs/P01-01/zcode/logs/2026-10-04-r03f01/`。r03 记录原字节归档于 `archive/r3-2026-10-04/`（precheck `5fd3d521…`；其失效原因仅为其绑定的 DSH evidence `18b2ccc1…` 被 F01 元数据修正为 `e22bf651…`）。

## 验收身份与绑定

- 审查者：ZCode N04-R03-F01 独立预验收会话（ZCode CLI，GLM-5.3-Flash）；实际工作根 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，无 Git。
- 当前候选（本轮独立重算，元数据修正未触及白名单）：`content-sha256:dadad19614a86a39ddf880c8ae8011e5fff889d1f02d12b7a0cfa28aaaad3cf8`（82 项）；dirty-tree `content-sha256:2b8deb75aa6b28d7529b6f00e0fc958d9556792574a6b8de7018ac4aac20d297`。
- 前置 G00 有效（25 项输入 0 漂移、runner 前置检查空问题）。
- 等待并确认 DSH F01 修正封存停写后才刷新本记录（seal/evidence 静置 >120s）。

## F01 修正核验（对照当前事实与日期）

- `deliverable_files` 现为 **26 项、哈希 0 漂移**；`[14]` = 当前 marker `packages/domain/src/logistics_domain/__init__.py`（sha256 `21334c02…`、2669 字节；原错误值 `8093a7…`/2129 已消除）。
- `remaining_risks` 现要求审查者确认 **dadad196（82 文件）**；旧表述保留并显式标注 historical。
- `limitations` 现声明 **phase 2 已开始**（P02-01 交付 states/primitives/errors），phase-1 旧句标注 historical；77→82 白名单变化已注明。
- 测试消费字段完好：`python_workspace_members` 与 importlib.metadata 实测一致；`tool_versions` 3.12.10/24.18.0；`dependencies_lock` 哈希与两把锁磁盘值一致；`legacy_demo` 173 + demo.zip；`validation_commands` 日志路径存在。`artifacts` 仍为字典，现为 12 键（原 11 + 新增 `domain_package_marker`），`uv_lock`/`package_lock` 值与磁盘一致。

## 实跑（本轮实测 + 明确复用）

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `uv run pytest tests/unit/test_p01_01_workspace_bootstrap.py tests/integration/test_p01_01_workspace_bootstrap.py -q`（**修正后交付字节上重跑**） | 0 | **56 passed**（冻结测试读取该 evidence 文件，故本轮重跑而非复用） |
| 六包导入探针（**复用 r03 记录**，日志逐字节拷贝并注明来源） | 0 | 不读取 evidence 且源码字节未变，r03 运行仍为该检查的有效证据 |
| 隔离纯度探针（**复用 r03 记录**，同上） | 0 | 零第三方模块 |
| 封存审计 / evidence 哈希复算 | 0 | 候选/G00/demo 不变；三份 DSH evidence 0 漂移 |

未重复全回归（按派发）；DSH 当前候选 272 passed / exit 0 仍作为有来源依赖证据，G01 重签归 N05-R01。

## 三项 precheck 闭包

`20-three-precheck-closure.json`：P01-01(r03f01, 57 输入) / P01-02(r01, `4474dfeb…` 字节未变) / P01-03(r01, `d9ee646e…` 字节未变) 全部 0 问题；runner `check_zcode_precheck` 实测 **3× PASS**。

## 验证边界

- 本记录绑定候选 `dadad196…`；相关文件再变动即失效，按影响重新预验收。
- 本会话未改 DSH 证据/Gate/业务文件，未启动 P02-02；P02-01 业务验收属 G02。
