# N01-R02 唯一阻断修复 · 待独立复核

结论：**READY_FOR_INDEPENDENT_REVIEW**。N02-R01-F02-C01 的完整枚举、十类事件引用映射、显式闭包及设计检查已完成；是否解阻由独立 Codex N02-R02 裁定。**G00 当前无效，N03 不可启动；P02未启动。** 本轮没有更新官方冻结/Gate，没有执行 `--record-g00`，没有签G01。

实施身份：`Codex N01-R02 /root`；交付时间UTC：`2026-10-04T14:17:51.912907+00:00`。实际工作根：`D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，`.git`不存在；沿用会话模型，三个子任务未覆盖模型。协作审读只辅助本轮实施，不替代下一轮独立复核。

计划 `1.0.3`，业务契约 `2.0.0`，Gate证据格式 `1.0.0`。2.0.0候选尚未被接受，本轮补齐其中未决规范，不宣称对已发布2.0.0兼容，也不改manifest版本。此前32实体及11辅助实体已经在领域目录，本轮地址空间决定不新增业务实体/字段/表/API。

输入候选：`content-sha256:adbd8a1ccfa59e8b803acfbb8beb6e23d8fbdad28a51ededbb5862ee0c79ee98`。

新候选：`content-sha256:d1c94436a020158a0573d290443c7c6799711da6564b1609a294fb332d8b7f63`。

新dirty-tree：`content-sha256:1f46a24cc017ed209fc3c049239de9be1cea7053992e4d49469af98c6addeed0`。

两种公式各自复算；候选集合77项，独立整树遍历与现行runner一致，变动恰为5项。[逐文件新候选](../../../artifacts/handoffs/N01-R02/codex/candidate-after.json)、[原候选](../../../artifacts/handoffs/N01-R02/codex/candidate-before.json)、[精确差异及前后hash](../../../artifacts/handoffs/N01-R02/codex/governance-diff.json)、[原文本diff](../../../artifacts/handoffs/N01-R02/codex/governance-diff.patch)、[改前原字节](../../../artifacts/handoffs/N01-R02/codex/before/docs/architecture/DATA_CONTRACTS.md)保留可复核输入。报告、日志、示例和tmp不混入候选身份。

## 完整枚举与引用目标

45项 = 领域目录32实体 + 11必需辅助实体 + TravelMatrix/RegionRef两个既有纯值目标。成员名和精确序列化值为本轮规范决定；旧脚本的11字符串没有被冻结为规范。zone/location保留既有资源边界标签；不接受warehouse_zone/storage_location别名或大小写变体。

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

EntityKind仍由P02-01 `states.py`唯一定义；EntityRef仍由P02-01 `primitives.py`唯一定义，字段为 `kind:EntityKind; id:UUID; revision:NonNegativeInt?`。提供修订时按选定事实快照检查；null只声明身份，不宣称当前版本一致。RegionRef无实体行，revision必须null；矩阵事件修订必填。元数据中的未来目标名不构成早期模型导入，历史审计/冲突记录保留当时事实，不按不断变化的live行统一重验。

## 十类事件映射

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

交通：同事件绑定一个现有矩阵，arc_refs非空、唯一、无自环，两个端点属于该矩阵；反向有向弧仍不同。跨矩阵拆事件，new_matrix_version严格大于旧version；ArcRef字段未改。

天气：内嵌节点集合非空唯一，节点属于场景矩阵并集；同场景版本同region_id绑定同集合，乱序不改变集合。影响每个矩阵中两个端点均在集合内的弧，新版本严格大于全部受影响矩阵版本；无受影响弧可作为明确无作用输入保留，不能虚构新弧或Region表。

仓储：两份引用kind/id/revision全值相等，限定Warehouse及五资源，解析同scope真实对象；warehouse不加入Resource五分支，zone不补calendar。既有TimeWindow闭窗与占用半开区间语义未改。

完整规则：[DATA_CONTRACTS](../../architecture/DATA_CONTRACTS.md)、[类型归属](../../architecture/TYPE_DEFINITION_OWNERSHIP.md)、[规范JSON](../../../contracts/changes/N01-R01-contract-decisions.json)、[本轮迁移追加](../../../contracts/changes/N01-R01-contract-freeze-2.0.0.md)。可独立读取的全表也在[枚举与映射](../../../artifacts/handoffs/N01-R02/codex/enum-and-event-tables.md)。

## 实跑与范围核验

| 检查 | 实测结果 | 原始证据 |
| --- | --- | --- |
| `python -B tools/ai_coding_plan/validate_plan.py --self-test` | exit0；73项、109Task/40Gate、errors=[] | [最终日志](../../../artifacts/handoffs/N01-R02/codex/validator/plan-validation-02.log)、[真实argv/cwd/UTC/输入hash](../../../artifacts/handoffs/N01-R02/codex/validator/plan-validation-02-command.json) |
| `python tmp/N01-R02/examples/verify_design_examples.py final01`（由capture启动） | exit0；268/268 = 原95 + 新173，正例81/反例92；114生成输出隔离字节复现 | [日志](../../../artifacts/handoffs/N01-R02/codex/examples/contract-check-final01.log)、[命令](../../../artifacts/handoffs/N01-R02/codex/examples/contract-check-final01-command.json)、[逐项结果](../../../artifacts/handoffs/N01-R02/codex/examples/contract-validation-final01.json)、[实例](../../../artifacts/handoffs/N01-R02/codex/examples/contract-examples-final01.json) |
| `python -B tmp/N01-R02/audit_final.py`（由capture启动） | exit0；77候选、5差异、3786保护；原43测试AST和record_g00的AST/原bytes未变 | [日志](../../../artifacts/handoffs/N01-R02/codex/final-audit.log)、[摘要](../../../artifacts/handoffs/N01-R02/codex/audit-summary.json)、[保护核验](../../../artifacts/handoffs/N01-R02/codex/protected-file-audit.json) |

规划负例包括EntityKind退回existing、定义缺失、成员遗漏、重复序列化值/JSON成员、EntityRef字段/归属漂移、映射缺项/错kind/错目标/不可解析或非UUID的ID路径。设计正反例从当前规范读取枚举与映射，涵盖45个值、十事件合法引用、未知值、错误目标、ID/修订不一致、缺目标，以及交通多弧、天气区域和全部六个仓储kind。它们验证设计谓词，不是已交付业务handler。

首次完整规划检查实际exit1：EntityRef显式字段暴露了遗漏的 `primitives → states` 单向模块边。已补此同P02-01边并使用新输入重新实跑；任务祖先/顺序和其他模块边未改。[原失败日志](../../../artifacts/handoffs/N01-R02/codex/validator/plan-validation-01.log)与[原输入hash](../../../artifacts/handoffs/N01-R02/codex/validator/plan-validation-01-command.json)保留；没有把旧输入的通过结论迁给新输入。前期71项局部自测试日志只作历史记录，最终73项才绑定新候选。

最终日志sha256：规划 `2e8da1ef32acbe18bb8aac40f8f907fa54debea4108faac70b57b2d409151fff`；设计 `da533b48ca41f9003d107e48f8eaa60f53d035e4cce5dddfe90db8cfcd9a60e2`。当前输入逐项匹配。原43项断言未删改，增加30项；record_g00函数原字节sha256 `6726a1f866e9f345ac6ea3feeba4d924bad6e1381ace601e9fbeb5c5632b88a9`保持一致。[AST保护证据](../../../artifacts/handoffs/N01-R02/codex/validator/ast-protection-final.json)。

保护3786项全部未变，范围外新增/删除为空。5个既有文件均在用户白名单内；196个类型未增减，EntityKind/EntityRef显式化、十payload仅追加引用规则，其他类型全部字节结构一致，JobKind、Scenario字段/隔离、Calendar、JobRequest未重做。业务实现、OWNERSHIP、锁、manifest、原Prompt、他人交接、历史示例、冻结JSON/MD和G00/G01及旧日志均未改。新增只在本轮三个授权目录。

## 迁移影响、验证边界与后续

新候选使受影响旧审查/契约证据失效；未来domain → DTO → ports → 消费者 → 测试 → 生成物按原阶段实施。旧事件不能根据旧11字符串猜目标、ID或修订；转换需要可信事实映射，保留原字节/hash/版本和转换记录，无法映射则拒绝。影响G00/G01候选输入、G02类型/Schema、G04场景、事件/审计引用消费者及依赖后继；本轮不刷新这些任务的旧证据。

当前G00原记录虽写历史passed，现行runner `previous_gate_record_problems('G00', record)`仍拒绝5项输入漂移；旧冻结12项中4项漂移，原日志及依赖校验没有被绕过。[只读旧冻结/G00核验](../../../artifacts/handoffs/N01-R02/codex/legacy-freeze-g00-state.json)。不以本轮设计通过推断G00恢复。

设计脚本使用UUID5合成身份及固定事实快照。继承适配器的CalendarDTO重叠、单独RegionRef空节点、OnArc时序、全场景FK/日历完整性覆盖限制仍在；CargoType夹具明确未验证，不能把场景示例称为完整业务合法Schema。新增区域谓词仅保证本轮事件映射所需约束。数据库、真实parser/handler/worker、OR-Tools、SimPy、模型、浏览器验收均NOT_RUN。[示例范围说明](../../../artifacts/handoffs/N01-R02/codex/examples/subtask-note.md)。没有新增独立demo。

下一执行者：**独立 Codex N02-R02**，复算此新候选、5项差异、保护文件与日志，裁定唯一修复；通过后才归档原冻结/G00/原日志、更新真实审查事实与哈希，实跑 `--self-test --record-g00`，再以现行runner核验新G00输入/日志/依赖。G00有效才可启动N03，G01有效才进入P02。

交付：[机器证据](../../../artifacts/handoffs/N01-R02/codex/evidence.json)。完成封存核验后停写，不自行执行下一轮。
