# B 运输基准入口

Owner: B。

基准输入建议固定：`data/scenarios/two_warehouses_20_orders.json` + `contracts/examples/routing_request.json`，记录：

- order 数量、车辆数量、矩阵版本
- budget_ms / max_workers / random_seed
- raw_status、SolveStatus、has_solution、solve_ms
- 总里程、总运行时长、车辆使用数、未服务订单数
- 独立运输校验结果和违规列表

注意：`feasible` 是“在声明求解范围和预算内找到可行解”，不表示已证明全局最优。
