# B：B01/B02 运输算法正式化

- 日期：2026-09-10
- 角色：B
- 契约版本：0.1.0 → 0.1.0（无公共契约变更）
- 基线：2026-09-10 团队统一 demo 协作骨架

## 本次实现

1. B01 固定矩阵适配器 `FixedTravelMatrixProvider`：按 matrix_id + version 获取快照矩阵，保留 None 不可达语义，校验节点顺序、维度和对角线。
2. B02 `OrToolsRoutingSolver`：实现 `RoutingRequest -> RoutingResult`。范围固定为单所属仓、一车一趟；按车辆复制订单内部节点，避免依赖 Windows 包的 SetAllowedVehiclesForIndex；约束车辆重量/体积、温区、装货就绪与窗口、订单服务窗口、保鲜截止、车辆班次和可选/必服务订单；支持冻结路线的节点顺序与时间。
3. 路线输出只暴露正式合同中的 `RouteStop`，内部车辆复制节点不泄漏到公共 DTO。
4. 独立运输校验 `domain/transport_rules.py` 不导入 Pydantic、OR-Tools、HTTP 或数据库，重新计算容量、温区、时间链、服务窗、保鲜、距离与车辆/订单覆盖。
5. 增加 B 运输矩阵/校验测试和可复现实验说明。

## 限制

- B02 首月保持“单仓、一车一趟、单温区车辆”的范围；多仓候选协调由上层 C/协调器负责。
- 装货没有独立服务时长字段，因此 B02 将 `warehouse_handoff.loading_window` 与 `ready_at_s` 约束到选中车辆的出发时刻；增加装货作业时长需要公共契约升级。
- RoutingModel 的可行解返回 `feasible`，不把有限搜索得到的解宣称为全局 `optimal`。
- 未找到解返回 `no_solution_within_budget`，除非是输入/兼容性预检能够在当前声明范围内直接证明无解。
- 当前骨架不新增 `/routing` HTTP 接口；B 的内部调用通过 `ports/routing.py`，由 AC 组合根接入。
