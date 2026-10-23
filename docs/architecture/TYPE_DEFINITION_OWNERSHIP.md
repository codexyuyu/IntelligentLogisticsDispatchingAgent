# 早期具名类型定义任务与合法承载审计 · N01-R01

本轮设计决定，计划1.0.3、数据契约2.0.0；不是原契约已有事实或业务实现。N02-F01–F04和ARCH-0006/0007直接闭包全部形成具名字段/映射决定，不再把字段留给下游自造。完整形状及正反例见[DATA](DATA_CONTRACTS.md#n01-r01-本轮完整契约决定)，规范机器附表见[decisions](../../contracts/changes/N01-R01-contract-decisions.json)，版本/迁移见[changes](../../contracts/changes/N01-R01-contract-freeze-2.0.0.md)。定义任务在manifest仍planned，Gate仍not_run；只有独立N02可裁定冻结是否成立。

| 类型 | 唯一定义任务 / 精确承载 | 形状依据与决定 |
| --- | --- | --- |
| JobKind | P02-01 / `packages/domain/src/logistics_domain/states.py` | OPTIMIZATION=optimization; SIMULATION=simulation; RESCHEDULE=reschedule; EXPERIMENT=experiment; METRIC=metric |
| JobStatus | P02-01 / `packages/domain/src/logistics_domain/states.py` | QUEUED=queued; RUNNING=running; COMPLETED=completed; FAILED=failed; CANCELLED=cancelled |
| JobOptimizationMode | P02-01 / `packages/domain/src/logistics_domain/states.py` | TRANSPORT=transport; WAREHOUSE=warehouse; JOINT=joint |
| ActorRole | P02-01 / `packages/domain/src/logistics_domain/states.py` | VIEWER=viewer; OPERATOR=operator |
| ResourceKind | P02-01 / `packages/domain/src/logistics_domain/states.py` | ZONE=zone; LOCATION=location; DOCK=dock; WORKER=worker; EQUIPMENT=equipment |
| GenerationPolicy | P02-01 / `packages/domain/src/logistics_domain/states.py` | CANONICAL_T1=canonical_t1; CANONICAL_W1=canonical_w1; CANONICAL_J1=canonical_j1; CANONICAL_I1=canonical_i1; CANONICAL_S1=canonical_s1; CANONICAL_M1=canonical_m1; GRID_A=grid_a; GRID_B=grid_b; GRID_C1=grid_c1; GRID_C2=grid_c2; GRID_C3=grid_c3; GRID=grid |
| CargoCondition | P02-01 / `packages/domain/src/logistics_domain/states.py` | INTACT=intact; TEMPERATURE_EXCURSION=temperature_excursion; DAMAGED=damaged; MISSING=missing |
| ReturnPolicy | P02-01 / `packages/domain/src/logistics_domain/states.py` | RETURN_TO_ORIGIN=return_to_origin; QUARANTINE=quarantine |
| WeatherProfile | P02-01 / `packages/domain/src/logistics_domain/states.py` | CLEAR=clear; RAIN=rain; SNOW=snow; STORM=storm |
| CalendarInterval | P02-01 / `packages/domain/src/logistics_domain/primitives.py` | start_s:NonNegativeInt; end_s:NonNegativeInt; available_units:NonNegativeInt |
| ResourceCalendar | P02-01 / `packages/domain/src/logistics_domain/primitives.py` | epoch_utc:UTC; intervals:CalendarInterval[]; version:NonNegativeInt |
| Rational | P02-01 / `packages/domain/src/logistics_domain/primitives.py` | numerator:PositiveInt; denominator:PositiveInt |
| EntityRef | P02-01 / `packages/domain/src/logistics_domain/primitives.py` | kind:EntityKind; id:UUID; revision:NonNegativeInt? |
| ArtifactRef | P02-01 / `packages/domain/src/logistics_domain/primitives.py` | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#公共类型与状态；HTTP具名投影见下文精确投影表 |
| TimeWindow | P02-01 / `packages/domain/src/logistics_domain/primitives.py` | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#公共类型与状态；HTTP具名投影见下文精确投影表 |
| Load | P02-01 / `packages/domain/src/logistics_domain/primitives.py` | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#公共类型与状态；HTTP具名投影见下文精确投影表 |
| ErrorCode | P02-01 / `packages/domain/src/logistics_domain/states.py` | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#公共类型与状态；HTTP具名投影见下文精确投影表 |
| EntityKind | P02-01 / `packages/domain/src/logistics_domain/states.py` | ORDER=order; CARGO=cargo; VEHICLE=vehicle; DRIVER=driver; WAREHOUSE=warehouse; WAREHOUSE_ZONE=zone; STORAGE_LOCATION=location; DOCK=dock; WORKER=worker; EQUIPMENT=equipment; TRANSPORT_TASK=transport_task; WAREHOUSE_TASK=warehouse_task; ROUTE=route; ROUTE_STOP=route_stop; SCHEDULE=schedule; SCHEDULE_TASK=schedule_task; SCHEDULE_VERSION=schedule_version; CONSTRAINT=constraint; OPTIMIZATION_REQUEST=optimization_request; OPTIMIZATION_RESULT=optimization_result; SIMULATION=simulation; SIMULATION_SNAPSHOT=simulation_snapshot; EVENT=event; EXCEPTION_EVENT=exception_event; RESCHEDULE_REQUEST=reschedule_request; RESCHEDULE_RESULT=reschedule_result; AGENT_RUN=agent_run; TOOL_CALL=tool_call; DECISION_RECORD=decision_record; EXPERIMENT=experiment; METRIC=metric; EXPERIMENT_RESULT=experiment_result; PLANNING_SNAPSHOT=planning_snapshot; JOB=job; JOB_ATTEMPT=job_attempt; IDEMPOTENCY=idempotency; RESERVATION=reservation; INVENTORY_LEDGER=inventory_ledger; OUTBOX=outbox; AUDIT_ENTRY=audit_entry; LIFECYCLE_EVENT=lifecycle_event; EXECUTION_SNAPSHOT=execution_snapshot; CONFIRMATION_TOKEN=confirmation_token; TRAVEL_MATRIX=travel_matrix; REGION=region |
| ConstraintCode | P02-01 / `packages/domain/src/logistics_domain/states.py` | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#公共类型与状态；HTTP具名投影见下文精确投影表 |
| Order | P02-02 / `packages/domain/src/logistics_domain/orders.py` | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 |
| OrderDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` | 逐字段/约束映射 Order；不重复领域定义 |
| Cargo | P02-02 / `packages/domain/src/logistics_domain/orders.py` | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 |
| CargoDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` | 逐字段/约束映射 Cargo；不重复领域定义 |
| Vehicle | P02-02 / `packages/domain/src/logistics_domain/resources.py` | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 |
| VehicleDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` | 逐字段/约束映射 Vehicle；不重复领域定义 |
| Driver | P02-02 / `packages/domain/src/logistics_domain/resources.py` | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 |
| DriverDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` | 逐字段/约束映射 Driver；不重复领域定义 |
| Warehouse | P02-02 / `packages/domain/src/logistics_domain/resources.py` | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 |
| WarehouseDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` | 逐字段/约束映射 Warehouse；不重复领域定义 |
| WarehouseZone | P02-02 / `packages/domain/src/logistics_domain/resources.py` | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 |
| ZoneDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` | 逐字段/约束映射 WarehouseZone；不重复领域定义 |
| StorageLocation | P02-02 / `packages/domain/src/logistics_domain/resources.py` | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 |
| StorageLocationDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` | 逐字段/约束映射 StorageLocation；不重复领域定义 |
| Dock | P02-02 / `packages/domain/src/logistics_domain/resources.py` | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 |
| DockDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` | 逐字段/约束映射 Dock；不重复领域定义 |
| Worker | P02-02 / `packages/domain/src/logistics_domain/resources.py` | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 |
| WorkerDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` | 逐字段/约束映射 Worker；不重复领域定义 |
| Equipment | P02-02 / `packages/domain/src/logistics_domain/resources.py` | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 |
| EquipmentDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` | 逐字段/约束映射 Equipment；不重复领域定义 |
| ZoneResource | P02-02 / `packages/domain/src/logistics_domain/resources.py` | kind:=zone; value:WarehouseZone |
| ZoneResourceDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` | kind:=zone; value:ZoneDTO |
| LocationResource | P02-02 / `packages/domain/src/logistics_domain/resources.py` | kind:=location; value:StorageLocation |
| LocationResourceDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` | kind:=location; value:StorageLocationDTO |
| DockResource | P02-02 / `packages/domain/src/logistics_domain/resources.py` | kind:=dock; value:Dock |
| DockResourceDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` | kind:=dock; value:DockDTO |
| WorkerResource | P02-02 / `packages/domain/src/logistics_domain/resources.py` | kind:=worker; value:Worker |
| WorkerResourceDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` | kind:=worker; value:WorkerDTO |
| EquipmentResource | P02-02 / `packages/domain/src/logistics_domain/resources.py` | kind:=equipment; value:Equipment |
| EquipmentResourceDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` | kind:=equipment; value:EquipmentDTO |
| Resource | P02-02 / `packages/domain/src/logistics_domain/resources.py` | discriminator=kind; zone→ZoneResource; location→LocationResource; dock→DockResource; worker→WorkerResource; equipment→EquipmentResource |
| ResourceDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` | discriminator=kind; zone→ZoneResourceDTO; location→LocationResourceDTO; dock→DockResourceDTO; worker→WorkerResourceDTO; equipment→EquipmentResourceDTO |
| CalendarIntervalDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` | 逐字段/约束映射 CalendarInterval；不重复领域定义 |
| CalendarDTO | P02-02 / `packages/contracts/src/logistics_contracts/entities.py` | 逐字段/约束映射 ResourceCalendar；外层必需schema_version=2.0.0；不重复领域定义 |
| ResourceCalendarBinding | P02-02 / `packages/domain/src/logistics_domain/resources.py` | resource_id:UUID; source_calendar:ResourceCalendar; source_hash:Sha256; calendar:ResourceCalendar |
| ResourceBundle | P02-02 / `packages/domain/src/logistics_domain/resources.py` | warehouses:Warehouse[]; zones:WarehouseZone[]; locations:StorageLocation[]; docks:Dock[]; workers:Worker[]; equipment:Equipment[]; calendars:ResourceCalendarBinding[] |
| InventoryEntry | P02-03 / `packages/domain/src/logistics_domain/planning.py` | cargo_id:UUID; location_id:UUID; quantity_units:NonNegativeInt; weight_g:NonNegativeInt; volume_cm3:NonNegativeInt |
| PlanningScope | P02-03 / `packages/domain/src/logistics_domain/planning.py` | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#关键-schema未列的实体字段继承-domain_catalog；HTTP具名投影见下文精确投影表 |
| TransportTask | P02-03 / `packages/domain/src/logistics_domain/planning.py` | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 |
| WarehouseTask | P02-03 / `packages/domain/src/logistics_domain/planning.py` | 继承具名原契约 docs/architecture/DOMAIN_CATALOG.md#32-个必需实体；HTTP具名投影见下文精确投影表 |
| TravelMatrix | P02-03 / `packages/domain/src/logistics_domain/planning.py` | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#关键-schema未列的实体字段继承-domain_catalog；HTTP具名投影见下文精确投影表 |
| ResourceRevision | P02-03 / `packages/domain/src/logistics_domain/planning.py` | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#关键-schema未列的实体字段继承-domain_catalog；HTTP具名投影见下文精确投影表 |
| ObjectivePolicy | P02-03 / `packages/domain/src/logistics_domain/planning.py` | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#关键-schema未列的实体字段继承-domain_catalog；HTTP具名投影见下文精确投影表 |
| SolveBudget | P02-03 / `packages/domain/src/logistics_domain/planning.py` | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#关键-schema未列的实体字段继承-domain_catalog；HTTP具名投影见下文精确投影表 |
| PlanningSnapshot | P02-03 / `packages/domain/src/logistics_domain/planning.py` | id:UUID; scope:PlanningScope; orders:Order[]; cargo:Cargo[]; vehicles:Vehicle[]; drivers:Driver[]; resources:ResourceBundle; inventory:InventoryEntry[]; revisions:ResourceRevision[]; matrices:TravelMatrix[]; hash:Sha256 |
| AtNodeLocation | P02-04 / `packages/domain/src/logistics_domain/execution.py` | kind:=at_node; node_id:UUID |
| OnArcLocation | P02-04 / `packages/domain/src/logistics_domain/execution.py` | kind:=on_arc; from_node_id:UUID; to_node_id:UUID; departed_at_s:NonNegativeInt; expected_arrival_s:NonNegativeInt; progress_numerator:NonNegativeInt; progress_denominator:PositiveInt |
| ExecutionLocation | P02-04 / `packages/domain/src/logistics_domain/execution.py` | discriminator=kind; at_node→AtNodeLocation; on_arc→OnArcLocation |
| ArcRef | P02-04 / `packages/domain/src/logistics_domain/execution.py` | from_node_id:UUID; to_node_id:UUID |
| RegionRef | P02-04 / `packages/domain/src/logistics_domain/execution.py` | region_id:UUID; node_ids:UUID[] |
| VehicleFailurePayload | P02-04 / `packages/domain/src/logistics_domain/execution.py` | kind:=vehicle_failure; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; vehicle_id:UUID; location:ExecutionLocation; unavailable_until_s:NonNegativeInt?; cargo_condition:CargoCondition |
| TransportDelayPayload | P02-04 / `packages/domain/src/logistics_domain/execution.py` | kind:=transport_delay; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; transport_task_id:UUID; additional_seconds:PositiveInt |
| TrafficDisruptionPayload | P02-04 / `packages/domain/src/logistics_domain/execution.py` | kind:=traffic_disruption; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; arc_refs:ArcRef[]; closure:bool; travel_multiplier:Rational?; new_matrix_version:PositiveInt |
| WeatherChangePayload | P02-04 / `packages/domain/src/logistics_domain/execution.py` | kind:=weather_change; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; region_ref:RegionRef; profile:WeatherProfile; travel_multiplier:Rational; new_matrix_version:PositiveInt |
| CargoAnomalyPayload | P02-04 / `packages/domain/src/logistics_domain/execution.py` | kind:=cargo_anomaly; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; cargo_id:UUID; condition:CargoCondition; quantity_units:PositiveInt; measured_temp_decic:int? |
| OrderCancellationPayload | P02-04 / `packages/domain/src/logistics_domain/execution.py` | kind:=order_cancellation; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; order_id:UUID; disposition_policy:ReturnPolicy |
| DemandIncreasePayload | P02-04 / `packages/domain/src/logistics_domain/execution.py` | kind:=demand_increase; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; order_id:UUID; delta_quantity:PositiveInt; delta_weight_g:PositiveInt; delta_volume_cm3:PositiveInt |
| DemandDecreasePayload | P02-04 / `packages/domain/src/logistics_domain/execution.py` | kind:=demand_decrease; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; order_id:UUID; delta_quantity:PositiveInt; delta_weight_g:PositiveInt; delta_volume_cm3:PositiveInt |
| EquipmentFailurePayload | P02-04 / `packages/domain/src/logistics_domain/execution.py` | kind:=equipment_failure; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; equipment_id:UUID; unavailable_until_s:NonNegativeInt?; remaining_capacity_units:NonNegativeInt |
| WarehouseResourceUnavailablePayload | P02-04 / `packages/domain/src/logistics_domain/execution.py` | kind:=warehouse_resource_unavailable; entity_ref:EntityRef; effective_at_s:NonNegativeInt; reason:SafeText; resource_ref:EntityRef; unavailable_window:TimeWindow; remaining_capacity_units:NonNegativeInt |
| EventPayload | P02-04 / `packages/domain/src/logistics_domain/execution.py` | discriminator=kind; vehicle_failure→VehicleFailurePayload; transport_delay→TransportDelayPayload; traffic_disruption→TrafficDisruptionPayload; weather_change→WeatherChangePayload; cargo_anomaly→CargoAnomalyPayload; order_cancellation→OrderCancellationPayload; demand_increase→DemandIncreasePayload; demand_decrease→DemandDecreasePayload; equipment_failure→EquipmentFailurePayload; warehouse_resource_unavailable→WarehouseResourceUnavailablePayload |
| ScenarioEventSpec | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | event_id:UUID; payload:EventPayload |
| ScenarioSize | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | orders:NonNegativeInt; cargo:NonNegativeInt; vehicles:NonNegativeInt; drivers:NonNegativeInt; warehouses:NonNegativeInt; zones:NonNegativeInt; storage_locations:NonNegativeInt; docks:NonNegativeInt; workers:NonNegativeInt; equipment:NonNegativeInt; transport_tasks:NonNegativeInt; warehouse_tasks:NonNegativeInt; inventory_entries:NonNegativeInt; matrices:NonNegativeInt |
| ScenarioRef | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | scenario_id:UUID; dataset_version:PositiveInt; schema_version:=2.0.0; content_hash:Sha256 |
| ScenarioSpec | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | id:UUID; version:PositiveInt; schema_version:=2.0.0; generator_version:VersionText; seed:Seed; epoch_utc:UTC; horizon_s:Horizon; size:ScenarioSize; generation_policy:GenerationPolicy; event_specs:ScenarioEventSpec[] |
| ScenarioInput | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | snapshot:PlanningSnapshot; transport_tasks:TransportTask[]; warehouse_tasks:WarehouseTask[] |
| ScenarioBundle | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | schema_version:=2.0.0; ref:ScenarioRef; spec:ScenarioSpec; input:ScenarioInput; source:=synthetic |
| ExpectedInteger | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | kind:=integer; measure:ExpectationMeasure; value:NonNegativeInt |
| ExpectationMeasure | P02-01 / `packages/domain/src/logistics_domain/states.py` | DISTANCE_M=distance_m; COST_CENTS=cost_cents; COMPLETION_S=completion_s; MAKESPAN_S=makespan_s; CHANGED_TASKS=changed_tasks |
| ExpectedViolation | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | kind:=violation; code:ConstraintCode |
| ExpectedTaskSet | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | kind:=task_set; task_ids:UUID[] |
| FixtureExpectation | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | discriminator=kind; integer→ExpectedInteger; violation→ExpectedViolation; task_set→ExpectedTaskSet |
| FixtureExpectations | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | schema_version:=2.0.0; scenario_ref:ScenarioRef; expectations:FixtureExpectation[] |
| ActorContext | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | actor_id:UUID; role:ActorRole; scope_id:UUID |
| RequestRef | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | request_id:UUID; version:PositiveInt; schema_version:=2.0.0; hash:Sha256; family:JobKind |
| OptimizationJobPayload | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | family:=optimization; request_ref:RequestRef; mode:JobOptimizationMode |
| SimulationJobPayload | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | family:=simulation; request_ref:RequestRef |
| RescheduleJobPayload | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | family:=reschedule; request_ref:RequestRef |
| ExperimentJobPayload | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | family:=experiment; request_ref:RequestRef |
| MetricJobPayload | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | family:=metric; request_ref:RequestRef |
| JobPayload | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | discriminator=family; optimization→OptimizationJobPayload; simulation→SimulationJobPayload; reschedule→RescheduleJobPayload; experiment→ExperimentJobPayload; metric→MetricJobPayload |
| JobCommand | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | schema_version:=2.0.0; kind:JobKind; payload:JobPayload; deadline_utc:UTC |
| JobRequest | P02-04 / `packages/contracts/src/logistics_contracts/runtime.py` | 逐字段/约束映射 JobCommand；不重复领域定义 |
| RequestMetadata | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | ref:RequestRef; scope_id:UUID; owner_actor_id:UUID; optimization_mode:JobOptimizationMode?; media_type:=application/json |
| JobResultRef | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | result_id:UUID; version:PositiveInt; schema_version:=2.0.0; hash:Sha256; family:JobKind |
| JobFailure | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | code:ErrorCode; safe_message:SafeText; trace_id:UUID; retryable:bool; diagnostic_ref:ArtifactRef? |
| Job | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | id:UUID; created_at:UTC; updated_at:UTC; row_version:NonNegativeInt; schema_version:=2.0.0; created_by:UUID; status:JobStatus; kind:JobKind; command:JobCommand; request_hash:Sha256; trace_id:UUID; actor_id:UUID; scope_id:UUID; available_at:UTC; deadline_utc:UTC; attempt:NonNegativeInt; max_attempts:PositiveInt; cancel_requested:bool; lease_owner:UUID?; lease_epoch:NonNegativeInt; lease_expires_at:UTC?; started_at:UTC?; finished_at:UTC?; result_ref:JobResultRef?; failure:JobFailure? |
| JobAttempt | P02-04 / `packages/domain/src/logistics_domain/runtime.py` | id:UUID; created_at:UTC; updated_at:UTC; row_version:NonNegativeInt; schema_version:=2.0.0; created_by:UUID; status:=recorded; job_id:UUID; attempt_no:PositiveInt; lease_owner:UUID; lease_epoch:PositiveInt; started_at:UTC; finished_at:UTC; outcome:AttemptOutcome; failure:JobFailure?; result_ref:JobResultRef? |
| AttemptOutcome | P02-01 / `packages/domain/src/logistics_domain/states.py` | COMPLETED=completed; FAILED=failed; CANCELLED=cancelled; LEASE_LOST=lease_lost |
| ErrorEnvelope | P02-04 / `packages/contracts/src/logistics_contracts/common.py` | 继承具名原契约 docs/architecture/DATA_CONTRACTS.md#公共类型与状态；HTTP具名投影见下文精确投影表 |
| JobRef | P05-03 / `packages/contracts/src/logistics_contracts/runtime.py` | schema_version:=2.0.0; job_id:UUID; status:JobStatus; status_url:str; result_url:str; trace_id:UUID |
| JobView | P05-03 / `packages/contracts/src/logistics_contracts/runtime.py` | schema_version:=2.0.0; job_id:UUID; kind:JobKind; status:JobStatus; row_version:NonNegativeInt; created_at:UTC; started_at:UTC?; finished_at:UTC?; attempt:NonNegativeInt; max_attempts:PositiveInt; deadline_utc:UTC; cancel_requested:bool; result_ref:JobResultRef?; error:ErrorEnvelope?; trace_id:UUID |
| CancelCommand | P05-03 / `packages/contracts/src/logistics_contracts/runtime.py` | schema_version:=2.0.0; expected_revision:NonNegativeInt; reason:SafeText |
| LeaseToken | P05-03 / `apps/backend/src/logistics_backend/application/jobs.py` | job_id:UUID; owner_id:UUID; epoch:PositiveInt; expires_at:UTC |
| Deadline | P05-03 / `apps/backend/src/logistics_backend/application/jobs.py` | expires_at_utc:UTC |
| WorkIdle | P05-03 / `apps/backend/src/logistics_backend/application/jobs.py` | kind:=idle |
| WorkTerminal | P05-03 / `apps/backend/src/logistics_backend/application/jobs.py` | kind:=terminal; job_id:UUID; attempt_no:PositiveInt; lease_epoch:PositiveInt; status:TerminalJobStatus; result_ref:JobResultRef?; failure:JobFailure? |
| TerminalJobStatus | P02-01 / `packages/domain/src/logistics_domain/states.py` | COMPLETED=completed; FAILED=failed; CANCELLED=cancelled |
| WorkRetryScheduled | P05-03 / `apps/backend/src/logistics_backend/application/jobs.py` | kind:=retry_scheduled; job_id:UUID; attempt_no:PositiveInt; lease_epoch:PositiveInt; next_available_at:UTC; failure:JobFailure |
| WorkLeaseLost | P05-03 / `apps/backend/src/logistics_backend/application/jobs.py` | kind:=lease_lost; job_id:UUID; attempt_no:PositiveInt; lease_epoch:PositiveInt; failure:JobFailure |
| WorkOutcome | P05-03 / `apps/backend/src/logistics_backend/application/jobs.py` | discriminator=kind; idle→WorkIdle; terminal→WorkTerminal; retry_scheduled→WorkRetryScheduled; lease_lost→WorkLeaseLost |
| ImportCount | P04-02 / `apps/backend/src/logistics_backend/cli/seed.py` | entity_kind:EntityKind; inserted:NonNegativeInt; unchanged:NonNegativeInt |
| ImportStatus | P02-01 / `packages/domain/src/logistics_domain/states.py` | IMPORTED=imported; NO_CHANGE=no_change; REJECTED=rejected |
| ImportReceipt | P04-02 / `apps/backend/src/logistics_backend/cli/seed.py` | schema_version:=2.0.0; scenario_ref:ScenarioRef; status:ImportStatus; counts:ImportCount[]; inserted:NonNegativeInt; unchanged:NonNegativeInt; error:ErrorEnvelope? |
| SecretValue | P05-01 / `apps/backend/src/logistics_backend/bootstrap.py` | 继承具名原契约 docs/architecture/IMPLEMENTATION_CONVENTIONS.md#n01-r01-早期配置与http闭包；HTTP具名投影见下文精确投影表 |
| CredentialGrant | P05-01 / `apps/backend/src/logistics_backend/bootstrap.py` | actor_id:UUID; role:ActorRole; token_sha256:Sha256 |
| RuntimeMode | P02-01 / `packages/domain/src/logistics_domain/states.py` | DEVELOPMENT=development; TEST=test; PRODUCTION=production |
| Settings | P05-01 / `apps/backend/src/logistics_backend/bootstrap.py` | mode:RuntimeMode; database_url:SecretValue; scope_id:UUID; credentials:CredentialGrant[]; bind_host:str; bind_port:PositiveInt; max_body_bytes:PositiveInt; request_timeout_s:PositiveInt |
| HealthResponse | P05-01 / `packages/contracts/src/logistics_contracts/http.py` | schema_version:=2.0.0; status:=alive |
| ReadyStatus | P02-01 / `packages/domain/src/logistics_domain/states.py` | READY=ready; NOT_READY=not_ready |
| DependencyStatus | P02-01 / `packages/domain/src/logistics_domain/states.py` | AVAILABLE=available; UNAVAILABLE=unavailable |
| ReadinessResponse | P05-01 / `packages/contracts/src/logistics_contracts/http.py` | schema_version:=2.0.0; status:ReadyStatus; database:DependencyStatus; trace_id:UUID |
| CargoCreate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| OrderCreate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| VehicleCreate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| DriverCreate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| WarehouseCreate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| ZoneCreate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| LocationCreate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| DockCreate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| WorkerCreate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| EquipmentCreate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| OrderUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| VehicleUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| DriverUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| WarehouseUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| ZoneUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| LocationUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| DockUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| WorkerUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| EquipmentUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| OrderUpdateBranch | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | entity_kind:=order; entity_id:UUID; changes:OrderUpdate |
| VehicleUpdateBranch | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | entity_kind:=vehicle; entity_id:UUID; changes:VehicleUpdate |
| DriverUpdateBranch | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | entity_kind:=driver; entity_id:UUID; changes:DriverUpdate |
| WarehouseUpdateBranch | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | entity_kind:=warehouse; entity_id:UUID; changes:WarehouseUpdate |
| ZoneUpdateBranch | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | entity_kind:=zone; entity_id:UUID; changes:ZoneUpdate |
| LocationUpdateBranch | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | entity_kind:=location; entity_id:UUID; changes:LocationUpdate |
| DockUpdateBranch | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | entity_kind:=dock; entity_id:UUID; changes:DockUpdate |
| WorkerUpdateBranch | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | entity_kind:=worker; entity_id:UUID; changes:WorkerUpdate |
| EquipmentUpdateBranch | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | entity_kind:=equipment; entity_id:UUID; changes:EquipmentUpdate |
| MasterDataUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | discriminator=entity_kind; order→OrderUpdateBranch; vehicle→VehicleUpdateBranch; driver→DriverUpdateBranch; warehouse→WarehouseUpdateBranch; zone→ZoneUpdateBranch; location→LocationUpdateBranch; dock→DockUpdateBranch; worker→WorkerUpdateBranch; equipment→EquipmentUpdateBranch |
| ZoneResourceUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | kind:=zone; changes:ZoneUpdate |
| LocationResourceUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | kind:=location; changes:LocationUpdate |
| DockResourceUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | kind:=dock; changes:DockUpdate |
| WorkerResourceUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | kind:=worker; changes:WorkerUpdate |
| EquipmentResourceUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | kind:=equipment; changes:EquipmentUpdate |
| ResourceUpdate | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | discriminator=kind; zone→ZoneResourceUpdate; location→LocationResourceUpdate; dock→DockResourceUpdate; worker→WorkerResourceUpdate; equipment→EquipmentResourceUpdate |
| OrderMasterView | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | entity_kind:=order; value:OrderDTO |
| VehicleMasterView | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | entity_kind:=vehicle; value:VehicleDTO |
| DriverMasterView | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | entity_kind:=driver; value:DriverDTO |
| WarehouseMasterView | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | entity_kind:=warehouse; value:WarehouseDTO |
| ZoneMasterView | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | entity_kind:=zone; value:ZoneDTO |
| LocationMasterView | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | entity_kind:=location; value:StorageLocationDTO |
| DockMasterView | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | entity_kind:=dock; value:DockDTO |
| WorkerMasterView | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | entity_kind:=worker; value:WorkerDTO |
| EquipmentMasterView | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | entity_kind:=equipment; value:EquipmentDTO |
| MasterDataView | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | discriminator=entity_kind; order→OrderMasterView; vehicle→VehicleMasterView; driver→DriverMasterView; warehouse→WarehouseMasterView; zone→ZoneMasterView; location→LocationMasterView; dock→DockMasterView; worker→WorkerMasterView; equipment→EquipmentMasterView |
| PageQuery | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | cursor:str?; limit:PositiveInt |
| OrderFilter | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| OrderPage | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | schema_version:=2.0.0; items:OrderDTO[]; next_cursor:str?; has_more:bool |
| VehicleFilter | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| VehiclePage | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | schema_version:=2.0.0; items:VehicleDTO[]; next_cursor:str?; has_more:bool |
| DriverQuery | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| DriverPage | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | schema_version:=2.0.0; items:DriverDTO[]; next_cursor:str?; has_more:bool |
| WarehouseFilter | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| WarehousePage | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | schema_version:=2.0.0; items:WarehouseDTO[]; next_cursor:str?; has_more:bool |
| ZoneQuery | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| ZonePage | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | schema_version:=2.0.0; items:ZoneDTO[]; next_cursor:str?; has_more:bool |
| LocationQuery | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| LocationPage | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | schema_version:=2.0.0; items:StorageLocationDTO[]; next_cursor:str?; has_more:bool |
| DockQuery | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| DockPage | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | schema_version:=2.0.0; items:DockDTO[]; next_cursor:str?; has_more:bool |
| WorkerQuery | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| WorkerPage | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | schema_version:=2.0.0; items:WorkerDTO[]; next_cursor:str?; has_more:bool |
| EquipmentQuery | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | 继承具名原契约 docs/api/API_CONTRACT.md#n01-r01-主数据具名投影；HTTP具名投影见下文精确投影表 |
| EquipmentPage | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | schema_version:=2.0.0; items:EquipmentDTO[]; next_cursor:str?; has_more:bool |
| PagePosition | P05-02 / `packages/contracts/src/logistics_contracts/http.py` | version:=1; scope_id:UUID; entity_kind:EntityKind; filter_hash:Sha256; after_created_at:UTC; after_id:UUID |


MasterData是能力统称，无此实体；MasterDataService唯一P05-02 application/master_data.py，update返回具名MasterDataView。P16-01 JobResult映射唯一contracts/runtime.py，catalog已精确补白名单；P32/P33按自身已有结果类型增加typed分支并复用JobResultRef，未来不存在完整typed handler时禁止生产入队。本轮没有伪造未来类或运行验收。

JobKind/JobStatus/JobOptimizationMode仅states定义；Calendar仅primitives定义；Resource/DTO仅resources/entities对应定义；Actor/Scenario/Job纯值唯一runtime，Event纯值先execution，再单向runtime消费；contracts层只能映射纯domain。附表existing行是具名原契约或显式HTTP投影的复用来源，不是许可实现空类。module DAG与task祖先校验覆盖本轮注册图，继承类型的实际导出完整性仍须G02真实Schema/正反例验收。

状态：READY_FOR_INDEPENDENT_REVIEW。没有独立复核/G00签收，不得派发N03/P02；若N02发现残余契约缺口，按具体缺陷继续最小治理，而不是调整Gate判定。


## N01-R02 唯一阻断项的显式闭包补充

EntityKind已从existing改为完整45成员enum，EntityRef从existing改为kind/id/revision完整record；它们不是继承文档中的名称占位。枚举覆盖DOMAIN_CATALOG的32业务实体、11已有辅助实体及TravelMatrix/RegionRef两种既有纯值地址，完整成员/值和十类事件目标映射见DATA_CONTRACTS的“N01-R02 EntityKind 与事件引用闭包决定”及规范附表的entity_ref_targets/event_entity_ref_mapping。目标类型名称只用于消费者解析登记，不是states/primitives向未来模型的导入依赖。

唯一承载与顺序不变：EntityKind=P02-01 states.py；EntityRef=P02-01 primitives.py；EventPayload=P02-04 execution.py；ScenarioEventSpec=P02-04 runtime.py；未来消费者只引用。显式EntityRef.kind补齐先前existing占位未展示的primitives→states单向模块边，两者同归P02-01；execution继续引用primitives。任务依赖顺序/祖先不变，无未来或反向导入。JobKind/Scenario字段与隔离/Calendar/JobRequest的已解决决定保持。

状态：N01-R02 READY_FOR_INDEPENDENT_REVIEW。N02-R01历史阻断记录保留；只有独立N02-R02复核和真实G00恢复后才允许N03。该补充不签冻结/Gate，不宣称业务类型已实现。
