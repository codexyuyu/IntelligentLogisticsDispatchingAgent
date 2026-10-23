# N01-R02 完整枚举与十类事件映射

本轮新规范决定，待独立复核；表从当前规范附表读取。不是旧示例的11字符串，也不是业务Schema导出。

| 成员名 | 精确序列化值 | 引用目标 | ID | revision |
| --- | --- | --- | --- | --- |
| ORDER | `order` | Order | id | row_version |
| CARGO | `cargo` | Cargo | id | row_version |
| VEHICLE | `vehicle` | Vehicle | id | row_version |
| DRIVER | `driver` | Driver | id | row_version |
| WAREHOUSE | `warehouse` | Warehouse | id | row_version |
| WAREHOUSE_ZONE | `zone` | WarehouseZone | id | row_version |
| STORAGE_LOCATION | `location` | StorageLocation | id | row_version |
| DOCK | `dock` | Dock | id | row_version |
| WORKER | `worker` | Worker | id | row_version |
| EQUIPMENT | `equipment` | Equipment | id | row_version |
| TRANSPORT_TASK | `transport_task` | TransportTask | id | row_version |
| WAREHOUSE_TASK | `warehouse_task` | WarehouseTask | id | row_version |
| ROUTE | `route` | Route | id | row_version |
| ROUTE_STOP | `route_stop` | RouteStop | id | row_version |
| SCHEDULE | `schedule` | Schedule | id | row_version |
| SCHEDULE_TASK | `schedule_task` | ScheduleTask | id | row_version |
| SCHEDULE_VERSION | `schedule_version` | ScheduleVersion | id | row_version |
| CONSTRAINT | `constraint` | Constraint | id | row_version |
| OPTIMIZATION_REQUEST | `optimization_request` | OptimizationRequest | id | row_version |
| OPTIMIZATION_RESULT | `optimization_result` | OptimizationResult | id | row_version |
| SIMULATION | `simulation` | Simulation | id | row_version |
| SIMULATION_SNAPSHOT | `simulation_snapshot` | SimulationSnapshot | id | row_version |
| EVENT | `event` | Event | id | row_version |
| EXCEPTION_EVENT | `exception_event` | ExceptionEvent | id | row_version |
| RESCHEDULE_REQUEST | `reschedule_request` | RescheduleRequest | id | row_version |
| RESCHEDULE_RESULT | `reschedule_result` | RescheduleResult | id | row_version |
| AGENT_RUN | `agent_run` | AgentRun | id | row_version |
| TOOL_CALL | `tool_call` | ToolCall | id | row_version |
| DECISION_RECORD | `decision_record` | DecisionRecord | id | row_version |
| EXPERIMENT | `experiment` | Experiment | id | row_version |
| METRIC | `metric` | Metric | id | row_version |
| EXPERIMENT_RESULT | `experiment_result` | ExperimentResult | id | row_version |
| PLANNING_SNAPSHOT | `planning_snapshot` | PlanningSnapshot | id | row_version |
| JOB | `job` | Job | id | row_version |
| JOB_ATTEMPT | `job_attempt` | JobAttempt | id | row_version |
| IDEMPOTENCY | `idempotency` | Idempotency | id | row_version |
| RESERVATION | `reservation` | Reservation | id | row_version |
| INVENTORY_LEDGER | `inventory_ledger` | InventoryLedger | id | row_version |
| OUTBOX | `outbox` | Outbox | id | row_version |
| AUDIT_ENTRY | `audit_entry` | AuditEntry | id | row_version |
| LIFECYCLE_EVENT | `lifecycle_event` | LifecycleEvent | id | row_version |
| EXECUTION_SNAPSHOT | `execution_snapshot` | ExecutionSnapshot | id | row_version |
| CONFIRMATION_TOKEN | `confirmation_token` | ConfirmationToken | id | row_version |
| TRAVEL_MATRIX | `travel_matrix` | TravelMatrix | id | version |
| REGION | `region` | RegionRef | region_id | 必须 null |

| payload.kind | 合法 entity_ref.kind | 引用目标与 ID 一致性 | revision |
| --- | --- | --- | --- |
| vehicle_failure | vehicle | entity_ref.id = vehicle_id；Vehicle.id | 给定时等于事实快照 row_version |
| transport_delay | transport_task | entity_ref.id = transport_task_id；TransportTask.id | 给定时等于事实快照 row_version |
| traffic_disruption | travel_matrix | entity_ref.id 选中 snapshot.matrices 的一个 TravelMatrix.id；全部弧限定在该矩阵 | 必填且等于矩阵 version |
| weather_change | region | entity_ref.id = region_ref.region_id；内嵌显式节点集合 | 必须 null |
| cargo_anomaly | cargo | entity_ref.id = cargo_id；Cargo.id | 给定时等于事实快照 row_version |
| order_cancellation | order | entity_ref.id = order_id；Order.id | 给定时等于事实快照 row_version |
| demand_increase | order | entity_ref.id = order_id；Order.id | 给定时等于事实快照 row_version |
| demand_decrease | order | entity_ref.id = order_id；Order.id | 给定时等于事实快照 row_version |
| equipment_failure | equipment | entity_ref.id = equipment_id；Equipment.id | 给定时等于事实快照 row_version |
| warehouse_resource_unavailable | warehouse / zone / location / dock / worker / equipment | entity_ref = resource_ref，kind/id/revision 全值相等；解析真实仓库或资源 | 给定时等于事实快照 row_version |

交通采用一个既有矩阵及非空、唯一、非自环有向弧，节点属于该矩阵，新版本严格前进；跨矩阵拆事件。天气节点非空唯一且属于场景矩阵并集，同场景版本同region_id固定节点集合；受影响矩阵的版本全部前进，无受影响弧可保留为显式无作用输入。仓储两份引用完全一致，warehouse保持独立本体，不扩充Resource五分支；zone不增加calendar。完整规则以DATA_CONTRACTS及规范JSON为准。
