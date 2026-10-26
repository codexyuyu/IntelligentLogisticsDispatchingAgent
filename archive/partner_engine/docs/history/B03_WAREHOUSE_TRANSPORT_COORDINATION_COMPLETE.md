# B-03 仓运协同优化完成说明

## 完成目标

将 B-01 冷间仓储排程与 B-02 OR-Tools Routing 串成一条可验证的端到端仓运链路：

`仓内作业完成 / ready_at → 装车时间窗 → 车辆出发 → 路径运输 → 客户交付 → 回仓`

## 本次实现

1. 新增 `backend/app/application/coordinator.py`
   - 统一调用 B-01 CP-SAT 与 B-02 Routing。
   - 两阶段共享同一总预算，Routing 使用仓储求解后的剩余预算。
   - 支持按仓库分组后分别求解并聚合结果。
   - 最终生成统一 `CandidatePlan`。

2. 新增 `backend/app/domain/plan_rules.py`
   - 独立执行 B-03 跨域校验，不依赖 OR-Tools。
   - 校验 ready_at、loading_window、车辆/仓库/订单归属、必服务订单、重复服务、freshness deadline、路线时间连续性、duration 一致性、回仓时间等。

3. 修改 `backend/app/application/http_services.py`
   - `/api/v1/planning-jobs` 统一进入 B-03 coordinator，不再在 HTTP service 内重复拼接 B-01/B-02。

4. 新增 `backend/tests/test_b03_coordination.py`
   - 正向仓运链路测试。
   - `ready_at` 冲突反例测试。

## 当前 B-03 范围

- 保持 B-02 V1.1 的一仓一趟车辆模型。
- 不新增数据库表，不修改共享契约。
- 不做异常局部重排；异常重排留给 B-04。
- 不做 SimPy 事件注入；留给 B-05。
- B-03 当前重点是“仓库时序与运输时序能否正确衔接并被独立验证”。

## 验收条件

以下链路必须成立：

`B-01 warehouse_handoffs → B-02 RoutingRequest → RoutingResult → B-03 plan validation → CandidatePlan`

成功时 `CandidatePlan.validation.status = passed`，失败时不得返回假成功方案。


## R17 深度反馈迭代补充
原 B03 单轮基础闭环保留为 `sequential` 默认模式；本次新增 `deep` 显式选择支持真实出发反馈至 CP-SAT、Routing 重算、预算分配、逐轮质量选择与回退保护。详情见 [R17 专题指南](../R17_B03_DEEP_JOINT_OPTIMIZATION_GUIDE.md)。
