# 20261024-1600 · PARTNER · 演示收尾：R05→R08→R09 闭环、协商 transcript、未知等待修

- 角色 / 日期 / 基线：PARTNER / 2026-10-24 / 基线 `8156718`（PR #5），分支 `partner/r09-final-demo-20261024`
- 目标：10-26 组会演示可用；不扩展架构、不改甲方文件
- 完成及修改文件：
  - 新增 `backend/app/application/negotiation_link.py`（R08 绑到**已求解**计划：任务=CP-SAT 排出的装载工序、窗口=该工序 release/deadline、仓储角色绑 CP-SAT 指派资源、运输角色绑实际承运车辆 + 该单 handoff）
  - 新增 `backend/tools/r09_demo_loop.py`（一键闭环：场景 → 确定性 R05 合成层 → `coordinate` 真跑 CP-SAT+Routing → 协商 → 观测 → 打印 + 落 JSON）
  - `backend/app/application/contract_net.py`：新增 `format_transcript(result)`（演示用逐行 transcript）
  - `backend/app/application/plan_observations.py`：`handoff_wait_s` 改为 `int | None`，新增 `measured_handoff_wait_s` / `unmeasured_handoff_orders`（**未知不再是 0**）
  - `backend/app/application/coordinator.py`：校验失败信息带上 status 与未校验规则（原来只有空字符串）
  - 修复 R05 建模/校验的**作用域越界**（本轮闭环暴露的真实缺陷）：`coldchain_model._occupancy_bounds` 增加 `scope`，`coldchain_timeline`、`coldchain_checks.derived_occupancies/check_resource_requirements/check_precool/check_exposure` 跳过请求范围外的工序与批次；否则按订单子集求解会 KeyError 或误报
  - 新增 `backend/tests/test_r09_demo_loop_unit.py`（5 条，含 4 次真求解）
- 契约版本：**0.2.0 未变**（无 DTO 改动，`export_contracts --check` 通过）
- 验证（Windows，Python 3.12.10，`PYTHONUTF8=1`）：
  - `pytest -q tests/test_r09_demo_loop_unit.py` → **5 passed**（27.7 s，含 4 次真实 CP-SAT+Routing）
  - backend 全量 → **345 passed**（基线 340 + 5）
  - `check_project.py` → PASS；`verify_delivery.py` → 12/12 exit 0；`build_file_map` 通过
- 演示运行方法：
  ```powershell
  .\.venv\Scripts\python.exe backend/tools/r09_demo_loop.py --max-orders 3 --budget-ms 12000 --out-dir ..\tmp\demo
  ```
  输出：plan id / 校验状态 / 覆盖数 / R05 证据（峰值、暴露、换批）/ handoff 等待（可测量与不可测量分别计数）/ 逐单协商结论 + 完整 transcript；`--out-dir` 落 `r09_demo_loop.json`
- 本轮实测（3 单、12 s 预算）：`validation=passed`；R05 `peaks=1 exposures=3`；协商 3/3 `confirmed`（warehouse 中标，transcript 同时记录 transport 报价）；等待 3 条全部可测量
- 未完成 / 剩余阻断：
  - 20 单全量闭环未在本机跑通：warehouse 预算按 30% 分配，20 单在 8–12 s 总预算下可能返回 `UNKNOWN`，演示建议 3–6 单、总预算 ≥12 s，或单列调参
  - R05 合成层是**演示数据**（`source_kind=simulation`），不可称为真实企业采集
  - 甲方仍未实现冷链域独立校验与持久化；本闭环的 `passed` 只代表 adapter 侧 `r05.*` 全部可校验且通过（预冷/容量/暴露/换批/需求/相容）
