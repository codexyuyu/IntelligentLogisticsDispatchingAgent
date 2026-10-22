# 领域实体目录 · Architecture Contract 2.0.0

本文是后续 P02/P03 的设计输入，尚未生成数据库或业务模型。`packages/domain` 的纯模型和枚举是实施后的领域唯一来源；`packages/contracts` 只负责边界验证、序列化与映射。ORM 是存储映射，前端类型是 OpenAPI 派生产物；不得各自重写业务枚举。

## 每个实体共同继承的字段与规则

下表**每一行**都具有：`id: UUID`（表名对应 ID 类型）、`status: 该行指定 Enum`、`created_at: UTC datetime`、`updated_at: UTC datetime`、`row_version: int >= 0`、`schema_version: str`、`created_by: ActorId`。首次创建两时间相等；业务变更由应用服务递增 row_version 和 updated_at。审计/快照/结果等不可变内容 created_at=updated_at，后续状态采用追加生命周期事件形成投影，不原地改内容。所有 ID 使用 UUID4；合成数据用带 namespace 的 UUID5，禁止把短示例 ID 直接当生产 UUID。

时间统一 `timestamptz`，领域时间须带时区。求解与仿真使用相对 `epoch_utc` 的整数秒。距离米、重量克、容积立方厘米、金额人民币分、温度十分之一摄氏度。浮点经外层显示转换，不进入求解整数约束；订单数量按整数最小包装单位。单价用 `rate_cents_per_km` 整数，每段费用 `(distance_m*rate+500)//1000`。不得默默将千克当克或分钟当秒。

服务开始允许窗 `[earliest_s, latest_s]` 两端可取；任务占用 `[start_s,end_s)`，故 `[0,10)` 与 `[10,20)` 不冲突。`hard_latest_start_s` 与 `soft_due_at_s` 是不同字段；软延误=`max(0, completion_s-soft_due_at_s)`，不能越过硬开始窗。horizon 默认86400秒，上限604800秒，输入越界拒绝；运行配置可通过契约变更调整。

## 32 个必需实体

字段列表是最低必需字段；所有 `*_id` 具有 FK 或快照内解析验证，`?` 表示显式可空，未标问号的字段必填。tuple/嵌套模型有专用 Schema，不代表任意 JSON。

| 实体 / 聚合所有者 | 状态与生命周期 | 关键字段（含类型） | 关联与关键不变量 |
| --- | --- | --- | --- |
| Order / Orders | draft→accepted→scheduled→in_execution→delivered；draft/accepted/scheduled可cancelled；执行中取消进cancel_requested→cancelled_after_return | external_ref:str; pickup_node_id:UUID; delivery_node_id:UUID; cargo_ids:tuple[UUID]; pickup_window:TimeWindow; delivery_window:TimeWindow; service_s:int; soft_due_at_s:int?; must_serve:bool; priority:int | 1:N Cargo、TransportTask；数量不能拆给多辆车；取消不抹除已发生库存 |
| Cargo / Orders | registered→stored→loaded→in_transit→delivered；任一未终结态可quarantined；返仓returned | order_id:UUID; cargo_type:CargoType; quantity_units:int; weight_g:int; volume_cm3:int; min_temp_decic:int; max_temp_decic:int; max_exposure_s:int; batch_ref:str | Order必需；数量/重量/容积正数；min<=max；位置从执行事实推导 |
| Vehicle / Fleet | available↔reserved→in_service→available；任意非retired可unavailable；最终retired | code:str; capacity_weight_g:int; capacity_volume_cm3:int; setpoint_decic:int; allowed_cargo_types:tuple[CargoType]; start_node_id:UUID; end_node_id:UUID; calendar:ResourceCalendar; driver_id:UUID?; fixed_cost_cents:int; rate_cents_per_km:int | N:1 Driver（时间上不可双派）；固定单车厢，能力非零；已停用不参与求解 |
| Driver / Fleet | active↔unavailable→retired | code:str; qualifications:tuple[Qualification]; shift:TimeWindow; max_drive_s:int; max_work_s:int | 车辆任务带明确driver_id；一个时段不能执行两车任务；MVP不声称符合所有地区复杂工时法规 |
| Warehouse / Warehouse | active↔unavailable→retired | code:str; name:str; node_id:UUID; timezone:str; calendar:ResourceCalendar | 1:N Zone、Dock、Worker、Equipment；node映射矩阵节点 |
| WarehouseZone / Warehouse | active↔unavailable→retired | warehouse_id:UUID; code:str; setpoint_decic:int; capacity_weight_g:int; capacity_volume_cm3:int; allowed_cargo_types:tuple[CargoType] | 1:N StorageLocation；重叠存储全部货物均满足固定温控点 |
| StorageLocation / Warehouse | available↔reserved↔occupied；可unavailable→retired | zone_id:UUID; code:str; capacity_weight_g:int; capacity_volume_cm3:int; calendar:ResourceCalendar | 库存占用受时段/初始库存约束，不能单靠当前status判断未来容量 |
| Dock / Warehouse | available↔busy；可unavailable→retired | warehouse_id:UUID; code:str; supported_operations:tuple[OperationKind]; allowed_zone_ids:tuple[UUID]; calendar:ResourceCalendar | 同一时刻单任务；需要切换时显式SetupOperation |
| Worker / Warehouse | available↔busy；可unavailable→retired | warehouse_id:UUID; skills:tuple[Skill]; allowed_zone_ids:tuple[UUID]; calendar:ResourceCalendar; pool_id:UUID? | 具名人员独占；同质池按人数累计，不混用两种计数重复算能力 |
| Equipment / Warehouse | available↔busy；可failed→repairing→available；可retired | warehouse_id:UUID; kind:EquipmentKind; quantity_capacity:int; allowed_zone_ids:tuple[UUID]; calendar:ResourceCalendar | 至少 sorting、handling；故障影响当前和未来占用 |
| TransportTask / Planning | pending→ready→running→completed；可cancelled/interrupted/failed | order_id:UUID; leg_no:int; pickup_node_id:UUID; delivery_node_id:UUID; cargo_ids:tuple[UUID]; predecessor_ids:tuple[UUID]; service_s:int | 稳定task_id贯穿版本；提货送货同车且有序；取消生成返仓腿而非货物消失 |
| WarehouseTask / Planning | pending→ready→running→completed；可cancelled/interrupted/failed | order_id:UUID?; warehouse_id:UUID; kind:OperationKind; duration_s:int; window:TimeWindow; predecessor_ids:tuple[UUID]; requirements:tuple[ResourceRequirement]; setup_class:str | kind=receive/dispatch/sort/load/unload/setup；主任务依赖DAG；setup为派生显式任务 |
| Route / Planning | candidate→validated→published；生命周期可superseded | version_id:UUID; vehicle_id:UUID; driver_id:UUID; start_node_id:UUID; end_node_id:UUID; total_distance_m:int; cost:CostBreakdown; matrix_ref:MatrixRef | 1:N RouteStop；不在记录里藏任意路线dict；计划内容不可变 |
| RouteStop / Planning | planned→reached→servicing→completed；可cancelled（仅未执行） | route_id:UUID; sequence:int; node_id:UUID; task_ids:tuple[UUID]; arrival_s:int; service_start_s:int; departure_s:int; load_before:Load; load_after:Load | unique(route_id,sequence)；arrival<=start<=departure；首末点明示 |
| Schedule / Planning | draft→active→completed；active可suspended→active；可archived | name:str; scope:PlanningScope; active_version_id:UUID?; epoch_utc:datetime; horizon_s:int | 1:N ScheduleVersion；活动指针CAS，不能就地替换版本内容 |
| ScheduleTask / Planning | planned→dispatched→running→completed；可cancelled/interrupted | version_id:UUID; task_id:UUID; task_kind:TaskKind; assigned_resource_ids:tuple[UUID]; planned_start_s:int; planned_end_s:int; sequence:int? | PK可用id，unique(version_id,task_id)；task_kind解析唯一基础任务；执行状态为事实投影 |
| ScheduleVersion / Planning | candidate→validated→committed→superseded；candidate可rejected/expired | schedule_id:UUID; version_no:int; parent_version_id:UUID?; snapshot_id:UUID; content_hash:str; reason:VersionReason; event_id:UUID?; task_refs:tuple[UUID]; validation_report_ref:UUID | unique(schedule,version_no)；内容永不覆盖；parent同schedule且较早；状态变化以追加审计投影 |
| Constraint / Planning | draft→active→deprecated | code:ConstraintCode; rule_version:str; severity:hard/soft; scope:ConstraintScope; parameters:ConstraintParameters; source:ConstraintSource | parameters按code判别联合；必需硬规则未知则拒绝提交 |
| OptimizationRequest / Optimization | accepted→queued→running→completed；可cancelled/failed | kind:transport/warehouse/joint; snapshot_id:UUID; policy:ObjectivePolicy; budget:SolveBudget; request_hash:str; job_id:UUID | 1:1 Job，可1:N重试Attempt；请求内容不可变 |
| OptimizationResult / Optimization | recorded（不可变），可追加invalidated投影 | request_id:UUID; solve_status:SolveStatus; engine_status:str; candidate_id:UUID?; validation:ValidationReport?; objective:ObjectiveBreakdown?; engine_metadata:EngineMetadata | 无incumbent时candidate=null；FEASIBLE不等于OPTIMAL；保留原引擎状态 |
| Simulation / Simulation | created→running↔paused→completed；可cancelled/failed | scenario_ref:ScenarioRef; schedule_version_id:UUID; parent_simulation_id:UUID?; seed:int; current_time_s:int; control_seq:int; source:simulation | 1:N Snapshot/Event；与正式执行域隔离 |
| SimulationSnapshot / Simulation | recorded（不可变） | simulation_id:UUID; time_s:int; state:TwinState; pending_events:tuple[PendingEvent]; rng_states:tuple[RngState]; last_event_seq:int; snapshot_hash:str | 在同时间事件批次处理完后保存；不用pickle活跃generator |
| Event / Events | received→validated→applied；可duplicate/rejected/quarantined | source:str; source_event_id:str; kind:EventKind; occurred_at_utc:datetime; received_at_utc:datetime; simulation_id:UUID?; sequence:int; payload:EventPayload | unique(source,source_event_id,scope)；payload判别Schema；发生时间不等于接收时间 |
| ExceptionEvent / Events | detected→analyzed→proposed→resolved；可manual_required/unresolved | event_id:UUID; severity:ExceptionSeverity; affected_entity_refs:tuple[EntityRef]; impact_report_ref:UUID?; decision_record_id:UUID? | 1:1 Event；10类payload明确定义；解不了不能标resolved |
| RescheduleRequest / Rescheduling | accepted→queued→running→completed；可cancelled/failed | base_version_id:UUID; exception_event_ids:tuple[UUID]; execution_snapshot_id:UUID; boundary:RescheduleBoundary; policy:ReschedulePolicy; job_id:UUID | 引用事件时刻事实，不读移动目标；本请求不覆盖基版本 |
| RescheduleResult / Rescheduling | recorded（不可变） | request_id:UUID; solve_status:SolveStatus; candidates:tuple[CandidateEvaluation]; selected_candidate_id:UUID?; diff:ScheduleDiff?; rounds:tuple[SearchRound]; decision_record_id:UUID | 无候选时selected=null；记录扩大范围/失败轮次 |
| AgentRun / Agents | received→planning→executing→explaining→await_confirmation→completed；可waiting_input/failed/cancelled | actor_id:UUID; conversation_id:UUID; role:AgentRole; parent_run_id:UUID?; deadline_utc:datetime; budget:AgentBudget; context_ref:UUID | 1:N ToolCall；所有角色共享父预算；不是持续无限对话 |
| ToolCall / Agents | requested→authorized→running→succeeded；可denied/failed/cancelled | run_id:UUID; tool_name:ToolName; call_index:int; args:ToolArguments; args_hash:str; result:ToolResult?; duration_ms:int?; idempotency_key:str? | tool_name判别args；保留trace；敏感字段引用或脱敏，禁止日志明文密钥 |
| DecisionRecord / Audit | recorded（不可变），可追加new decision关联 | event_id:UUID?; agent_run_id:UUID?; base_version_id:UUID?; candidate_refs:tuple[UUID]; selected_ref:UUID?; explanation:EvidenceExplanation; action:DecisionAction; actor_id:UUID | 建议/确认/拒绝分记录；事实和预测明确标识；关联前后版本 |
| Experiment / Evaluation | draft→queued→running→completed；可failed/cancelled | spec:ExperimentSpec; dataset_ref:ScenarioRef; policy_refs:tuple[str]; seeds:tuple[int]; definition_version:str; environment:EnvironmentFingerprint | 相同预算/场景配对比较；1:N ExperimentResult |
| Metric / Evaluation | draft→active→deprecated | code:MetricCode; definition_version:str; unit:MetricUnit; numerator:MetricFormula; denominator:MetricFormula?; zero_policy:null_with_reason; source:MetricSource | 定义实体而非把每次值塞入定义；值在MetricValue/ExperimentResult |
| ExperimentResult / Evaluation | recorded（不可变） | experiment_id:UUID; policy_id:str; seed:int; run_status:RunStatus; metric_values:tuple[MetricValue]; artifact_refs:tuple[ArtifactRef]; elapsed_ms:int; error:ErrorEnvelope? | unique(experiment,policy,seed,attempt)；失败保留记录且不从分母消失 |

## 必需辅助实体（不替代上表）

同样继承公共字段。`PlanningSnapshot(recorded)` 保存scope、对象修订向量、矩阵版本、库存和资源日历、content_hash；`Job(queued→running→completed/failed/cancelled)` 保存kind、typed请求引用、lease_owner/epoch/expires_at、attempt、deadline、result_ref；`JobAttempt(recorded)` 保存开始结束与原始错误；`Idempotency(active→expired)` 保存actor/scope/key/request_hash/receipt；`Reservation(held→committed→released/expired)` 保存资源/货物、区间、quantity、版本与有效期。

`InventoryLedger(recorded)` 保存cargo/location/quantity_delta/cause_event_id/version_ref，按事务追加；`Outbox(pending→delivering→delivered/dead_letter)` 保存topic、typed payload、seq、retry_after、attempt；`AuditEntry(recorded)` 保存actor、action、entity_ref、trace_id、前后内容hash；`LifecycleEvent(recorded)` 保存entity_ref、from/to、cause、timestamp；`ExecutionSnapshot(recorded)` 保存事件时刻实物/资源状态；`ConfirmationToken(active→consumed/expired)` 只存token hash和绑定信息。所有未来新增实体也必须满足同样ID/状态/生命周期/时间规范。

## 数据库约束与索引

外键删除默认RESTRICT；订单/车辆/仓库编码唯一；所有非负字段CHECK；task依赖环在领域检查。提交时固定顺序锁相关资源与Schedule行，在同一事务内复核库存与完整时段占用、active_version及revision向量，再追加版本/预留/审计/outbox。针对互斥资源可增tstzrange exclusion，资源池仍需父资源行锁后累计校验，不能以排他区间代替容量约束。

优先索引：`orders(status,id)`、`schedule_versions(schedule_id,version_no)`、`schedule_tasks(version_id,task_id)`、`reservations(resource_id,start_s,end_s,status)`、`jobs(status,available_at,lease_expires_at)`、`events(scope,sequence)`、`outbox(status,sequence)`、`tool_calls(run_id,call_index)`、`audit(trace_id,created_at)`。快照JSONB只存Schema定义的typed内容；关系和并发键不得全藏入JSONB。

库存和占用随版本替换只释放未来可撤销预留；已执行事实和库存账不删除。取消在途订单的货物仍保持位置与数量，直至返仓或明确处置完成。


## N01-R01 本轮关联闭包决定

这是本轮新增设计决定：Job/JobAttempt完整共同字段及专属字段、状态不变量、ScenarioRef、ActorContext和资源包装按[DATA完整决定](DATA_CONTRACTS.md#n01-r01-本轮完整契约决定)。Job请求保存P02-04 JobCommand与不可变RequestRef，不导入未来能力DTO；纯错误保存JobFailure并在边界映射Envelope。CalendarInterval/ResourceCalendar先由P02-01 primitives定义，包含必需epoch_utc/version/intervals，P02-02引用时已成立。32实体数量不变；Resource是既有zone/location/dock/worker/equipment实体的kind/value包装，不新增第33实体。ResourceBundle仅引用当前具体实体，其calendar绑定是相同日历的只读投影。OrderCreate内嵌CargoCreate按同事务填双方FK，公共ID/状态/时间/row_version/created_by由服务产生，不能客户端自报。

本轮2.0.0破坏迁移不改变既有单位、半开占用、状态转移及计划不可变规则；新增公共引用及scope是明确决定，未实现或签收。原1.0.0及所有旧证据保持历史原字节，实际迁移及Schema验收由原任务经独立复核后执行。
