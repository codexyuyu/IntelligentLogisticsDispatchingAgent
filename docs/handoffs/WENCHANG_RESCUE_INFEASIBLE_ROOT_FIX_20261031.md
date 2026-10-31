# 文昌校区三车故障救援：INFEASIBLE 根因修复与验收

## 根因（不是容量数据本身不可行）

`fault_rescue_showcase.py` 使用了时间/载重维度的 **from-index transit callback**。
故障时冷藏车 01 已完成 O1 卸货，车辆从 O1 作为 RoutingModel 的 `Start(0)` 继续出发；初始载重是尚未交付的 O2（1 件）。旧回调却仅根据节点名判断：`O1` 是配送节点，因此在 **车辆起点** 再次对 O1 执行 `demand=-1`；到 O2 时又执行 `-1`，使累计载重变成负数。RoutingModel 的容量维度下界 0 因而把所有相关路线排除。

旧时间回调在这个已完成 O1 卸货的车辆起点又计入一次 70 秒卸货服务，导致接续路线时间偏差。此问题也一并修复：**起点不重复执行节点作业**，仅对真正参与后续求解的客户节点应用需求和服务时间。

## 修复方法

1. `_load_change` / `_service_seconds` 显式区分 `routing.IsStart`，不对车辆起点再次减货或计时。
2. `_construct_rescue_seeds` 独立构造所有可能的 O4/O5 救援归属组合（不固定救援车），先验证容量、交接、软时效和时限；当前 fixture 至少有一条业务可行路线。
3. OR-Tools 使用 `ReadAssignmentFromRoutes` 读取候选起始路线，并通过 `SolveFromAssignmentWithParameters` 搜索；如初始路线被模型拒绝或没有求得解，保留冷启动求解路径。
4. 采用 `_validate_candidate` 二次校验最终实际求解结果：冻结前缀、取货先于配送、全体订单唯一覆盖、容量、服务时长、行驶时间连续性及车辆返场。
5. 不再把 `SolveWithParameters()` 没有返回结果一概解释为业务容量不满足。失败时返回诊断阶段和准确的“模型拒绝初始解/预算内无解”状态，并禁止审批。

## 本地单次验收（无需任何数据库）

在安装了本项目 Python 环境（含 OR-Tools）的源码根目录运行：

```bash
python scripts/check_fault_rescue_solver.py
```

预期 `status=solved`, `candidate_valid=true`, `recovered_orders=2`，O4/O5 各被车 01 或车 03 接管，并显示 8 单完成、故障后不救援为 6 单完成。**以上是验收标准，不能在未实际跑过 OR-Tools 前宣称已达成。**

检查无数据库连接、无数据写入、无 Git 推送。文昌地图、仓库 3D、DeepSeek 和其他调度业务均保留。

## 现有环境限制

本打包环境没有安装 OR-Tools，且无法在线获取；纯逻辑的 pytest 检查可以运行，真实 RoutingModel 求解必须在用户已安装 OR-Tools 的本地环境执行。若仍返回模型拒绝，请提供返回的 `solver_diagnostic`。
