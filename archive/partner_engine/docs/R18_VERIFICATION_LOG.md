# R18 交付环境验证记录（2026-10-14）

> **2026-10-14 晚实测补记**：文末新增[附：Windows 实测与收尾验收](#附windows-实测与收尾验收2026-10-14-晚)一节。本文件正文描述的依赖缺失、无法求解等状态属于**当时交付环境**，保留为历史记录；R18 五组真实求解已在 Windows 机完成并冻结归档，最新口径以附录为准。

**真实性声明**：不重复运行用户已验收的 R17 公平 A/B 实验；仅在已提供的原始证据上开展静态/逐单指标核算。新 R18 的 5 个场景未做真实 OR-Tools 求解，不能使用“5/5 成功”或“多场景改善 X%”这类结论。

## 已通过

1. `python -m tools.r18_evidence_audit --input ../benchmarks/b03/r17_accepted/r17_accepted_original.json --scenario ../data/scenarios/two_warehouses_20_orders.json --output ../benchmarks/b03/r17_accepted/r17_arithmetic_audit.json`：20 单累计等待 4500→2400 秒，运输里程同为 56000 m；R17 原场景 SHA256 匹配；由源 JSON 所记录 validation=passed，两组订单全覆盖、候选计划指标一致。审计结果参见 JSON。
2. `python -m tools.r18_multiscene_ablation --dry-run --case-count 5`：生成 5 个不同、Pydantic 校验通过、包含 4 个仓库×温区组合层的预注册合成场景；仅生成输入，不求解；样例目录不打包，脚本可重复生成。
3. `python -m pytest -q backend/tests`：**61 passed, 1 skipped**（其中新增 R18 测试 14 条，旧回归测试不变）。验证包括 tamper 侦测、订单覆盖、独立等待/距离计算、相同距离比较约束、不同距离停止披露等待优化率、失败保留、文件覆盖防护、预注册快照一致性。
4. `node frontend/scripts/test-r15-evidence.cjs`：PASS。
5. `node frontend/scripts/test-r16-speed.cjs`：PASS。
6. Python `compileall`：PASS。
7. TSX 全局 TypeScript `transpileModule` **语法检查**：`App.tsx` 与 B-06 `Page.tsx` 通过。这不是完整 TS 严格类型检查 / Vite 构建。
8. `python scripts/build_file_map.py --check`：PASS。
9. 缺少求解器条件下，曾以三个**新**场景、每组 1000ms 执行端到端失败留痕烟雾检查：运行器返回非零退出码，每组记录 `incomplete`、有效对比数为 0、平均改善率为 `null`；仅证明不会将失败包装为成功，不构成调度性能证据。烟雾检查输出未打包。

## 当前环境未完成/保留的告警

- Python `ortools` 与 `simpy` 模块**均未安装**；尝试 `pip install ortools==9.15.6755 simpy` 因无网络 DNS 无法安装。因此不能独立验证 R18 新多场景的 CP-SAT、Routing 与 SimPy 完整实跑。用户 Windows 安装依赖后，可用 R18 新实验命令在用户本地实际执行。
- `npm run build`：当前环境没有 `frontend/node_modules`，停在 prebuild `ERR_MODULE_NOT_FOUND: openapi-typescript`，**未完成生产构建**。Windows 首次执行 `npm ci` 再构建。
- `python scripts/check_project.py`：静态架构检查报 R17 原有 `backend/app/application/coordinator.py`、`handle_event.py`、`http_services.py` 对 `adapters` 的直接引用。本次工具未修改这些文件，未以竞赛临赛的大规模架构调整消除既存警告。
- 数据库生产持久化、Agent 自然语言编排和更多异常类型不属本轮实现；不得在演示中误称已上线。

## 重要口径

- R17 原证据来自用户先前在 Windows 环境正式运行后上传的 JSON；本轮核算是与用户证据一致性复查，不是“重新求解”。
- R18 `--dry-run` 不运行算法，不能产生优化对照成绩。
- R18 真实实验一旦运行，务必保存 `raw/*_paired.json`、`manifest.json` 和 `summary.*`，包括失败组。完整运行记录取决于用户的 Windows 软件/硬件环境，不应默认为已完成。

## 附：Windows 实测与收尾验收（2026-10-14 晚）

本节由 R18 收尾验收追加，不修改上文正文与结论原文。

### 实测环境（与上文交付环境不同）

- Python 3.14.3；`ortools 9.15.6755`（`cp_model`、`constraint_solver` 均可导入）；`simpy 4.1.2`；node v24.19.0 / npm 11.17.0；`frontend/node_modules` 存在 → 本机可真实求解与构建。
- `python -m pytest -q tests`：**62 passed**（原记录 61 passed / 1 skipped，skip 因本机装有 simpy 而转为通过）。

### 真实运行 R18 五组

- 命令：`python -m tools.r18_multiscene_ablation --case-count 5 --budget-ms 90000`
- 运行目录：`benchmarks/b03/r18_runs/run_20261014_212550_205783/`（2026-10-15 交接清理时删除该运行目录；证据以冻结归档为准）（20 个文件）。
- 结果：**5/5 `complete_validated_pair` + `equal_distance`**；改善/持平/变差 = 5/0/0；描述性平均改善 **40.13%**（28.57 / 41.67 / 46.67 / 40.00 / 43.75）。
- 五组均订单全覆盖、原生校验 passed、逐单实算等待自洽、两组同为 90 秒预算、距离完全相同（50/54/56/56/56 km）；`s20_seed66` 与 R17 已验收档案一致。
- 冻结归档：`benchmarks/b03/r18_accepted/`（`r18_accepted_manifest.json` 记逐文件 SHA256，`r18_multiscene_audit.json` 记独立复算，5 组全部与运行 summary 一致）。

### 收尾修复（对应上文告警）

- 依赖清单：`backend/requirements.txt` 补 `simpy`，`requirements-lock.txt` 补 `ortools==9.15.6755`、`simpy==4.1.2` 及其运行依赖 → 上文“装完无法求解/ImportError”已消除。
- 证据生成器换行缺陷：`r18_evidence_audit.py`、`r18_multiscene_ablation.py`、`r17_joint_ablation.py` 的 `write_text` 显式使用 `newline='\n'`，Windows 不再把 LF 改写成 CRLF。
- `benchmarks/b03/r17_accepted/r17_arithmetic_audit.json` 已恢复交付包原始字节（SHA256 `f70edfc7…`），首次重跑造成的 `060fd844…` 已作废。
- 打包排除：`scripts/project_files.py` 不再收录 `benchmarks/b03/r18_runs/**` 运行产物与 `*.err` 文件；冻结归档 `r18_accepted/**` 仍随包交付。
- 前端生成产物 `frontend/src/client/generated.ts` 已用锁定工具链重生成并登记（`70a82f17…`，与 R17 包逐字节相同）；交付包原记录的 `8a3477e2…` 非本仓库工具链产物。
- `backend/app/application/handle_event.py` 的两处函数内 import 提到模块顶部（用户明确授权；不改逻辑）。
- 仍未解决：`scripts/check_project.py` 的既有 `application→adapters` 告警（`coordinator.py`/`handle_event.py`/`http_services.py`），涉及公共组合根，留待与 AC 协调后处理。

### 口径（不变）

合成场景、等预算成对、无显著性检验；40.13% 是「订单级累计备货完成→离仓等待」的描述性改善，不是距离或成本改善，也不是全局最优或真实县域普遍收益。

