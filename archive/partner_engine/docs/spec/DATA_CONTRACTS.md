> 导入规格说明：本文件中的 DSH UUID、规划任务与历史契约仅作设计来源；现行运行接口以 [共享契约](../../contracts/README.md) 和 backend/app/contracts 为准。未合入引用不具有可执行契约效力。

# 共享数据与接口契约 · 2.0.0

这是架构冻结输入；类型实施任务见TASK_MANIFEST。所有跨模块输入输出均具名且有版本，禁止任意dict/Any穿越边界。列表字段为tuple或显式list[T]，可选字段用T|None且有缺失语义；Pydantic边界`extra=forbid`，纯domain不依赖Pydantic。字段实现后由Python导出JSON Schema和OpenAPI，本文随破坏变更修订，禁止产生另一个手写标准。

## 公共类型与状态

`EntityRef(kind: EntityKind, id: UUID, revision: int?)`；`ArtifactRef(id: UUID, media_type: str, sha256: str, relative_path: SafeArtifactPath)`；`ResourceRevision(entity_ref, row_version)`；`TimeWindow(earliest_s:int, latest_s:int)`；`Load(weight_g:int, volume_cm3:int)`；`ResourceRequirement(resource_kind, eligible_ids:tuple[UUID], units:int)`；`CalendarInterval(start_s:int,end_s:int,available_units:int)`；`ResourceCalendar(epoch_utc:UTC datetime, intervals:tuple[CalendarInterval], version:int)`（本轮2.0.0新增必需epoch）；`ConstraintParameters` 按ConstraintCode判别，不接受自由key-value。

`SolveStatus = OPTIMAL | FEASIBLE | INFEASIBLE | TIMEOUT | UNKNOWN | INVALID_INPUT | ERROR | CANCELLED`。TIMEOUT可以有经验证incumbent，具体以candidate与validation判断；无incumbent不能报告可行。`feasibility = VALID | INVALID | UNKNOWN`。`JobStatus = queued | running | completed | failed | cancelled`：completed表示工作已执行并产出typed结果，优化可能INFEASIBLE/TIMEOUT；worker自身崩溃/代码错误重试耗尽才failed。`MetricSource = planned | simulation | actual`。`ActorRole = viewer | operator`。

`ErrorEnvelope(schema_version, code:ErrorCode, message:str, trace_id:UUID, retryable:bool, details:tuple[ErrorDetail])`。`ErrorDetail`为FieldError(field_path,rule,expected:str,actual:str)、ConflictDetail(entity_ref,expected_revision,actual_revision)、UnsupportedDetail(capability)判别联合；不要输出完整原输入或密钥。

错误表：INVALID_INPUT/INVALID_TRANSITION/DEPENDENCY_CYCLE→422；UNAUTHENTICATED→401；FORBIDDEN/TOOL_FORBIDDEN→403；NOT_FOUND→404；STALE_SNAPSHOT/RESOURCE_CONFLICT/IDEMPOTENCY_CONFLICT/CONFIRMATION_EXPIRED→409；REQUEST_TOO_LARGE→413；RATE_LIMITED→429；PROVIDER_UNAVAILABLE/DEPENDENCY_UNAVAILABLE→503；INTERNAL_ERROR→500。求解无解/超时是已完成作业的result状态，不伪装HTTP500。MANUAL_REQUIRED、NO_FEASIBLE_CANDIDATE是业务结果原因；未实现能力在开发期间HTTP501，禁止进入对应Gate。

## 关键 Schema（未列的实体字段继承 DOMAIN_CATALOG）

| Schema | 必需字段与边界语义 | 实施归属 |
| --- | --- | --- |
| PlanningScope | order_ids:tuple[UUID]; warehouse_ids:tuple[UUID]; vehicle_ids:tuple[UUID]; epoch_utc:datetime; horizon_s:int | P02-03 |
| PlanningSnapshot | id; scope; orders:tuple[Order]; cargo:tuple[Cargo]; vehicles:tuple[Vehicle]; drivers:tuple[Driver]; resources:ResourceBundle; inventory:tuple[InventoryEntry]; revisions:tuple[ResourceRevision]; matrices:tuple[TravelMatrix]; hash:str | P02-03/P03-03 |
| SolveBudget | wall_time_ms:int(1..60000); deadline_utc:datetime; max_candidates:int(1..10); seed:int; worker_count:int(默认1); deterministic_test_mode:bool | P02-03 |
| ObjectivePolicy | version:str; optional_unserved_penalty_cents:int; soft_late_cents_per_s:int; makespan_cents_per_s:int; disturbance_weights:DisturbanceWeights；均非负且int64上界检查 | P02-03 |
| EngineMetadata | name; version; configuration_hash; seed; workers; input_hash; solve_ms; build_ms; engine_status; incumbent_exists; best_bound:int?; optimality_gap:float? | P02-03 |
| ValidationReport | id; candidate_hash; snapshot_hash; rules_version; valid:bool; required_codes:tuple[ConstraintCode]; checked_codes:tuple[ConstraintCode]; unsupported_codes; violations:tuple[Violation]; validated_at | 纯类型P02-03；边界/注册P10-01 |
| Violation | code; severity; entity_refs; field_path; actual:str; expected:str; message:str | P02-03 |
| CandidatePlan | id; schedule_id; base_version_id?; snapshot_id; snapshot_hash; epoch_utc; horizon_s; transport_plan:TransportPlan; warehouse_plan:WarehousePlan; task_assignments:tuple[ScheduleTask]; objective; content_hash; solver_evidence_refs:tuple[UUID] | P02-03 |
| SolverEvidence | id; engine_name:routing/cp_sat; engine_version; input_hash; assignment_hash; configuration_hash; solve_status; trusted_job_id:UUID?；纯内核结果此字段可空，可信worker存储时绑定实际job，正式提交必须非空；Agent自报无效 | P02-03；P07/P09/P16填充 |
| CostBreakdown | distance_cents; fixed_vehicle_cents; service_cents; overtime_cents; setup_cents; total_cents；total仅这五项实际成本之和，不含任何优化罚分 | P02-03 |
| ObjectiveBreakdown | business_cost_cents; optional_unserved_penalty; soft_late_penalty; disturbance_penalty; makespan_penalty; objective_total；业务成本与罚分各计一次，不将objective_total称运输总成本 | P02-03 |
| TransportRequestDTO | schema_version; scope; order_ids; vehicle_ids; matrix_ref; constraints:tuple[ConstraintDTO]; budget; objective_policy | P06-01 |
| TransportProblem | snapshot; nodes:tuple[RoutingNode]; vehicles:tuple[VehicleState]; pickup_delivery_pairs; matrix; constraints; policy | P06-01 |
| RoutingNode | id; kind:depot/pickup/delivery/virtual_start; order_id?; location_id; service_s; hard_window; soft_due_at_s?; load_delta:SignedLoad | P06-01 |
| VehicleState | vehicle_id; driver_id; start_node_id; end_node_id; start_load; capacity; setpoint_decic; available_window; max_drive_s; allowed_cargo_types | P06-01 |
| TransportSolution | status; engine_metadata; candidate:TransportPlan?; optional_unserved_order_ids; objective?; validation:ValidationReport?; diagnostics:tuple[Diagnostic]; solver_evidence:tuple[SolverEvidence] | P06-01 |
| MatrixQuery / TravelMatrix | query含ordered_node_ids/profile/time_bucket/expected_version；matrix含id/version/node_ids/distance_m:tuple[tuple[int or null]]/travel_s同形/source/observed_at/hash；None为不可达，成对一致 | 纯矩阵值P02-03；Query/DTO/Provider P06-02 |
| WarehouseRequestDTO / WarehouseProblem | scope; snapshot; tasks:tuple[WarehouseTask]; calendars; initial_inventory; storage_intervals; setup_policy; handoffs; objective; budget | P08-01/02 |
| WarehouseSolution | status; assignments:tuple[OperationAssignment]?; storage_allocations; setup_operations; objective?; validation?; engine_metadata; diagnostics; solver_evidence:tuple[SolverEvidence] | P08-01 |
| HandoffConstraint | order_id; predecessor_task_id; successor_task_id; location_id; min_transfer_s; cargo_units; kind:load_before_depart/unload_after_arrive/storage_conservation | P08-02 |
| SetupPolicy | version; transitions:tuple[SetupTransition(resource_kind,from_class,to_class,duration_s,requirements,cost_cents)] | P08-01 |
| SimulationRequest | schema_version; scenario_ref; schedule_version_id; validated_plan; seed; until_s; stochastic_policy:StochasticPolicy; source=simulation | P11-01 |
| TwinState | time_s; orders:tuple[OrderExecution]; vehicles:tuple[VehicleExecution]; warehouses:tuple[WarehouseExecution]; inventory; resource_usage; last_event_seq | 纯值P02-04；仿真映射P11-01 |
| PendingEvent / RngState | event_id,time_s,priority,insertion_seq,payload:ExecutionEventPayload；rng含stream_name、algorithm_version、typed integer state、draw_count | 纯值P02-04；仿真映射P11-01 |
| SimulationSnapshot | 见实体目录，完整TwinState+pending_events+rng_states+source_plan_hash+schema_version | P11-01 |
| SimulationResult / SimulationView | simulation_id; status; time_s; snapshot_ref; event_cursor; execution_summary; seed; source；Result另含final_state_hash、artifacts | P11-01/P16-04 |
| SimulationControl | action:pause/resume/step; control_seq:int; expected_revision:int; advance_to_s:int? | P16-04 |
| EventEnvelope | schema_version; source; source_event_id; kind; occurred_at_utc; simulation_id?; payload:EventPayload; expected_revision? | P13-01 |
| ImpactReport | event_ids; base_version_id; execution_snapshot_id; affected_tasks; affected_orders; affected_resources; reason_paths:tuple[ImpactPath]; boundary_refs | P14-01 |
| RescheduleBoundary | event_time_s; frozen_tasks; interrupted_tasks; virtual_starts; residual_loads; resource_blocks; mutable_task_ids; immutable_hash | P14-02 |
| AdjustmentSpec | id; strategy:reassign/defer/alternate_resource/rescue/return; changed_constraint_refs; rescue_tasks; assumptions:tuple[VerifiedAssumption] | P15-01 |
| RescheduleProblem / RescheduleRequestDTO | base_version; execution_snapshot; events; impact; boundary; candidate_policies; budget; objective_policy | P14-01/P15-02 |
| RescheduleSolution | status; rounds:tuple[SearchRound]; candidates:tuple[CandidateEvaluation]; selected_candidate_id?; comparison:ScheduleDiff?; manual_requirements | P15-02 |
| ScheduleDiff | base_version_id; candidate_id; changed_tasks:tuple[TaskChange]; added_cost:int; delay_difference:int; resource_changes:tuple[ResourceChange]; affected_orders:tuple[UUID]; constraint_results:ValidationComparison; disturbance:DisturbanceScore | P15-04 |
| JointPlanningRequest / JointPlanningResult | scope,budget,policy；结果含status/rounds/offers/candidate/validation/engine_metadata，预算贯穿所有子问题 | P16-02 |
| WarehouseWindowOffer | id; snapshot_hash; warehouse_id; order_ids; ready_at_s; receiving_windows; resource_summary; expires_at；不含正式预留 | P16-02 |
| CommitCommand | schedule_id; candidate_id; candidate_hash; expected_active_version_id?; snapshot_hash; idempotency_key; confirmation_token? | P02-03/P16-03 |
| CommitReceipt | schedule_id; version_id; version_no; parent_version_id?; content_hash; audit_id; trace_id; committed_at | P02-03 |
| JobCommand / JobRequest / JobRef | 五类早期具名引用payload，完整形状见本轮决定表；Ref含schema_version/job_id/status/status_url/result_url/trace_id | 纯Command及Request映射P02-04；JobRef及行为P05-03 |
| ToolSpec / ToolCallRequest | name、description、args_schema、required_role、effect:read/propose/commit；call含run_id、call_id、name、arguments:ToolArguments、deadline、idempotency_key、expected_revision | P17-01 |
| ToolResult | call_id; status:success/error/pending; data:ToolData判别联合; error:ErrorEnvelope?; trace_id; audit_ref | P17-01 |
| LLMRequest / LLMResponse | typed Messages/ToolSpecs/response_schema/budget；响应TextPart/ToolProposal联合+usage+provider_request_id；没有ScheduleVersion写入字段 | P18-01 |
| IntentDraft | intent; entity_refs; constraints:tuple[ConstraintProposal]; missing_fields; questions; evidence:tuple[SourceSpan]; ready:bool | P19-01 |
| AgentRequest / AgentOutcome | actor/run/conversation/message/deadline/budget；Outcome status、candidate_refs、questions、explanation、decision_ref；不承载自由生成路线 | P19-02 |
| EvidenceExplanation | summary; facts:tuple[FactRef]; statements:tuple[EvidenceStatement(text,fact_ids,kind:fact/prediction/recommendation)]; generator:model/template | P20-02 |
| ConfirmationToken | opaque随机token对外，仅hash入库；绑定actor/run/candidate_hash/expected_revision/expires_at；有效期默认300秒，一次消费可幂等重放原receipt | P23-02 |
| RealtimeEnvelope | schema_version; seq:int; event_id; topic:Topic; entity_ref; revision; payload:RealtimePayload联合；不推敏感全量实体 | P31-01 |
| EvaluationInput / MetricSet | scope_id/source/window/eligible_orders/execution_facts/availability/costs/latency_samples；MetricSet含definition_version、values、sample_count、coverage、missing_reasons | P32-01 |
| ExperimentSpec | scenario_ref; policy_ids; paired_seeds; repetitions>=10; equal_budget; metric_version; stop_policy; environment_fingerprint | 纯值P02-04；实验行为P33-01 |

所有`Protocol`使用本表的纯domain类型或明确view模型；HTTP/Tool边界使用对应DTO，应用层负责映射。`ServiceBundle`是具名服务字段的组合结构，不能`dict[str,object]`服务定位器。`ToolArguments`按ToolName判别到对应服务请求DTO。未列小型UI Props必须从生成客户端类型组合，不能新定义业务实体。

## EventPayload 十类精确定义

公共 `entity_ref`、`effective_at_s`、`reason` 均必填。vehicle_failure(vehicle_id,location:ExecutionLocation,unavailable_until_s?,cargo_condition:CargoCondition)；transport_delay(transport_task_id,additional_seconds>0)；traffic_disruption(arc_refs,closure:bool,travel_multiplier:Rational?,new_matrix_version)；weather_change(region_ref,profile:WeatherProfile,travel_multiplier:Rational,new_matrix_version)；cargo_anomaly(cargo_id,condition:temperature_excursion/damaged/missing,quantity_units,measured_temp_decic?)；order_cancellation(order_id,disposition_policy:ReturnPolicy)；demand_increase(order_id,delta_quantity>0,delta_weight_g>0,delta_volume_cm3>0)；demand_decrease(order_id,delta_quantity>0,delta_weight_g>0,delta_volume_cm3>0)；equipment_failure(equipment_id,unavailable_until_s?,remaining_capacity_units>=0)；warehouse_resource_unavailable(resource_ref,unavailable_window,remaining_capacity_units>=0)。

增/减是独立kind，delta均正；应用时总量不得负，已执行数量不能减少。天气/交通产生新矩阵，保留来源和有理倍率；未发生的路段受新数据影响，在途路段以实际位置和剩余段单独重建，不能改写历史。迟到事件标记quarantined/reprojection_required，待重投影生成新快照后再分析。

## 冻结的服务 / Protocol 方法

阶段间类型依赖规则：P02-03的`domain/planning.py`完整定义Route/RouteStop、TransportPlan、WarehousePlan、CandidatePlan、SolveBudget和ValidationReport等纯值类型，不能等P06/P08/P10才出现被P03引用的类型。P02-04的`domain/execution.py`定义TwinState、ExecutionEvent、PendingEvent、RngState；`domain/runtime.py`定义AgentBudget、ExperimentSpec等运行实体所需纯值类型。P11/P17/P33等后续阶段只新增该能力的请求映射、Problem组装、Protocol与实现，引用早期实体和纯值类型，不再创建同名第二份定义。运行实体DTO在`contracts/runtime.py`，仿真请求/响应DTO在`contracts/simulation.py`，职责不同。Schema所需类型必须真正可实例化，不能用Any、空类或TODO代替。

`ScenarioSpec`的纯数据形状也在P02-04定义，P04负责生成；`ScenarioEngine`的加载实现可在P12-04装配。P02的Schema导出仅依赖完整contracts类型；P05才将已实现路由OpenAPI加入同一导出器，不能让P02导入尚不存在的FastAPI应用。

2026-10-03 N01-R01 本轮设计决定（计划1.0.3，数据契约2.0.0）：ScenarioSpec/Ref/Bundle、ActorContext、JobCommand及其具名引用闭包在P02-04 runtime唯一定义；JobKind/JobStatus/JobOptimizationMode在P02-01 states唯一定义，CalendarInterval/ResourceCalendar在P02-01 primitives唯一定义。P02-04 execution先定义场景引用的事件纯值，runtime只单向引用。P03只持久化；P04生成/导入；P05仅消费完整早期类型与实现行为。下面决定替代上轮“字段未决、派发前解决”，但仍须独立N02复核；没有签收G00。

| 接口 | 签名 | 允许副作用 |
| --- | --- | --- |
| TransportSolver | solve(problem:TransportProblem,budget:SolveBudget)->TransportSolution | 无，受限CPU计算 |
| WarehouseScheduler | solve(problem:WarehouseProblem,budget:SolveBudget)->WarehouseSolution | 无 |
| JointPlanningSolver | solve(problem:JointProblem,budget:SolveBudget)->JointCandidateSolution | 无；有限轮次仓运窗口反馈，P15首次实现、P16服务复用 |
| ConstraintValidator | validate(plan:CandidatePlan,snapshot:PlanningSnapshot)->ValidationReport | 无；独立重算 |
| RescheduleSolver | solve(problem:RescheduleProblem,budget:SolveBudget)->RescheduleSolution | 无 |
| TravelMatrixProvider | get_matrix(query:MatrixQuery)->TravelMatrix | adapter可读缓存/已批准数据源；solver回调禁止调用 |
| DigitalTwinEngine | apply(state:TwinState,event:ExecutionEvent)->TwinState | 纯投影 |
| SimulationEngine | run(request:SimulationRequest)->SimulationResult | 仅仿真分支内 |
| EventEngine | ingest(envelope:EventEnvelope)->EventReceipt | 由应用服务事务保存，不直接修改计划 |
| ScenarioEngine | load(ref:ScenarioRef)->ScenarioBundle | 只读 |
| PlanningSnapshotStore | capture(scope:PlanningScope)->PlanningSnapshot | 一致性只读事务 |
| PlanCommitStore | commit(cmd:CommitCommand,report:ValidationReport)->CommitReceipt | 由ScheduleService调用，单事务 |
| ScheduleService | commit(cmd:CommitCommand,actor:ActorContext)->CommitReceipt | 唯一正式计划提交用例 |
| ImpactAnalyzer | analyze(event:ExceptionEvent,snapshot:ExecutionSnapshot,plan:ScheduleVersion)->ImpactReport | 无 |
| ToolExecutor | execute(call:ToolCallRequest,context:ToolContext)->ToolResult | 白名单业务服务 |
| LLMProvider | complete(request:LLMRequest)->LLMResponse | 模型网络访问，仅adapter |
| AgentOrchestrator | run(request:AgentRequest)->AgentOutcome | 工具调用与AgentRun记录 |
| MetricCalculator | compute(input:EvaluationInput)->MetricSet | 无 |
| ExperimentRunner | run(spec:ExperimentSpec)->ExperimentResultBundle | 隔离实验分支与结果留档 |

## 兼容变更

本轮设计目标新契约2.0.0（旧设计1.0.0保留原字节）；已有demo 0.1.0仅迁移输入，不能悄悄改版本文件覆盖旧基线。破坏字段/单位/enum/路径/必需语义升major，新增可选字段升minor，兼容修复升patch。先写`contracts/changes/`说明，再同一集成修改domain→DTO→ports→调用方→测试→导出物；非阻断架构问题写`docs/architecture/issues/`继续本任务，不顺手重构。方案hash规范排除创建时间、生命周期投影与耗时，只包含稳定业务内容；包含schema/rules/matrix版本，采用UTF-8、排序键、整数和明确null。

规范化方案hash另排除随机生成的candidate/version/route记录ID和solver_evidence记录ID，但包含稳定订单/任务/车辆/资源ID、路线节点顺序与所有业务时刻/载荷/费用。SolverEvidence.assignment_hash绑定该规范化内容，可信job_id可追溯真实引擎执行。正式提交必须解析非空solver_evidence_refs，核验引擎来源与assignment_hash再独立验证；只有一份valid=true的报告不能把LLM或规则手造候选变成正式计划。缺可信证据返回UNVERIFIED_SOLVER_RESULT/422。纯内核输出待存的typed evidence，由应用worker事务持久化并绑定job，内核不查库。


## N01-R01 本轮完整契约决定

以下新增字段、序列化值、引用和失败语义均为 **N01-R01 本轮设计决定**；原1.0.0并未给出这些完整决定。依据是N02-F01–F04、既有五类作业/状态、早期纯值规则、目录字段与API路径。历史规范机器附表 `N01-R01-contract-decisions.json`（未合入本工程）与下表属于同一待审文档契约；后续实施仍以domain源码唯一定义、DTO映射、实际Schema导出为准。附表不是业务Schema导出。字段全部必填，`?`表示显式可空且仍须提供，`[]`表示有序具名tuple，`=值`表示精确literal；PATCH的“缺省保持”例外仅按API精确投影表。禁止额外字段、空类、Any、自由dict和未来导入。

标量：UUID为标准小写UUID；UTC为秒精度、带UTC时区的datetime，JSON固定`YYYY-MM-DDTHH:MM:SSZ`；int拒绝bool/float并在int64范围；PositiveInt>=1，NonNegativeInt>=0；Seed为0..2^63-1；Horizon为1..604800；Sha256为64小写hex非空；VersionText为精确`major.minor.patch`非负十进制版本；SafeText为1..256字符脱敏说明，不能包含原始请求/凭据/堆栈；str字段仍受其专属规则限制，不能容纳脚本或类型选择器。

### N02-F01：JobKind 与判别映射

JobKind仅有OPTIMIZATION=optimization、SIMULATION=simulation、RESCHEDULE=reschedule、EXPERIMENT=experiment、METRIC=metric。JobStatus保留QUEUED=queued/RUNNING=running/COMPLETED=completed/FAILED=failed/CANCELLED=cancelled。optimization.payload.mode来自同源JobOptimizationMode：TRANSPORT=transport、WAREHOUSE=warehouse、JOINT=joint。顶层kind、payload.family、request_ref.family三者精确相等；optimization必须带mode且与注册元数据相等，其余分支禁止mode。JobStatus.completed表示产出typed业务结果；INFEASIBLE/TIMEOUT可以是completed结果，不能映射worker failed。

### N02-F02：场景身份、内容与期望隔离

ScenarioRef的scenario_id是场景家族ID；dataset_version是>=1的不可变数据修订；schema_version固定2.0.0，generator_version是生成器精确版本。ref与spec的ID/version/schema必须一致。同ID/version只能绑定一个content_hash，冲突409 IDEMPOTENCY_CONFLICT，不覆盖、不自动取latest。生成器额外seed参数必须等于spec.seed。ScenarioSpec唯一持有event_specs，ScenarioInput不再复制事件。ScenarioInput使用已有PlanningSnapshot及具名运输/仓储任务集合，不接受方案、求解证据或期望解；正式消费者接收spec/input的具名内容，ScenarioEngine只返回严格Bundle。

ScenarioSize的14个计数分别等于实际snapshot集合、resources对应集合、任务集合数量；仓储location计数对应resources.locations。scope.epoch/horizon与spec一致；snapshot/revision/matrix/calendar的来源/版本/hash先逐项核验；重复实体/事件ID、悬空FK、任务前驱自环/环、矩阵节点缺失、事件超horizon拒绝。ScenarioEventSpec的EventPayload十分支及直接嵌套纯值在本轮表中闭合：RegionRef明确region_id及非空、唯一node_ids，node_ids均须存在于场景矩阵；区域影响仅作用于两端都在该集合的弧，不能猜测未知区域成员；交通关闭时multiplier=null，开放倍率必须正有理数；cargo_anomaly.condition不得intact；temperature_excursion必填measured_temp_decic，其他condition此字段为null；unavailable_until不得早于effective_at；on_arc满足departed<expected_arrival、0<=numerator<=denominator且from!=to。EventEnvelope仍由P13做边界映射/存储，不能重新定义EventPayload。

content_hash = sha256(UTF8 canonical JSON `{schema_version,scenario_id,dataset_version,spec,input,source}`)，排除ref.content_hash自身；完整spec/input进入hash，包含seed/generator/schema、日历/matrix版本及稳定ID，不含旁文件期望、报告、耗时、新Job ID。编码为UTF8无BOM、键排序、紧凑分隔、拒绝NaN/Infinity和重复key、null明确、UUID小写、UTC秒Z；数组保留规范顺序。所有实体集合按UUID升序，任务前驱ID按UUID升序，矩阵节点顺序和对应矩阵行列保持原业务序，事件按(effective_at_s,既有priority,event_id)固定；fixture共同created_at/updated_at=spec.epoch。snapshot.hash先排除自身hash按相同规范复算；完整Bundle身份再绑定该值。生成/读取必须核验上述规范，不能在读取时改字节后沿用旧hash。raw文件sha256另存，不能混同业务content_hash。

FixtureExpectations是独立测试旁文件，绑定ScenarioRef，只有有限整数/违规/任务集合断言，不含Route/CandidatePlan/SolverEvidence。P04将其写入现有invalid_cases.json的具名expectations集合；正式loader不读此文件，不传入Job内容、不改变场景hash，业务入口extra=forbid拒绝expected/expectations/expected_plan。M1指标手算输入保留TEST_FIXTURES规范，原目录typed场景输入并不构造预制成功方案。对oracle改9000→1，正式输入hash不变；对车辆容量改800000→799999，输入hash必须变。期望不变量非空且同measure/code/taskset标识不重复。

### N02-F03：资源日历与资源包装

CalendarInterval/ResourceCalendar唯一P02-01 primitives，不依赖resources/planning/runtime/DTO/数据库。日历epoch新增必需字段是破坏迁移。区间0<=start<end<=604800，available_units>=0，按start严格升序且无重叠，接续合法；空日历和未覆盖时间表示0可用，不隐式填充。version>=0，初始0；绑定场景验证end<=horizon和units不超过具名资源实际容量。具名独占资源单位上限1，设备池不超过quantity_capacity；不能重复计算worker pool与成员。

P03 capture明确窗口投影：绝对端点=calendar.epoch+整数秒，与scope窗口求交集，空交集舍弃，非空交集重新减scope.epoch；禁止舍入秒或直接跨epoch复用。原日历不可变，ResourceCalendarBinding保存完整source_calendar、其canonical JSON的source_hash和投影calendar；source/version/hash逐项核验，投影calendar等于资源实体在快照中的calendar，version保持源值。由source_calendar与scope可复算每个投影区间，不能只保存裁剪后的值然后宣称原来源可验证；Vehicle日历按同一绑定结构纳入calendars，即使Vehicle实体仍在vehicles集合。CalendarDTO/CalendarIntervalDTO在P02-02 entities仅映射公共字段/约束，根HTTP CalendarDTO另有必需schema_version=2.0.0，不在http自造纯值。PUT需If-Match=resource.row_version且DTO.version=当前calendar.version，成功事务产生calendar.version+1及row_version+1，不能客户端自报新版本；旧记录无可信epoch来源则迁移拒绝。

Resource是zone/location/dock/worker/equipment五个kind/value包装分支，与既有具体实体同构；不是第33个实体。ResourceDTO映射对应既有DTO；Equipment内部kind仍为EquipmentKind，外层kind=equipment，两者不能覆盖。URLkind/ID必须等于包装kind/value.id。Vehicle/Driver/Warehouse保持各自独立DTO。ResourceBundle.calendars绑定覆盖snapshot中Vehicle/Warehouse/StorageLocation/Dock/Worker/Equipment，按resource_id唯一，其calendar与对应实体快照日历逐字段相等；Vehicle实体由vehicles承载；Zone/Driver不凭空增加calendar字段。本轮决定将通用calendar端点kind限定location/dock/worker/equipment，zone仍可PATCH其既有资源字段，但zone calendar返回INVALID_INPUT/422+UnsupportedDetail，不隐式修改仓库日历；Warehouse/Vehicle通过自己的既有DTO映射日历。

### N02-F04：作业引用与生命周期

采用完整早期具名引用方案，避免提前导入P06/P11/P14/P32 DTO。RequestRef固定request_id/version/schema_version/hash/family，RequestMetadata固定scope/owner及optimization_mode；(request_id,version)对应不可变保存原字节。同ID新内容必须新version；旧版本不会解析成latest。请求hash为保存后的规范JSON原字节sha256；读取时按原字节复算，不用重新序列化掩盖篡改。producer先严格解析自己能力的完整schema，规范保存，再注册受控元数据；客户端不能指定schema parser、模块路径或自报已解析。跨作业边界只传具名引用，没有原始dict/Any/pickle。

提交顺序：strict解析JobRequest/三轴判别/版本→认证scope及owner校验→查询精确ref和受控metadata→检查当前注册revision→复算原内容hash→核实该family/mode/schema的真实parser和handler已启用→对应parser严格解析内容→事务保存Job和actor+operation幂等→202。未知字段/kind/schema/mode/内容或hash错误INVALID_INPUT/422；missing ref NOT_FOUND/404；旧revision STALE_SNAPSHOT/409；跨scope或越权FORBIDDEN/403；同幂等key不同完整JobCommand hash IDEMPOTENCY_CONFLICT/409；开发期真实parser/handler未启用501且不入队。校验元数据不等于未来业务schema或solver通过。生产只注册已完成能力。

消费者分工：transport P06-01、warehouse P08-01/02、simulation P11-01/P12、reschedule P14/P15、joint P16-02、experiment P02-04 Spec/P33、metric P32分别提供自己的strict内容解析/真实handler，统一封装已定义JobCommand，不反向创建Job类型。worker执行前重新核验hash、租约epoch、deadline和取消标志。JobResultRef也是早期具名引用，P16及P32/P33结果DTO复用它；不在P05导入未来结果union。

Job.kind/command.kind及deadline两处值必须相同；attempt<=max_attempts。running lease_owner/expires非空，每次领取epoch递增；queued与终态无有效租约；terminal有finished_at且started<=finished。completed result_ref非空/family一致/failure=null；failed result=null/failure非空；cancelled result=null，不伪造成功。queued可原子取消，running先cancel_requested再由当前lease CAS收尾；已终态取消幂等返回原终态，不逆转历史。JobAttempt只在结束后追加recorded，(job_id,attempt_no)唯一，failed/lease_lost有脱敏failure，completed有result_ref，finished>=started。LeaseToken四字段对照数据库当前租约；旧epoch产生WorkLeaseLost且不能改当前Job。retry_scheduled只在attempt<max_attempts且失败可重试时成立，释放租约并排至next_available_at，耗尽则failed。

Deadline是application/jobs内部UTC期限值，Job/Command不依赖它；子任务取父SolveBudget/Agent deadline与本截止的最早值，进程内仅用monotonic计剩余，跨进程UTC、租约以数据库UTC为准。WorkOutcome严格idle/terminal/retry_scheduled/lease_lost四分支；idle只有判别字段，表示没有领到作业，不能当成功结果。JobView不暴露lease/owner/token/db定位/堆栈，JobRef URL由服务端按job_id生成。CancelCommand只带expected_revision/reason，目标来自path、actor来自认证；Agent取消可复用同字段Schema但映射独立run状态机，不能取消Job时顺带改Agent生命周期。

### ActorContext 与早期边界闭包

ActorContext唯一P02-04 runtime：actor_id/role/scope_id，role复用viewer/operator；scope_id为Settings单工作空间UUID，不新增工作空间实体。由P05认证构造，body自报actor/role/scope额外字段拒绝；viewer写或跨scope403，缺凭据401；本run/actor关联限制与AgentRole工具白名单取交集，不能把Coordinator当operator。JobFailure在domain纯值，不依赖contracts.ErrorEnvelope，边界只映射已有错误Envelope；原始脱敏诊断按ArtifactRef留档，不能泄露完整请求/凭据。RESULT_NOT_READY/409与UNVERIFIED_SOLVER_RESULT/422是现有API/提交条款引用的错误，本轮明确纳入ErrorCode唯一映射，UNSUPPORTED仍不是ErrorCode。

ImportReceipt、Settings、Health/Readiness、主数据命令/查询/分页的完整字段与合法来源见历史内部约定 `IMPLEMENTATION_CONVENTIONS.md`（未合入本工程）及历史 HTTP 精确投影 `API_CONTRACT.md`（未合入本工程），不再将其字段留给P03/P04/P05猜测。MasterData仍只是能力统称，不新增实体；MasterDataService是应用服务，不是DTO。后续尚未实施的所有协议/实体不因此被宣称代码可导出，本轮检查只验证受审类型的设计引用与任务/模块闭包，G02实际Schema/业务负例仍必须执行。

### 规范具名定义与字段附表

下表与JSON规范附表逐项一致；existing行仅继承已列具名原契约或下面明确的新HTTP投影，不以空类实施。每个定义任务必须拥有精确承载文件；纯domain不得导入contracts/backend，execution→runtime禁止，runtime→execution单向。完整模块DAG见JSON附表。

| 类型 | 完整字段 / 映射 | 定义任务 / 唯一承载 |
| --- | --- | --- |
| JobKind | OPTIMIZATION=optimization; SIMULATION=simulation; RESCHEDULE=reschedule; EXPERIMENT=experiment; METRIC=metric | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| JobStatus | QUEUED=queued; RUNNING=running; COMPLETED=completed; FAILED=failed; CANCELLED=cancelled | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| JobOptimizationMode | TRANSPORT=transport; WAREHOUSE=warehouse; JOINT=joint | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| ActorRole | VIEWER=viewer; OPERATOR=operator | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| ResourceKind | ZONE=zone; LOCATION=location; DOCK=dock; WORKER=worker; EQUIPMENT=equipment | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| GenerationPolicy | CANONICAL_T1=canonical_t1; CANONICAL_W1=canonical_w1; CANONICAL_J1=canonical_j1; CANONICAL_I1=canonical_i1; CANONICAL_S1=canonical_s1; CANONICAL_M1=canonical_m1; GRID_A=grid_a; GRID_B=grid_b; GRID_C1=grid_c1; GRID_C2=grid_c2; GRID_C3=grid_c3; GRID=grid | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| CargoCondition | INTACT=intact; TEMPERATURE_EXCURSION=temperature_excursion; DAMAGED=damaged; MISSING=missing | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| ReturnPolicy | RETURN_TO_ORIGIN=return_to_origin; QUARANTINE=quarantine | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| WeatherProfile | CLEAR=clear; RAIN=rain; SNOW=snow; STORM=storm | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| CalendarInterval | start_s:NonNegativeInt; end_s:NonNegativeInt; available_units:NonNegativeInt | P02-01 / `packages/domain/src/logistics_domain/primitives.py` |
| ResourceCalendar | epoch_utc:UTC; intervals:CalendarInterval[]; version:NonNegativeInt | P02-01 / `packages/domain/src/logistics_domain/primitives.py` |
| Rational | numerator:PositiveInt; denominator:PositiveInt | P02-01 / `packages/domain/src/logistics_domain/primitives.py` |
| EntityRef | kind:EntityKind; id:UUID; revision:NonNegativeInt? | P02-01 / `packages/domain/src/logistics_domain/primitives.py` |
| ArtifactRef | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#公共类型与状态；HTTP具名投影见下文精确投影表 | P02-01 / `packages/domain/src/logistics_domain/primitives.py` |
| TimeWindow | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#公共类型与状态；HTTP具名投影见下文精确投影表 | P02-01 / `packages/domain/src/logistics_domain/primitives.py` |
| Load | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#公共类型与状态；HTTP具名投影见下文精确投影表 | P02-01 / `packages/domain/src/logistics_domain/primitives.py` |
| ErrorCode | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#公共类型与状态；HTTP具名投影见下文精确投影表 | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| EntityKind | ORDER=order; CARGO=cargo; VEHICLE=vehicle; DRIVER=driver; WAREHOUSE=warehouse; WAREHOUSE_ZONE=zone; STORAGE_LOCATION=location; DOCK=dock; WORKER=worker; EQUIPMENT=equipment; TRANSPORT_TASK=transport_task; WAREHOUSE_TASK=warehouse_task; ROUTE=route; ROUTE_STOP=route_stop; SCHEDULE=schedule; SCHEDULE_TASK=schedule_task; SCHEDULE_VERSION=schedule_version; CONSTRAINT=constraint; OPTIMIZATION_REQUEST=optimization_request; OPTIMIZATION_RESULT=optimization_result; SIMULATION=simulation; SIMULATION_SNAPSHOT=simulation_snapshot; EVENT=event; EXCEPTION_EVENT=exception_event; RESCHEDULE_REQUEST=reschedule_request; RESCHEDULE_RESULT=reschedule_result; AGENT_RUN=agent_run; TOOL_CALL=tool_call; DECISION_RECORD=decision_record; EXPERIMENT=experiment; METRIC=metric; EXPERIMENT_RESULT=experiment_result; PLANNING_SNAPSHOT=planning_snapshot; JOB=job; JOB_ATTEMPT=job_attempt; IDEMPOTENCY=idempotency; RESERVATION=reservation; INVENTORY_LEDGER=inventory_ledger; OUTBOX=outbox; AUDIT_ENTRY=audit_entry; LIFECYCLE_EVENT=lifecycle_event; EXECUTION_SNAPSHOT=execution_snapshot; CONFIRMATION_TOKEN=confirmation_token; TRAVEL_MATRIX=travel_matrix; REGION=region | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| ConstraintCode | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#公共类型与状态；HTTP具名投影见下文精确投影表 | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| Order | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 | P02-02 / `packages/domain/src/logistics_domain/orders.py` |
| OrderDTO | 逐字段/约束映射 Order；不重复领域定义 | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` |
| Cargo | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 | P02-02 / `packages/domain/src/logistics_domain/orders.py` |
| CargoDTO | 逐字段/约束映射 Cargo；不重复领域定义 | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` |
| Vehicle | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 | P02-02 / `packages/domain/src/logistics_domain/resources.py` |
| VehicleDTO | 逐字段/约束映射 Vehicle；不重复领域定义 | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` |
| Driver | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 | P02-02 / `packages/domain/src/logistics_domain/resources.py` |
| DriverDTO | 逐字段/约束映射 Driver；不重复领域定义 | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` |
| Warehouse | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 | P02-02 / `packages/domain/src/logistics_domain/resources.py` |
| WarehouseDTO | 逐字段/约束映射 Warehouse；不重复领域定义 | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` |
| WarehouseZone | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 | P02-02 / `packages/domain/src/logistics_domain/resources.py` |
| ZoneDTO | 逐字段/约束映射 WarehouseZone；不重复领域定义 | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` |
| StorageLocation | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 | P02-02 / `packages/domain/src/logistics_domain/resources.py` |
| StorageLocationDTO | 逐字段/约束映射 StorageLocation；不重复领域定义 | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` |
| Dock | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 | P02-02 / `packages/domain/src/logistics_domain/resources.py` |
| DockDTO | 逐字段/约束映射 Dock；不重复领域定义 | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` |
| Worker | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 | P02-02 / `packages/domain/src/logistics_domain/resources.py` |
| WorkerDTO | 逐字段/约束映射 Worker；不重复领域定义 | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` |
| Equipment | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 | P02-02 / `packages/domain/src/logistics_domain/resources.py` |
| EquipmentDTO | 逐字段/约束映射 Equipment；不重复领域定义 | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` |
| ZoneResource | kind:=zone; value:WarehouseZone | P02-02 / `packages/domain/src/logistics_domain/resources.py` |
| ZoneResourceDTO | kind:=zone; value:ZoneDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` |
| LocationResource | kind:=location; value:StorageLocation | P02-02 / `packages/domain/src/logistics_domain/resources.py` |
| LocationResourceDTO | kind:=location; value:StorageLocationDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` |
| DockResource | kind:=dock; value:Dock | P02-02 / `packages/domain/src/logistics_domain/resources.py` |
| DockResourceDTO | kind:=dock; value:DockDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` |
| WorkerResource | kind:=worker; value:Worker | P02-02 / `packages/domain/src/logistics_domain/resources.py` |
| WorkerResourceDTO | kind:=worker; value:WorkerDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` |
| EquipmentResource | kind:=equipment; value:Equipment | P02-02 / `packages/domain/src/logistics_domain/resources.py` |
| EquipmentResourceDTO | kind:=equipment; value:EquipmentDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` |
| Resource | discriminator=kind; zone→ZoneResource; location→LocationResource; dock→DockResource; worker→WorkerResource; equipment→EquipmentResource | P02-02 / `packages/domain/src/logistics_domain/resources.py` |
| ResourceDTO | discriminator=kind; zone→ZoneResourceDTO; location→LocationResourceDTO; dock→DockResourceDTO; worker→WorkerResourceDTO; equipment→EquipmentResourceDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` |
| CalendarIntervalDTO | 逐字段/约束映射 CalendarInterval；不重复领域定义 | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` |
| CalendarDTO | 逐字段/约束映射 ResourceCalendar；外层必需schema_version=2.0.0；不重复领域定义 | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` |
| ResourceCalendarBinding | resource_id:UUID; source_calendar:ResourceCalendar; source_hash:Sha256; calendar:ResourceCalendar | P02-02 / `packages/domain/src/logistics_domain/resources.py` |
| ResourceBundle | warehouses:Warehouse[]; zones:WarehouseZone[]; locations:StorageLocation[]; docks:Dock[]; workers:Worker[]; equipment:Equipment[]; calendars:ResourceCalendarBinding[] | P02-02 / `packages/domain/src/logistics_domain/resources.py` |
| InventoryEntry | cargo_id:UUID; location_id:UUID; quantity_units:NonNegativeInt; weight_g:NonNegativeInt; volume_cm3:NonNegativeInt | P02-03 / `packages/domain/src/logistics_domain/planning.py` |
| PlanningScope | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#关键-schema未列的实体字段继承-domain_catalog；HTTP具名投影见下文精确投影表 | P02-03 / `packages/domain/src/logistics_domain/planning.py` |
| TransportTask | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 | P02-03 / `packages/domain/src/logistics_domain/planning.py` |
| WarehouseTask | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 | P02-03 / `packages/domain/src/logistics_domain/planning.py` |
| TravelMatrix | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#关键-schema未列的实体字段继承-domain_catalog；HTTP具名投影见下文精确投影表 | P02-03 / `packages/domain/src/logistics_domain/planning.py` |
| ResourceRevision | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#关键-schema未列的实体字段继承-domain_catalog；HTTP具名投影见下文精确投影表 | P02-03 / `packages/domain/src/logistics_domain/planning.py` |
| ObjectivePolicy | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#关键-schema未列的实体字段继承-domain_catalog；HTTP具名投影见下文精确投影表 | P02-03 / `packages/domain/src/logistics_domain/planning.py` |
| SolveBudget | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#关键-schema未列的实体字段继承-domain_catalog；HTTP具名投影见下文精确投影表 | P02-03 / `packages/domain/src/logistics_domain/planning.py` |
| PlanningSnapshot | id:UUID; scope:PlanningScope; orders:Order[]; cargo:Cargo[]; vehicles:Vehicle[]; drivers:Driver[]; resources:ResourceBundle; inventory:InventoryEntry[]; revisions:ResourceRevision[]; matrices:TravelMatrix[]; hash:Sha256 | P02-03 / `packages/domain/src/logistics_domain/planning.py` |
| AtNodeLocation | kind:=at_node; node_id:UUID | P02-04 / `packages/domain/src/logistics_domain/execution.py` |
| OnArcLocation | kind:=on_arc; from_node_id:UUID; to_node_id:UUID; departed_at_s:NonNegativeInt; expected_arrival_s:NonNegativeInt; progress_numerator:NonNegativeInt; progress_denominator:PositiveInt | P02-04 / `packages/domain/src/logistics_domain/execution.py` |
| ExecutionLocation | discriminator=kind; at_node→AtNodeLocation; on_arc→OnArcLocation | P02-04 / `packages/domain/src/logistics_domain/execution.py` |
| ArcRef | from_node_id:UUID; to_node_id:UUID | P02-04 / `packages/domain/src/logistics_domain/execution.py` |
| RegionRef | region_id:UUID; node_ids:UUID[] | P02-04 / `packages/domain/src/logistics_domain/execution.py` |
| VehicleFailurePayload | kind:=vehicle_failure; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; vehicle_id:UUID; location:ExecutionLocation; unavailable_until_s:NonNegativeInt?; cargo_condition:CargoCondition | P02-04 / `packages/domain/src/logistics_domain/execution.py` |
| TransportDelayPayload | kind:=transport_delay; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; transport_task_id:UUID; additional_seconds:PositiveInt | P02-04 / `packages/domain/src/logistics_domain/execution.py` |
| TrafficDisruptionPayload | kind:=traffic_disruption; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; arc_refs:ArcRef[]; closure:bool; travel_multiplier:Rational?; new_matrix_version:PositiveInt | P02-04 / `packages/domain/src/logistics_domain/execution.py` |
| WeatherChangePayload | kind:=weather_change; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; region_ref:RegionRef; profile:WeatherProfile; travel_multiplier:Rational; new_matrix_version:PositiveInt | P02-04 / `packages/domain/src/logistics_domain/execution.py` |
| CargoAnomalyPayload | kind:=cargo_anomaly; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; cargo_id:UUID; condition:CargoCondition; quantity_units:PositiveInt; measured_temp_decic:int? | P02-04 / `packages/domain/src/logistics_domain/execution.py` |
| OrderCancellationPayload | kind:=order_cancellation; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; order_id:UUID; disposition_policy:ReturnPolicy | P02-04 / `packages/domain/src/logistics_domain/execution.py` |
| DemandIncreasePayload | kind:=demand_increase; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; order_id:UUID; delta_quantity:PositiveInt; delta_weight_g:PositiveInt; delta_volume_cm3:PositiveInt | P02-04 / `packages/domain/src/logistics_domain/execution.py` |
| DemandDecreasePayload | kind:=demand_decrease; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; order_id:UUID; delta_quantity:PositiveInt; delta_weight_g:PositiveInt; delta_volume_cm3:PositiveInt | P02-04 / `packages/domain/src/logistics_domain/execution.py` |
| EquipmentFailurePayload | kind:=equipment_failure; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; equipment_id:UUID; unavailable_until_s:NonNegativeInt?; remaining_capacity_units:NonNegativeInt | P02-04 / `packages/domain/src/logistics_domain/execution.py` |
| WarehouseResourceUnavailablePayload | kind:=warehouse_resource_unavailable; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; resource_ref:EntityRef; unavailable_window:TimeWindow; remaining_capacity_units:NonNegativeInt | P02-04 / `packages/domain/src/logistics_domain/execution.py` |
| EventPayload | discriminator=kind; vehicle_failure→VehicleFailurePayload; transport_delay→TransportDelayPayload; traffic_disruption→TrafficDisruptionPayload; weather_change→WeatherChangePayload; cargo_anomaly→CargoAnomalyPayload; order_cancellation→OrderCancellationPayload; demand_increase→DemandIncreasePayload; demand_decrease→DemandDecreasePayload; equipment_failure→EquipmentFailurePayload; warehouse_resource_unavailable→WarehouseResourceUnavailablePayload | P02-04 / `packages/domain/src/logistics_domain/execution.py` |
| ScenarioEventSpec | event_id:UUID; payload:EventPayload | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| ScenarioSize | orders:NonNegativeInt; cargo:NonNegativeInt; vehicles:NonNegativeInt; drivers:NonNegativeInt; warehouses:NonNegativeInt; zones:NonNegativeInt; storage_locations:NonNegativeInt; docks:NonNegativeInt; workers:NonNegativeInt; equipment:NonNegativeInt; transport_tasks:NonNegativeInt; warehouse_tasks:NonNegativeInt; inventory_entries:NonNegativeInt; matrices:NonNegativeInt | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| ScenarioRef | scenario_id:UUID; dataset_version:PositiveInt; schema_version:=2.0.0; content_hash:Sha256 | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| ScenarioSpec | id:UUID; version:PositiveInt; schema_version:=2.0.0; generator_version:VersionText; seed:Seed; epoch_utc:UTC; horizon_s:Horizon; size:ScenarioSize; generation_policy:GenerationPolicy; event_specs:ScenarioEventSpec[] | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| ScenarioInput | snapshot:PlanningSnapshot; transport_tasks:TransportTask[]; warehouse_tasks:WarehouseTask[] | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| ScenarioBundle | schema_version:=2.0.0; ref:ScenarioRef; spec:ScenarioSpec; input:ScenarioInput; source:=synthetic | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| ExpectedInteger | kind:=integer; measure:ExpectationMeasure; value:NonNegativeInt | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| ExpectationMeasure | DISTANCE_M=distance_m; COST_CENTS=cost_cents; COMPLETION_S=completion_s; MAKESPAN_S=makespan_s; CHANGED_TASKS=changed_tasks | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| ExpectedViolation | kind:=violation; code:ConstraintCode | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| ExpectedTaskSet | kind:=task_set; task_ids:UUID[] | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| FixtureExpectation | discriminator=kind; integer→ExpectedInteger; violation→ExpectedViolation; task_set→ExpectedTaskSet | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| FixtureExpectations | schema_version:=2.0.0; scenario_ref:ScenarioRef; expectations:FixtureExpectation[] | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| ActorContext | actor_id:UUID; role:ActorRole; scope_id:UUID | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| RequestRef | request_id:UUID; version:PositiveInt; schema_version:=2.0.0; hash:Sha256; family:JobKind | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| OptimizationJobPayload | family:=optimization; request_ref:RequestRef; mode:JobOptimizationMode | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| SimulationJobPayload | family:=simulation; request_ref:RequestRef | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| RescheduleJobPayload | family:=reschedule; request_ref:RequestRef | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| ExperimentJobPayload | family:=experiment; request_ref:RequestRef | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| MetricJobPayload | family:=metric; request_ref:RequestRef | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| JobPayload | discriminator=family; optimization→OptimizationJobPayload; simulation→SimulationJobPayload; reschedule→RescheduleJobPayload; experiment→ExperimentJobPayload; metric→MetricJobPayload | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| JobCommand | schema_version:=2.0.0; kind:JobKind; payload:JobPayload; deadline_utc:UTC | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| JobRequest | 逐字段/约束映射 JobCommand；不重复领域定义 | P02-04 / `packages/contracts/src/logistics_contracts/runtime.py` |
| RequestMetadata | ref:RequestRef; scope_id:UUID; owner_actor_id:UUID; optimization_mode:JobOptimizationMode?; media_type:=application/json | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| JobResultRef | result_id:UUID; version:PositiveInt; schema_version:=2.0.0; hash:Sha256; family:JobKind | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| JobFailure | code:ErrorCode; safe_message:SafeText; trace_id:UUID; retryable:bool; diagnostic_ref:ArtifactRef? | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| Job | id:UUID; created_at:UTC; updated_at:UTC; row_version:NonNegativeInt; schema_version:=2.0.0; created_by:UUID; status:JobStatus; kind:JobKind; command:JobCommand; request_hash:Sha256; trace_id:UUID; actor_id:UUID; scope_id:UUID; available_at:UTC; deadline_utc:UTC; attempt:NonNegativeInt; max_attempts:PositiveInt; cancel_requested:bool; lease_owner:UUID?; lease_epoch:NonNegativeInt; lease_expires_at:UTC?; started_at:UTC?; finished_at:UTC?; result_ref:JobResultRef?; failure:JobFailure? | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| JobAttempt | id:UUID; created_at:UTC; updated_at:UTC; row_version:NonNegativeInt; schema_version:=2.0.0; created_by:UUID; status:=recorded; job_id:UUID; attempt_no:PositiveInt; lease_owner:UUID; lease_epoch:PositiveInt; started_at:UTC; finished_at:UTC; outcome:AttemptOutcome; failure:JobFailure?; result_ref:JobResultRef? | P02-04 / `packages/domain/src/logistics_domain/runtime.py` |
| AttemptOutcome | COMPLETED=completed; FAILED=failed; CANCELLED=cancelled; LEASE_LOST=lease_lost | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| ErrorEnvelope | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#公共类型与状态；HTTP具名投影见下文精确投影表 | P02-04 / `packages/contracts/src/logistics_contracts/common.py` |
| JobRef | schema_version:=2.0.0; job_id:UUID; status:JobStatus; status_url:str; result_url:str; trace_id:UUID | P05-03 / `packages/contracts/src/logistics_contracts/runtime.py` |
| JobView | schema_version:=2.0.0; job_id:UUID; kind:JobKind; status:JobStatus; row_version:NonNegativeInt; created_at:UTC; started_at:UTC?; finished_at:UTC?; attempt:NonNegativeInt; max_attempts:PositiveInt; deadline_utc:UTC; cancel_requested:bool; result_ref:JobResultRef?; error:ErrorEnvelope?; trace_id:UUID | P05-03 / `packages/contracts/src/logistics_contracts/runtime.py` |
| CancelCommand | schema_version:=2.0.0; expected_revision:NonNegativeInt; reason:SafeText | P05-03 / `packages/contracts/src/logistics_contracts/runtime.py` |
| LeaseToken | job_id:UUID; owner_id:UUID; epoch:PositiveInt; expires_at:UTC | P05-03 / `apps/backend/src/logistics_backend/application/jobs.py` |
| Deadline | expires_at_utc:UTC | P05-03 / `apps/backend/src/logistics_backend/application/jobs.py` |
| WorkIdle | kind:=idle | P05-03 / `apps/backend/src/logistics_backend/application/jobs.py` |
| WorkTerminal | kind:=terminal; job_id:UUID; attempt_no:PositiveInt; lease_epoch:PositiveInt; status:TerminalJobStatus; result_ref:JobResultRef?; failure:JobFailure? | P05-03 / `apps/backend/src/logistics_backend/application/jobs.py` |
| TerminalJobStatus | COMPLETED=completed; FAILED=failed; CANCELLED=cancelled | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| WorkRetryScheduled | kind:=retry_scheduled; job_id:UUID; attempt_no:PositiveInt; lease_epoch:PositiveInt; next_available_at:UTC; failure:JobFailure | P05-03 / `apps/backend/src/logistics_backend/application/jobs.py` |
| WorkLeaseLost | kind:=lease_lost; job_id:UUID; attempt_no:PositiveInt; lease_epoch:PositiveInt; failure:JobFailure | P05-03 / `apps/backend/src/logistics_backend/application/jobs.py` |
| WorkOutcome | discriminator=kind; idle→WorkIdle; terminal→WorkTerminal; retry_scheduled→WorkRetryScheduled; lease_lost→WorkLeaseLost | P05-03 / `apps/backend/src/logistics_backend/application/jobs.py` |
| ImportCount | entity_kind:EntityKind; inserted:NonNegativeInt; unchanged:NonNegativeInt | P04-02 / `apps/backend/src/logistics_backend/cli/seed.py` |
| ImportStatus | IMPORTED=imported; NO_CHANGE=no_change; REJECTED=rejected | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| ImportReceipt | schema_version:=2.0.0; scenario_ref:ScenarioRef; status:ImportStatus; counts:ImportCount[]; inserted:NonNegativeInt; unchanged:NonNegativeInt; error:ErrorEnvelope? | P04-02 / `apps/backend/src/logistics_backend/cli/seed.py` |
| SecretValue | 继承具名原契约 docs/architecture/IMPLEMENTATION_CONVENTIONS.md#n01-r01-早期配置与http闭包；HTTP具名投影见下文精确投影表 | P05-01 / `apps/backend/src/logistics_backend/bootstrap.py` |
| CredentialGrant | actor_id:UUID; role:ActorRole; token_sha256:Sha256 | P05-01 / `apps/backend/src/logistics_backend/bootstrap.py` |
| RuntimeMode | DEVELOPMENT=development; TEST=test; PRODUCTION=production | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| Settings | mode:RuntimeMode; database_url:SecretValue; scope_id:UUID; credentials:CredentialGrant[]; bind_host:str; bind_port:PositiveInt; max_body_bytes:PositiveInt; request_timeout_s:PositiveInt | P05-01 / `apps/backend/src/logistics_backend/bootstrap.py` |
| HealthResponse | schema_version:=2.0.0; status:=alive | P05-01 / `packages/contracts/src/logistics_contracts/http.py` |
| ReadyStatus | READY=ready; NOT_READY=not_ready | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| DependencyStatus | AVAILABLE=available; UNAVAILABLE=unavailable | P02-01 / `packages/domain/src/logistics_domain/states.py` |
| ReadinessResponse | schema_version:=2.0.0; status:ReadyStatus; database:DependencyStatus; trace_id:UUID | P05-01 / `packages/contracts/src/logistics_contracts/http.py` |
| CargoCreate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| OrderCreate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| VehicleCreate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| DriverCreate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| WarehouseCreate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| ZoneCreate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| LocationCreate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| DockCreate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| WorkerCreate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| EquipmentCreate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| OrderUpdate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| VehicleUpdate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| DriverUpdate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| WarehouseUpdate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| ZoneUpdate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| LocationUpdate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| DockUpdate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| WorkerUpdate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| EquipmentUpdate | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| OrderUpdateBranch | entity_kind:=order; entity_id:UUID; changes:OrderUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| VehicleUpdateBranch | entity_kind:=vehicle; entity_id:UUID; changes:VehicleUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| DriverUpdateBranch | entity_kind:=driver; entity_id:UUID; changes:DriverUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| WarehouseUpdateBranch | entity_kind:=warehouse; entity_id:UUID; changes:WarehouseUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| ZoneUpdateBranch | entity_kind:=zone; entity_id:UUID; changes:ZoneUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| LocationUpdateBranch | entity_kind:=location; entity_id:UUID; changes:LocationUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| DockUpdateBranch | entity_kind:=dock; entity_id:UUID; changes:DockUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| WorkerUpdateBranch | entity_kind:=worker; entity_id:UUID; changes:WorkerUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| EquipmentUpdateBranch | entity_kind:=equipment; entity_id:UUID; changes:EquipmentUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| MasterDataUpdate | discriminator=entity_kind; order→OrderUpdateBranch; vehicle→VehicleUpdateBranch; driver→DriverUpdateBranch; warehouse→WarehouseUpdateBranch; zone→ZoneUpdateBranch; location→LocationUpdateBranch; dock→DockUpdateBranch; worker→WorkerUpdateBranch; equipment→EquipmentUpdateBranch | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| ZoneResourceUpdate | kind:=zone; changes:ZoneUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| LocationResourceUpdate | kind:=location; changes:LocationUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| DockResourceUpdate | kind:=dock; changes:DockUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| WorkerResourceUpdate | kind:=worker; changes:WorkerUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| EquipmentResourceUpdate | kind:=equipment; changes:EquipmentUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| ResourceUpdate | discriminator=kind; zone→ZoneResourceUpdate; location→LocationResourceUpdate; dock→DockResourceUpdate; worker→WorkerResourceUpdate; equipment→EquipmentResourceUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| OrderMasterView | entity_kind:=order; value:OrderDTO | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| VehicleMasterView | entity_kind:=vehicle; value:VehicleDTO | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| DriverMasterView | entity_kind:=driver; value:DriverDTO | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| WarehouseMasterView | entity_kind:=warehouse; value:WarehouseDTO | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| ZoneMasterView | entity_kind:=zone; value:ZoneDTO | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| LocationMasterView | entity_kind:=location; value:StorageLocationDTO | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| DockMasterView | entity_kind:=dock; value:DockDTO | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| WorkerMasterView | entity_kind:=worker; value:WorkerDTO | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| EquipmentMasterView | entity_kind:=equipment; value:EquipmentDTO | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| MasterDataView | discriminator=entity_kind; order→OrderMasterView; vehicle→VehicleMasterView; driver→DriverMasterView; warehouse→WarehouseMasterView; zone→ZoneMasterView; location→LocationMasterView; dock→DockMasterView; worker→WorkerMasterView; equipment→EquipmentMasterView | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| PageQuery | cursor:str?; limit:PositiveInt | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| OrderFilter | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| OrderPage | schema_version:=2.0.0; items:OrderDTO[]; next_cursor:str?; has_more:bool | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| VehicleFilter | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| VehiclePage | schema_version:=2.0.0; items:VehicleDTO[]; next_cursor:str?; has_more:bool | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| DriverQuery | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| DriverPage | schema_version:=2.0.0; items:DriverDTO[]; next_cursor:str?; has_more:bool | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| WarehouseFilter | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| WarehousePage | schema_version:=2.0.0; items:WarehouseDTO[]; next_cursor:str?; has_more:bool | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| ZoneQuery | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| ZonePage | schema_version:=2.0.0; items:ZoneDTO[]; next_cursor:str?; has_more:bool | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| LocationQuery | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| LocationPage | schema_version:=2.0.0; items:StorageLocationDTO[]; next_cursor:str?; has_more:bool | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| DockQuery | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| DockPage | schema_version:=2.0.0; items:DockDTO[]; next_cursor:str?; has_more:bool | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| WorkerQuery | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| WorkerPage | schema_version:=2.0.0; items:WorkerDTO[]; next_cursor:str?; has_more:bool | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| EquipmentQuery | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| EquipmentPage | schema_version:=2.0.0; items:EquipmentDTO[]; next_cursor:str?; has_more:bool | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |
| PagePosition | version:=1; scope_id:UUID; entity_kind:EntityKind; filter_hash:Sha256; after_created_at:UTC; after_id:UUID | P05-02 / `packages/contracts/src/logistics_contracts/http.py` |


### 逐项合法示例与违规反例

| 决定 | 合法输入 / 预期 | 单点违规 / 必须检出 |
| --- | --- | --- |
| F01 | 五kind分别引用同family，optimization三mode可解析 | routing未知kind；simulation带mode；kind/payload/ref错配→422 |
| F02 | 相同规范spec/input两次hash一致，期望旁文件独立 | ref.version≠spec.version；63位hash；input含expected_plan；size不符；事件超horizon→拒绝 |
| F03 | epoch明确，[0,10)@1+[10,20)@0接续合法 | 重叠、反序、bool/float秒、无epoch、units超容量→拒绝；跨epoch未经投影不能复用 |
| F04 | 已注册同ID/version原字节hash+真实handler；strictref解析 | 改原字节/旧revision/无handler分别422/409/501，不产生Job；旧lease不能写结果 |
| Actor/Resource | 可信operator同scope；equipment包装+内部handling | viewer写403；body自报role；zone包装EquipmentDTO→拒绝 |
| Job/内部协议 | completed带typed INFEASIBLE结果ref仍为completed | completed无结果、失败无failure、结束早于开始、耗尽后retry→拒绝 |

上述是可执行契约检查的规范样例，不是正式业务运行证据。验证日志与本轮交接绑定，独立N02决定是否解除冻结阻断。


## N01-R02 EntityKind 与事件引用闭包决定

本节是 **N01-R02 新规范决定**，修复 N02-R01-F02-C01；旧示例脚本的11值集合不属于此前冻结规范。当前候选仍为计划1.0.3、业务契约2.0.0，补足的是尚未签收的2.0.0设计，不能声称已有2.0.0发布兼容。字段/成员附表唯一定稿见 `contracts/changes/N01-R01-contract-decisions.json` 的 `EntityKind`、`EntityRef`、`entity_ref_targets` 与 `event_entity_ref_mapping`。本节及规范附表待独立N02-R02复核，不更新官方冻结或Gate。

### 完整成员与精确序列化值

完整且封闭集合为45项：DOMAIN_CATALOG的32必需实体、其“必需辅助实体”节的11已有实体，以及TravelMatrix、RegionRef两个既有纯值目标。纳入11辅助实体是本轮明确的地址空间决定，允许现有审计/生命周期描述既有对象，不增加实体、字段、表、处理器或API。WarehouseZone/StorageLocation的值保留既有资源包装和HTTP投影的zone/location；成员名与值分开，不接受warehouse_zone/storage_location别名、大小写变体或旧脚本未登记值。

| 成员名 | 精确 JSON 字符串 | 引用目标及 ID 字段 | revision 来源 |
| --- | --- | --- | --- |
| ORDER | `order` | Order.id | row_version |
| CARGO | `cargo` | Cargo.id | row_version |
| VEHICLE | `vehicle` | Vehicle.id | row_version |
| DRIVER | `driver` | Driver.id | row_version |
| WAREHOUSE | `warehouse` | Warehouse.id | row_version |
| WAREHOUSE_ZONE | `zone` | WarehouseZone.id | row_version |
| STORAGE_LOCATION | `location` | StorageLocation.id | row_version |
| DOCK | `dock` | Dock.id | row_version |
| WORKER | `worker` | Worker.id | row_version |
| EQUIPMENT | `equipment` | Equipment.id | row_version |
| TRANSPORT_TASK | `transport_task` | TransportTask.id | row_version |
| WAREHOUSE_TASK | `warehouse_task` | WarehouseTask.id | row_version |
| ROUTE | `route` | Route.id | row_version |
| ROUTE_STOP | `route_stop` | RouteStop.id | row_version |
| SCHEDULE | `schedule` | Schedule.id | row_version |
| SCHEDULE_TASK | `schedule_task` | ScheduleTask.id | row_version |
| SCHEDULE_VERSION | `schedule_version` | ScheduleVersion.id | row_version |
| CONSTRAINT | `constraint` | Constraint.id | row_version |
| OPTIMIZATION_REQUEST | `optimization_request` | OptimizationRequest.id | row_version |
| OPTIMIZATION_RESULT | `optimization_result` | OptimizationResult.id | row_version |
| SIMULATION | `simulation` | Simulation.id | row_version |
| SIMULATION_SNAPSHOT | `simulation_snapshot` | SimulationSnapshot.id | row_version |
| EVENT | `event` | Event.id | row_version |
| EXCEPTION_EVENT | `exception_event` | ExceptionEvent.id | row_version |
| RESCHEDULE_REQUEST | `reschedule_request` | RescheduleRequest.id | row_version |
| RESCHEDULE_RESULT | `reschedule_result` | RescheduleResult.id | row_version |
| AGENT_RUN | `agent_run` | AgentRun.id | row_version |
| TOOL_CALL | `tool_call` | ToolCall.id | row_version |
| DECISION_RECORD | `decision_record` | DecisionRecord.id | row_version |
| EXPERIMENT | `experiment` | Experiment.id | row_version |
| METRIC | `metric` | Metric.id | row_version |
| EXPERIMENT_RESULT | `experiment_result` | ExperimentResult.id | row_version |
| PLANNING_SNAPSHOT | `planning_snapshot` | PlanningSnapshot.id | row_version |
| JOB | `job` | Job.id | row_version |
| JOB_ATTEMPT | `job_attempt` | JobAttempt.id | row_version |
| IDEMPOTENCY | `idempotency` | Idempotency.id | row_version |
| RESERVATION | `reservation` | Reservation.id | row_version |
| INVENTORY_LEDGER | `inventory_ledger` | InventoryLedger.id | row_version |
| OUTBOX | `outbox` | Outbox.id | row_version |
| AUDIT_ENTRY | `audit_entry` | AuditEntry.id | row_version |
| LIFECYCLE_EVENT | `lifecycle_event` | LifecycleEvent.id | row_version |
| EXECUTION_SNAPSHOT | `execution_snapshot` | ExecutionSnapshot.id | row_version |
| CONFIRMATION_TOKEN | `confirmation_token` | ConfirmationToken.id | row_version |
| TRAVEL_MATRIX | `travel_matrix` | TravelMatrix.id | version |
| REGION | `region` | RegionRef.region_id | 必须 null |

EntityKind唯一P02-01 `states.py`；EntityRef唯一P02-01 `primitives.py`，完整字段为 `kind:EntityKind; id:UUID; revision:NonNegativeInt?`，extra=forbid，bool不是int。登记目标是消费者解析元数据，不能让早期枚举/值对象导入P02-03/P02-04或其他未来模型。未提供revision只表达身份，不宣称当前版本匹配；提供时按具名事实快照的row_version或矩阵version核验。UUID合法但目标不存在、kind/目标类型不相符、引用的作用域不同、ID不一致或给定revision过期均拒绝。区域引用必须null；它标识内嵌节点分组，不是独立实体、数据库行或可假设存在的区域表。

ResourceRevision仍是行修订向量：仅允许32实体或11辅助实体，内部EntityRef.revision非空时等于外部row_version；矩阵版本由既有TravelMatrix/MatrixRef表示，region不进入行向量。ConflictDetail、Violation、IntentDraft、ExceptionEvent、RealtimeEnvelope、AuditEntry和LifecycleEvent复用此地址空间。实时通知的对象revision按相应实体行来源；历史审计/冲突/校验报告保持当时事实引用，不把它们统一重新解析为现在的可变行而制造旧证据失效。公开输出仍遵守现有scope/脱敏规则，能引用某kind不授予读取秘密字段的权限。

### 十类 EventPayload 的目标映射

以下映射只收紧已冻结payload的引用语义，不添加事件字段或改变Job/Scenario/Calendar设计。解析上下文必须是同一场景/执行事实的具名对象集合、矩阵及显式区域分组，不用任意字符串或事件ID冒充目标ID；缺少上下文不能报告引用有效。

| payload.kind | 合法 entity_ref.kind | 目标与 ID 一致性 | revision |
| --- | --- | --- | --- |
| vehicle_failure | vehicle | id=vehicle_id，解析 Vehicle.id | 给定时等于事实快照 row_version |
| transport_delay | transport_task | id=transport_task_id，解析 TransportTask.id | 给定时等于事实快照 row_version |
| traffic_disruption | travel_matrix | id=指定 snapshot.matrices 中的 TravelMatrix.id；同事件全部弧由该矩阵限定 | 必填且等于该矩阵 version |
| weather_change | region | id=region_ref.region_id；目标是该 payload 的显式节点分组 | 必须 null |
| cargo_anomaly | cargo | id=cargo_id，解析 Cargo.id | 给定时等于事实快照 row_version |
| order_cancellation | order | id=order_id，解析 Order.id | 给定时等于事实快照 row_version |
| demand_increase | order | id=order_id，解析 Order.id | 给定时等于事实快照 row_version |
| demand_decrease | order | id=order_id，解析 Order.id | 给定时等于事实快照 row_version |
| equipment_failure | equipment | id=equipment_id，解析 Equipment.id | 给定时等于事实快照 row_version |
| warehouse_resource_unavailable | warehouse / zone / location / dock / worker / equipment | entity_ref=resource_ref（kind/id/revision 全部相等），解析相应既有资源 | 给定时等于事实快照 row_version |

交通多弧：entity_ref选定一个现有TravelMatrix；arc_refs必须非空，有向(from_node_id,to_node_id)不得重复或自环，两端都属于该矩阵node_ids。多弧不拿第一条弧、某个节点或新矩阵ID冒充整个矩阵身份；跨矩阵影响拆成多个事件。new_matrix_version必须严格大于所引用旧version；旧矩阵/旧hash不覆盖。ArcRef继续只有from_node_id/to_node_id，不增加matrix_id/arc_id。

天气区域：entity_ref.id精确等于region_ref.region_id；node_ids非空且唯一，每个节点都在场景矩阵节点并集。同一场景版本内，同region_id必须绑定同一节点集合（顺序不改变集合），不得在另一事件中换成员。影响范围恰为每个场景矩阵中两个端点都属于该集合的有向弧；new_matrix_version严格大于每个受影响矩阵当前version。没有受影响弧可作为明确无作用输入保留，不凭空增加弧；缺矩阵或未知节点拒绝。RegionRef结构不变，不通过区域名猜测节点或地理边界。

仓储资源：外层entity_ref与resource_ref按完整(kind,id,revision)相等，目标存在于同scope的Warehouse/WarehouseZone/StorageLocation/Dock/Worker/Equipment。warehouse是Warehouse本体，仍不进入既有Resource五分支包装；zone没有calendar，不因此添加日历。vehicle/driver/order或节点不能作为此分支的资源目标。unavailable_window保持既有TimeWindow闭窗语义，资源占用的半开区间规则不变，本轮不重定义端点或容量算法。

本轮设计检查必须从规范读取枚举与十映射，覆盖每个分支合法目标及未知kind、错目标、ID不一致、缺失目标、修订不一致；检查器拒绝EntityKind退回existing、成员遗漏/重复值、EntityRef字段未闭合或归属漂移及映射缺项/错目标。它们是设计证据，不是业务Schema、事件持久化、仿真或HTTP验收。
