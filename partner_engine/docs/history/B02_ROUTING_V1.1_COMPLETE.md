# B-02 Routing V1.1 完成说明

本版本在团队统一框架内完成运输路径规划主链路：

`RoutingRequest → FixedTravelMatrixProvider → OR-Tools RoutingModel → vehicle assignment / stop sequence / arrival time → distance & duration → independent transport validation → RoutingResult`

## 已实现

- 固定所属仓的一车一趟运输范围
- 订单必服务/可选服务
- 车辆载重与体积容量
- 车辆冷链温区兼容
- 车辆班次与可用时间
- 仓库 ready_at / loading_window
- 订单服务时间窗
- 服务时长真正进入 RoutingModel 时间维度
- freshness deadline
- 冻结路线约束
- versioned travel matrix adapter
- 不可达边不被转换为 0 成本/0 时间
- 独立运输校验，不调用 OR-Tools
- 无解与预算耗尽的状态语义分离

## 成本说明

当前共享 `RoutingResult` 契约没有 transport_cost 字段，因此本版本不伪造一个公共字段。`adapters/routing/metrics.py` 提供显式 vehicle cost-per-km 输入的运输成本侧算子；公共契约未来经 AC 的 contracts change 流程增加成本字段后，再接入 `RoutingResult`。

## 已知范围

- B-02 V1.1 固定单仓、一车一趟。
- `warehouse_handoffs` 在本版本作为整车出发装载窗处理，因此同车多订单的装载窗必须存在共同交集；更细粒度的月台作业排程属于后续仓运协同。
- 需要真实路网时，替换 matrix provider，不改 RoutingModel 的主接口。
