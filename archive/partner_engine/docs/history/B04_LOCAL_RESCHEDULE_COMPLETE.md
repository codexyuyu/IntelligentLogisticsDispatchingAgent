# B-04 异常局部重排完成说明

## 阶段目标

在 B-01 冷间排程、B-02 Routing、B-03 仓运协同的统一新框架之上，实现事件驱动的局部重排。

B-04 V1 的正式可运行场景为：**车辆出发延误（`departure_delayed`）**。

## 已完成

1. `backend/app/application/impact_analysis.py`
   - 根据异常车辆路线识别受影响订单。
   - 受影响车辆整条路线进入重排，避免只改一部分车辆路线。
   - 其余订单进入 locked scope。
   - 不直接修改旧计划。

2. `backend/app/application/handle_event.py`
   - 校验事件与原计划 snapshot/version 一致。
   - 生成版本化派生 snapshot。
   - 仅调整异常车辆的 `available_at_s`。
   - 保留未受影响路线，并使用 Routing 的 `frozen_routes` 固定它们。
   - 对受影响范围重新调用 OR-Tools Routing。
   - 重新执行 B-02 transport validator 与 B-03 plan validator。
   - 生成新的 CandidatePlan，版本号递增。
   - 输出新旧方案差异。

3. `backend/app/contracts/reschedule.py`
   - 增加 `ImpactAnalysis`、`PlanDiff`、`LocalRescheduleResult`。

4. `backend/app/application/runtime.py`
   - 增加 snapshot history，支持事件后派生版本继续追溯原 snapshot。
   - 保存事件重排结果。
   - 支持按 snapshot/version 查找当前有效计划。

5. `backend/app/application/http_services.py`
   - `/api/v1/events` 已接入 B-04 局部重排。
   - 保留幂等键。
   - 生成 replanning job，并把新计划写入运行时。

6. `backend/app/contracts/http.py`
   - `EventAccepted` 增加 B-04 重排结果。

7. `backend/tests/test_b04_reschedule.py`
   - 覆盖车辆延误、受影响订单识别、未受影响路线冻结、snapshot 版本递增、计划版本递增和新旧方案变更。

## 完整链路

`DispatchEvent(departure_delayed)`
→ 影响范围分析
→ 派生 snapshot v+1
→ 冻结未受影响路线
→ OR-Tools Routing 局部重算
→ B-02 独立校验
→ B-03 仓运协同校验
→ 新 CandidatePlan
→ 新旧方案差异

## 当前 V1 边界

当前只把 `departure_delayed` 做成真实局部重排闭环。`dock_unavailable`、`cargo_quarantined`、`weather_changed`、`demand_changed` 已保留在共享事件契约中，但不在本次 V1 中假装已经完成处理；这些事件将在后续扩展到冷间故障、道路异常和订单变化。

另外，B-04 V1 要求车辆延误事件发生在原计划车辆出发之前；车辆已经进入在途状态后的重排属于后续状态机扩展。

## 验证结果

当前开发环境执行：

`pytest -q backend/tests`

结果：**32 passed**。

端到端 OR-Tools 实际求解需要项目声明的 OR-Tools 运行环境；当前容器没有可用的 Linux OR-Tools wheel，因此本次无法在容器里再跑一次真实求解器。B-04 的事件编排、影响分析、契约和独立校验均已通过测试。

### 2026-09-12 runtime fix: multi-warehouse orchestration

The B-02 V1 solver intentionally rejects a single RoutingRequest that mixes warehouses. B-04 now partitions a local replan by warehouse, keeps frozen routes scoped to the same warehouse, runs one RoutingModel per warehouse, and aggregates the results before the existing transport/plan validation. This preserves the B-02 V1 contract while allowing B-04 to operate on the multi-warehouse project scenario.


### Scope fix
B-04 now preserves request-local order scope; it no longer requires warehouse handoffs for orders from the imported snapshot that were not included in the previous planning job.
