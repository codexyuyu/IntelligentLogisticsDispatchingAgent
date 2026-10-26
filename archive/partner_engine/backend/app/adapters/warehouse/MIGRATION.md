# B-01 CP-SAT 迁移说明

- 来源：旧 `archive/legacy/algorithm-service/app/main.py` 的 B-01 CP-SAT V1.2。
- 新入口：`CpSatWarehouseScheduler.schedule(WarehouseScheduleRequest)`。
- 统一边界：`app.ports.warehouse.WarehouseScheduler` 与 `app.contracts.planning`。
- 独立校验：`WarehouseScheduleValidator`，不复用 CP-SAT 建模函数。

## 当前契约边界

新的团队共享契约以 `Operation`、`WarehouseResource`、`ScheduledOperation` 为仓储排程对象。
因此这里只迁移契约已经表达的硬约束：

1. release_at_s / deadline_at_s；
2. 资源 available / unavailable windows；
3. 同一资源非重叠；
4. predecessor_ids 先后约束；
5. frozen_operations 事实冻结；
6. 求解预算与状态语义。

旧版 B-01 中的“批次数量、订单分配量、温区/品类、冷间库存容量”等 richer 字段没有在当前共享契约中等价表达，不能在迁移层自行猜字段或改变公共契约。因此旧 `archive/legacy/algorithm-service` 保留作为回归基线；待团队通过契约变更后，再迁移这些扩展约束。
