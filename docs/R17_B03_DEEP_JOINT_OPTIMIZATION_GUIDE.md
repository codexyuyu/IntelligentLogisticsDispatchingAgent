# R17 / B-03 仓储—运输深度双向协同：交付、操作、测试与 AI 接口说明

> 基于 R16_SPEED 原工程增量开发。保留 React + FastAPI + OR-Tools CP-SAT + Routing + SimPy；不修改已有场景、车辆矩阵、B-06 随机 Seed 生成、R16 快检预算和异常局部重调度逻辑。R16 应保留备份。

## 1. 这次真正完成的算法升级

R16 单轮链路：`仓储 CP-SAT → 订单 ready_at → Routing → 联合校验`。

R17 深度模式（**显式选择才运行**）：

1. 保留 R16 单轮求解，取得**通过独立校验的初始保底方案**。
2. 从 Routing 真实路线的**仓库出发时刻**提取每个已服务订单的 `WarehouseDepartureTarget`，不是误用“回仓到达时间”。
3. CP-SAT 重新计算实际仓库作业开始、结束及资源安排：**首先重罚超出目标发车时刻的备货延误，并识别每辆车负责的订单组，优先让同一辆车的货物尽早全部备齐，随后减少过早备货造成的交接等待**。资源互斥、作业时间窗、先后关系、冻结任务和不可用窗口仍是硬约束；反馈目标是软目标，不会伪造无解。
4. 用更新后的 `warehouse_handoffs` **重新调用 OR-Tools Routing**，重新检查车辆温区、载重/容积、配送时间窗、线路距离、司机班次和货物新鲜度。
5. 独立检查仓库操作和交接 ready_at 一致性、仓储排程、Routing、跨域时序与订单覆盖，任意校验未通过都不采纳该候选。
6. 仅当候选方案按以下**字典序目标严格优于目前的合法方案**才采纳：`未服务订单数 → 总运输距离 → 逐订单备货结束到出发的等待总秒数 → 仓储最晚完工时间 → 路线累计时长`。不会用更长路线换取较短等待（除非服务订单数先得到改善）。
7. 在同一请求预算内最多三轮；耗尽或新方案未改善时停止，**返回已经验证的保底方案**，不会因为反馈阶段失败而失去原本可行的方案。

**注意：** 这是一种具备求解反馈的分解协调优化，不是数学上证明全局最优的单个 CP-SAT+VRP 联合模型。局部反馈不保证每一轮距离下降；真正改善了什么请看轮次证据，不能虚构提升。

## 2. 页面在哪里、如何演示

访问 `http://127.0.0.1:5173/` → 左侧 **智能调度 → 联合调度**。选择：

- **深度双向协同（最多 90 秒）**：第一次演示建议先运行预装 20 单双仓场景。90 秒是整个协调任务的预算；后端当前 Planning Job 是同步执行，页面请求期间可能看起来没有进度，属既有运行方式。
- **单轮仓运衔接（60 秒）**：R16 行为作为稳定保底。无需改变 B-06 的快速/标准评测界面。

运行成功后，查看**R17 双向协同 · 可追溯求解证据**区：初始/最终运输距离、逐订单交接等待、尝试与入选轮次、是否通过独立校验、每轮求解耗时以及未采纳原因。**导出仓运协同 JSON 证据** 保存完整快照、最终 CandidatePlan、校验信息和每轮指标。页面同时把原本错误的“窗口结束 ≤ 发车”修正为“`ready_at ≤ 发车 ≤ 窗口结束`”。

如果没有改善，页面会如实显示“第 1 轮入选”，这是有效结果而不是运行失败。**不需要展示虚构的优化率。**

## 3. Windows 从零启动（两个 PowerShell 窗口）

推荐解压根目录：`D:\1aaaqianduan\915_B03_DEEP_JOINT_OPTIMIZATION_R17`，确保实际不存在多余嵌套目录。先关闭旧的 R16 服务（端口 8000 和 5173）。

**窗口 1 / 后端：**

```powershell
cd "D:\1aaaqianduan\915_B03_DEEP_JOINT_OPTIMIZATION_R17\backend"
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康与接口定义：`http://127.0.0.1:8000/docs`。

**窗口 2 / 前端：**

```powershell
cd "D:\1aaaqianduan\915_B03_DEEP_JOINT_OPTIMIZATION_R17\frontend"
npm ci
npm run test:evidence
npm run test:speed
npm run build
npm run dev
```

`npm run build` **自动根据 R17 的 OpenAPI 合约再生成 TypeScript API 类型**；先 `npm ci` 安装 openapi-typescript。首次依赖安装需要网络。打开 `http://127.0.0.1:5173/`。

**本机先验收一轮后端：**

```powershell
cd "D:\1aaaqianduan\915_B03_DEEP_JOINT_OPTIMIZATION_R17\backend"
python -m pytest -q tests
```

R17 算法比较完后，请导出 JSON 发回用于确认：`coordination.mode`、`selected_round`、`rounds[*].reason`，及完整校验是否通过。

## 4. 正式证据：同场景、同总预算对照（比赛建议保留）

页面上的“单轮 60 秒”和“深度 90 秒”便于展示，**不是严格公平的算法性能对照**。要展示“深度模式优于单轮模式”，应在**同一输入快照、相同 CPU/版本、相同总预算**条件下比较。

后端目录执行下面的一次命令，程序会分别跑两个模式，真实保存两份完整 CandidatePlan、快照 SHA256、各自端到端求解时间、每轮调度反馈和合法性结果：

```powershell
cd "D:\1aaaqianduan\915_B03_DEEP_JOINT_OPTIMIZATION_R17\backend"
python -m tools.r17_joint_ablation --scenario "../data/scenarios/two_warehouses_20_orders.json" --budget-ms 90000 --output "r17_joint_evidence.json"
```

这个命令是两组各 90 秒预算，整体耗时可能较长；这是**比赛数据采集**，无需每天重复。可传其他正式场景快照 JSON（完整 `PlanningSnapshot` 或带 `snapshot` 属性的 JSON）及不同 `--budget-ms`。如一方失败，JSON 将保留错误说明，不会做虚假距离比较。**至少多个不同场景才可讨论平均值与波动**，不能凭一组成绩宣传普遍增益。

另一个完整快检：原有 B-06 S50 / 17 快检仍按 R16 的 12 秒预算运行，不会因为新功能变成多轮。通过后再进行其他评测。

## 5. 给成员 C / Agent 的正式工具接口

沿用 API：`POST /api/v1/planning-jobs`，无需额外定义一套 Order/Vehicle DTO。增加**可选字段** `coordination_mode`，旧调用无需改动：

```json
{
  "snapshot_id": "snap_initial",
  "expected_snapshot_version": 1,
  "order_ids": ["ord_001", "ord_002"],
  "budget_ms": 90000,
  "max_coordination_rounds": 3,
  "coordination_mode": "deep"
}
```

上例的 `snapshot_id/order_ids` 必须替换为实际已导入场景。`coordination_mode` 默认为 `sequential`；仅当 mode=`deep` 且轮次大于 1 时才进行反馈。返回方式仍为 JobAccepted → GET `/api/v1/jobs/{job_id}` → GET `/api/v1/plans/{plan_id}`。

`CandidatePlan` 新增**可选** `coordination`：包含 `mode`、`requested_rounds`、`attempted_rounds`、`selected_round`、初始与最后的距离/交接等待、每轮的状态/指标/采纳原因。其他接口字段保持兼容；Agent **只能解释实际校验通过的结果，不得编造路径、优化率或重排成功**。

## 6. 数据、验证与可信度边界

本次修改不包含以下功能，不能宣称已完成：

- 实时交通/OSRM 真实地图、多趟配送或在途车辆重规划；
- 把库存容量、温度资源特性、预冷和清洁转换成完备 CP-SAT 约束（当前公共 Operation 合约不足）；
- 仓库出库执行事务与 PostgreSQL 持久化；
- 全局最优证明、跨不同业务场景的普遍优化率；
- AI Agent 的工具编排（成员 C 负责）。

本次新增的**真实独立约束校验**会检查手工伪造的 warehouse_handoff.ready_at，但为了兼容已有 B-04 历史测试数据中“尚未填操作明细”的旧方案，不会对完全缺失的仓储操作记录做溯源推断。新生成的 B-03 路径会通过 CP-SAT 排程验证与交接检查双重验证。

**当前交付环境确认项：** 后端测试 47 passed / 1 skipped；前端 `npm run test:evidence` 和 `npm run test:speed` 通过；TSX 语法编译解析通过；OpenAPI / JSON schema 已重新导出并确认无漂移。**本环境没有 OR-Tools 运行库和完整 npm node_modules，因此不能声称真实 R17 求解、全部前端构建及 Windows 运行已经验证**，需按上述步骤本机完成验收。`scripts/check_project.py` 还包含来自早期版本的 “application 不直接引用 adapters” 架构治理检查；当前原有 coordinator、handle_event、http_services 直接引用实现，会触发这一静态检查。本次没有为满足静态检查而全面改造成员 A 的组合根，因为会增加临赛回归风险；这是留给团队的架构治理事项，不影响已经通过的后端业务单元测试。

## 7. 排障快速判断

- 看见第 1 轮入选：属于**没有找到更优且合法的反馈方案**，不是失败。
- `feedback` 轮出现 `rejected:`：检查相应失败类型；最终方案仍取上一个合法解。
- `warehouse_solver_failed`：说明 CP-SAT 在预算内没得到可行解；不能直接断言业务无解。
- `routing_solver_failed`：说明 Routing 未找到可行方案；优先检查时间窗、容量、温区、预算。
- `coordination_validation_failed`：说明真实约束校验未通过；不可跳过校验或手动修改指标。
- 页面没有报告区：请先运行一次 R17 方案，确认不是沿用 R16 后端进程。
