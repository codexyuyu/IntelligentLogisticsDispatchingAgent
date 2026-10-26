# B 运输场景

Owner: B。

当前正式 B02 使用 `data/scenarios/two_warehouses_20_orders.json` 作为快照来源，调用时通过 `contracts/examples/routing_request.json` 的公共字段构造 `RoutingRequest`。不要把历史 `reference_demos` 的分钟字段复制进正式业务契约。

B02 当前范围：单所属仓、一车一趟；车辆使用重量/体积双容量、单温区兼容、装货就绪/窗口、订单服务窗口、服务时长、保鲜截止和班次约束。未服务订单只有在 `required=false` 时允许通过 Disjunction 作为可选任务。
