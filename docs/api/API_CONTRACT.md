# HTTP、作业与 Agent Tool 边界 · /api/v1

数据契约2.0.0，HTTP路径仍/api/v1；路径未改不表示body向后兼容。设计中的API，实施后以源码生成OpenAPI为唯一运行标准。每次路径、enum或字段变更必须同步生成客户端。路由只做认证、Schema解析、映射和状态码转换，调用应用服务；不能直接查改核心计划或运行求解。CPU密集任务交给同仓库独立worker，持久化作业与租约支持崩溃恢复；FastAPI的请求内后台机制不承担本系统求解可靠性职责。[FastAPI Background Tasks 文档](https://fastapi.tiangolo.com/tutorial/background-tasks/) 对较重后台计算给出不同执行方式的提示；本项目选择无需队列集群的数据库作业方案。

## 通用规则

- HTTP JSON UTF-8，实体ID UUID，时间ISO8601 UTC，schema_version必需。整数单位见DOMAIN_CATALOG；响应所有enum来自共享Schema。
- Cursor分页：`cursor?:opaque, limit:int=50(1..200)`，稳定`(created_at,id)`排序；列表返回`items:tuple[T],next_cursor:str?,has_more:bool`，不暴露数据库游标。
- 写操作需要operator；viewer可读其授权scope。MVP单工作空间、两角色；ActorContext由后端认证产生，不接受body自报actor。外网部署再接标准身份提供器，不发展复杂权限平台。
- 创建作业/提交/事件要求`Idempotency-Key`；key作用域actor+operation，保留至少24h，同body hash返回原回执，不同body409。更新使用`If-Match: row_version`；提交另有expected_active_version_id。
- `X-Request-ID`若有效可关联到trace，否则后端生成；响应trace_id；敏感信息不写日志。body默认上限2MiB，普通请求10s超时；作业预算服务端最大60s，Agent总预算默认60s。
- 202返回JobRef；GET作业返回执行状态，GET结果返回typed业务结果，排队/运行时结果查询409 RESULT_NOT_READY。已完成求解无解仍为有效result；绝不生成占位成功方案。
- 空集合返回200空页；资源不存在404；字段无效422；版本/资源冲突409；401/403/413/429/503及其余错误按DATA_CONTRACTS。无内部stack trace外泄。

## 端点表（operation_id按英文蛇形命名，实施时冻结）

| 方法与路径 | 请求 / 响应Schema | 应用服务与权限 | 交付 |
| --- | --- | --- | --- |
| GET /health；GET /ready | 无→HealthResponse / ReadinessResponse | 系统探针，最小公开信息 | P05-01 |
| GET /orders；GET /orders/{id} | OrderFilter+PageQuery→OrderPage / OrderDTO | MasterDataService，viewer | P05-02 |
| POST /orders；PATCH /orders/{id} | OrderCreate / OrderUpdate→OrderDTO（201/200） | draft/accepted规则，operator；执行中改需求走event | P05-02 |
| GET /vehicles；GET /vehicles/{id} | VehicleFilter→VehiclePage / VehicleDTO | MasterDataService，viewer | P05-02 |
| POST /vehicles；PATCH /vehicles/{id} | VehicleCreate / VehicleUpdate→VehicleDTO | operator，If-Match | P05-02 |
| GET /drivers；POST /drivers；PATCH /drivers/{id} | DriverQuery/DriverCreate/DriverUpdate→DriverPage/DriverDTO | viewer读/operator写 | P05-02 |
| GET /warehouses；GET /warehouses/{id} | WarehouseFilter→WarehousePage/WarehouseDTO | viewer | P05-02 |
| POST /warehouses；PATCH /warehouses/{id} | WarehouseCreate/WarehouseUpdate→WarehouseDTO | operator | P05-02 |
| GET/POST /warehouses/{id}/zones | ZoneQuery/ZoneCreate→ZonePage/ZoneDTO | viewer读/operator写 | P05-02 |
| GET/POST /warehouses/{id}/locations | LocationQuery/LocationCreate→LocationPage/StorageLocationDTO | viewer读/operator写 | P05-02 |
| GET/POST /warehouses/{id}/docks | DockQuery/DockCreate→DockPage/DockDTO | viewer读/operator写 | P05-02 |
| GET/POST /warehouses/{id}/workers | WorkerQuery/WorkerCreate→WorkerPage/WorkerDTO | viewer读/operator写 | P05-02 |
| GET/POST /warehouses/{id}/equipment | EquipmentQuery/EquipmentCreate→EquipmentPage/EquipmentDTO | viewer读/operator写 | P05-02 |
| PATCH /resources/{kind}/{id}；GET/PUT /resources/{kind}/{id}/calendar | ResourceUpdate判别联合 / CalendarDTO→ResourceDTO / CalendarDTO | PATCH kind白名单zone/location/dock/worker/equipment；calendar仅location/dock/worker/equipment，operator写 | P05-02 |
| GET /jobs/{id}；POST /jobs/{id}/cancel | 无 / CancelCommand→JobView | JobService，所属scope；operator取消 | P05-03 |
| GET /jobs/{id}/result | 无→JobResult判别union | ResultService，viewer | P16-01 |
| POST /optimizations/transport | TransportRequestDTO→JobRef，202 | OptimizationService，operator | P16-01 |
| POST /optimizations/warehouse | WarehouseRequestDTO→JobRef，202 | OptimizationService，operator | P16-01 |
| POST /optimizations/joint | JointPlanningRequest→JobRef，202 | JointPlanningService，operator | P16-02 |
| POST /reschedules | RescheduleRequestDTO→JobRef，202 | RescheduleService，operator | P16-01 |
| GET /reschedules/{id} | 无→RescheduleResultView | RescheduleService，viewer | P16-01 |
| POST /events；GET /events；GET /events/{id} | EventEnvelope / EventQuery→EventReceipt / EventPage / EventView | EventService，operator写、viewer读 | P13-02 |
| GET /exceptions；GET /exceptions/{id} | ExceptionFilter→ExceptionPage/ExceptionView | ExceptionService，viewer | P16-01 |
| POST /exceptions/{id}/analyze；GET /exceptions/{id}/impact | AnalyzeCommand→ImpactReport | ImpactService，operator计算/viewer读 | P16-01 |
| GET /schedules；GET /schedules/{id}/versions；GET /schedules/{id}/versions/{version_id} | ScheduleQuery→SchedulePage/VersionPage/ScheduleVersionDTO | ScheduleService，viewer | P16-03 |
| GET /candidates/{id}；POST /candidates/{id}/validate | 无 / ValidateCommand→CandidatePlanDTO / ValidationReport | ScheduleService，viewer读/operator校验 | P16-03 |
| POST /schedules/{id}/versions/commit | CommitCommand→CommitReceipt，201（幂等重放200） | ScheduleService，operator；Agent调用额外确认令牌 | P16-03 |
| GET /schedules/{id}/diff?base_version_id=...&candidate_id=... | DiffQuery→ScheduleDiff | ComparisonService，viewer；同schedule | P16-04 |
| GET /scenarios；GET /scenarios/{id} | ScenarioQuery→ScenarioPage/ScenarioBundle | ScenarioService，viewer；不执行脚本 | P16-04 |
| POST /simulations；GET /simulations/{id} | SimulationRequestDTO→JobRef / SimulationView | SimulationService，operator写/viewer读 | P16-04 |
| POST /simulations/{id}/control | SimulationControl→SimulationView | SimulationService，operator；控制命令持久化 | P16-04 |
| GET /simulations/{id}/snapshots；GET /simulations/{id}/events | CursorQuery→SnapshotPage/ExecutionEventPage | viewer | P16-04 |
| POST /simulations/{id}/fork | ForkCommand(snapshot_id,changes:ScenarioChange[])→JobRef | operator，新分支 | P16-04 |
| POST /agent-runs；GET /agent-runs/{id} | AgentRequest→AgentRunRef / AgentRunView | AgentService，operator发起、所属scope读 | P23-02 |
| POST /agent-runs/{id}/messages；POST /agent-runs/{id}/cancel | UserMessage / CancelCommand→AgentRunView | AgentService，operator | P23-02 |
| POST /agent-runs/{id}/confirmation-token | ConfirmationRequest(candidate_id,candidate_hash,expected_revision)→ConfirmationTokenView | 明确用户确认动作、operator；模型工具不暴露此端点 | P23-02 |
| POST /agent-runs/{id}/confirm | ConfirmAgentDecision(token,cmd)→CommitReceipt | AgentService转ScheduleService，原子消费绑定令牌 | P23-02 |
| WS /ws；GET /changes?after_seq=... | RealtimeEnvelope / ChangePage | 同scope授权，WS Origin校验；不以URL传密钥 | P31-01 |
| GET /metrics；GET /dashboard | MetricQuery→MetricSet / DashboardView | MetricsService，viewer；这里/metrics带/api/v1 | P32-02 |
| POST /experiments；GET /experiments；GET /experiments/{id}/results | ExperimentSpec→JobRef / ExperimentPage / ExperimentResultBundle | operator创建、viewer读 | P33-02 |
| GET /experiments/{id}/export?format=json\|csv | ExportQuery→受控文件内容 | viewer；formula injection转义，下载路径非用户任意路径 | P33-02 |
| GET /audit?trace_id=... | AuditQuery→AuditPage | operator；分页与脱敏 | P37-02 |
| GET /metrics（无/api/v1前缀） | 无→PrometheusText | 内网运维身份；与业务指标API区分 | P37-02 |

额外的Filter/Create/Update/View为对应领域DTO的明确投影，不允许任意Patch dict；必须在API实现任务中具名定义、extra=forbid，导出OpenAPI。禁止通用`set_status`接口跳过状态机。API生产环境仅暴露已实现能力，未启用模块返回明确unsupported。

## Agent工具白名单与角色

| ToolName | 请求→响应 | 可调用角色 | Effect |
| --- | --- | --- | --- |
| read_snapshot | PlanningScope→PlanningSnapshotView（按角色最小字段） | 四角色 | read |
| submit_transport | TransportRequestDTO→JobRef | Coordinator、Transport | propose |
| submit_warehouse | WarehouseRequestDTO→JobRef | Coordinator、Warehouse | propose |
| submit_joint | JointPlanningRequest→JobRef | Coordinator | propose |
| get_job | JobQuery→JobView/JobResult | 四角色，限本run关联 | read |
| validate_candidate | CandidateRef→ValidationReport | 四角色，限scope | read |
| analyze_impact | AnalyzeCommand→ImpactReport | Coordinator、Exception | read |
| submit_reschedule | RescheduleRequestDTO→JobRef | Coordinator、Exception | propose |
| compare_versions | DiffQuery→ScheduleDiff | Coordinator、Exception | read |
| start_simulation | SimulationRequestDTO→JobRef | Coordinator | propose（隔离分支） |
| commit_schedule | CommitCommand+ConfirmationToken→CommitReceipt | Coordinator，且actor=operator | commit |

标准ToolContext包含actor、role、run_id、trace_id、deadline与shared_budget。授权取actor权限、角色白名单和对象scope交集；来自用户文本、工具输出或模型的“我已获批准”均不能提升权限。ToolExecutor只调用业务ServiceBundle，不获得数据库会话、SQL工具、文件写工具或任意HTTP能力。

## 一次完整请求顺序

创建结构化请求→202 JobRef→worker求解→GET job/result→GET candidate+validation→用户确认→POST commit(candidate_hash,expected_active_version_id)→事务返回version_no→outbox推送。自然语言入口在之前增加澄清和Tool调用；最后确认仍经过同一业务服务。WebSocket只通知变更，HTTP读模型与数据库是最终状态来源。


## N01-R01 主数据具名投影

本节为本轮新增设计决定；P05-02 contracts.http承载这些边界，实体DTO仅复用P02-02 contracts.entities。全部HTTP body带schema_version=2.0.0，extra=forbid；具体实体DTO逐字段映射DOMAIN共同字段及对应行，不额外自造实体。Create没有id/status/created_at/updated_at/row_version/created_by，服务按既有初态产生；PATCH禁止通用set_status，至少一个mutable字段，缺字段保持、null只对原契约可空字段合法。父warehouse取path且内部zone等必须属于该warehouse，不接受body改scope。If-Match是header，不复制到body。

| Create Schema | 精确业务字段（其余拒绝） | 关系/空值 |
| --- | --- | --- |
| CargoCreate | cargo_type, quantity_units, weight_g, volume_cm3, min_temp_decic, max_temp_decic, max_exposure_s, batch_ref | 类型/空值继承Cargo对应字段；父path字段无 |
| OrderCreate | external_ref, pickup_node_id, delivery_node_id, pickup_window, delivery_window, service_s, soft_due_at_s, must_serve, priority, cargo:CargoCreate[] | 类型/空值继承Order对应字段；父path字段无 |
| VehicleCreate | code, capacity_weight_g, capacity_volume_cm3, setpoint_decic, allowed_cargo_types, start_node_id, end_node_id, calendar, driver_id, fixed_cost_cents, rate_cents_per_km | 类型/空值继承Vehicle对应字段；父path字段无 |
| DriverCreate | code, qualifications, shift, max_drive_s, max_work_s | 类型/空值继承Driver对应字段；父path字段无 |
| WarehouseCreate | code, name, node_id, timezone, calendar | 类型/空值继承Warehouse对应字段；父path字段无 |
| ZoneCreate | code, setpoint_decic, capacity_weight_g, capacity_volume_cm3, allowed_cargo_types | 类型/空值继承WarehouseZone对应字段；父path字段warehouse_id |
| LocationCreate | zone_id, code, capacity_weight_g, capacity_volume_cm3, calendar | 类型/空值继承StorageLocation对应字段；父path字段无 |
| DockCreate | code, supported_operations, allowed_zone_ids, calendar | 类型/空值继承Dock对应字段；父path字段warehouse_id |
| WorkerCreate | skills, allowed_zone_ids, calendar, pool_id | 类型/空值继承Worker对应字段；父path字段warehouse_id |
| EquipmentCreate | kind, quantity_capacity, allowed_zone_ids, calendar | 类型/空值继承Equipment对应字段；父path字段warehouse_id |

OrderCreate.cargo非空，CargoCreate不含order_id，由同一事务生成Order/Cargo ID并填双向FK；任一失败全部回滚。不得改为悬空cargo_ids或假设另一未登记Cargo端点。ZoneCreate不含warehouse_id；LocationCreate.zone_id必须属于path warehouse；其他仓储Create由path填warehouse_id。

| Update Schema | 精确可修改字段 | 规则 |
| --- | --- | --- |
| OrderUpdate | external_ref, pickup_node_id, delivery_node_id, pickup_window, delivery_window, service_s, soft_due_at_s, must_serve, priority | 缺省保持；仅原nullable可null；至少一字段 |
| VehicleUpdate | code, capacity_weight_g, capacity_volume_cm3, setpoint_decic, allowed_cargo_types, start_node_id, end_node_id, calendar, driver_id, fixed_cost_cents, rate_cents_per_km | 缺省保持；仅原nullable可null；至少一字段 |
| DriverUpdate | code, qualifications, shift, max_drive_s, max_work_s | 缺省保持；仅原nullable可null；至少一字段 |
| WarehouseUpdate | code, name, node_id, timezone, calendar | 缺省保持；仅原nullable可null；至少一字段 |
| ZoneUpdate | code, setpoint_decic, capacity_weight_g, capacity_volume_cm3, allowed_cargo_types | 缺省保持；仅原nullable可null；至少一字段 |
| LocationUpdate | code, capacity_weight_g, capacity_volume_cm3 | 缺省保持；仅原nullable可null；至少一字段 |
| DockUpdate | code, supported_operations, allowed_zone_ids | 缺省保持；仅原nullable可null；至少一字段 |
| WorkerUpdate | skills, allowed_zone_ids, pool_id | 缺省保持；仅原nullable可null；至少一字段 |
| EquipmentUpdate | kind, quantity_capacity, allowed_zone_ids | 缺省保持；仅原nullable可null；至少一字段 |

OrderUpdate仅draft修改需求，cargo数量变更用既有事件协议而非替换FK；执行中变更走事件。ResourceUpdate为kind/changes五分支，MasterDataUpdate为entity_kind/entity_id/changes九分支，changes严格匹配对应Update；MasterDataView为同entity_kind/value九分支，映射对应具名DTO。Equipment内部kind与Resource包装kind分层；日历五资源只走PUT calendar，Vehicle/Warehouse专属Update可映射日历。取消body复用CancelCommand schema字段，但Job/Agent path分别映射自己的状态机，不共用写副作用。

PageQuery(cursor:str|null=null,limit:int=50)，1..200；Filter/Query继承它，精确过滤字段如下，字段type/null来自对应实体DTO，status唯一共享枚举，未提供不过滤；不接受自由过滤表达式。

| 查询类型 | 唯一元素来源 | 精确可选过滤字段 |
| --- | --- | --- |
| OrderFilter | OrderDTO | status, external_ref |
| VehicleFilter | VehicleDTO | status, code, driver_id |
| DriverQuery | DriverDTO | status, code |
| WarehouseFilter | WarehouseDTO | status, code |
| ZoneQuery | ZoneDTO | status, code |
| LocationQuery | StorageLocationDTO | status, code, zone_id |
| DockQuery | DockDTO | status, code |
| WorkerQuery | WorkerDTO | status, pool_id |
| EquipmentQuery | EquipmentDTO | status, kind |

OrderPage/VehiclePage/DriverPage/WarehousePage/ZonePage/LocationPage/DockPage/WorkerPage/EquipmentPage全部为schema_version/items:tuple[对应DTO]/next_cursor:null或str/has_more。has_more等于next_cursor非空，空页null/false。PagePosition完整字段见DATA表，version=1，编码canonical JSON后base64url，最大2048字符；绑定scope/entity_kind/filter_hash和after(created_at,id)，filter hash排除cursor/limit，严格升序且下一页strict>cursor。未知版本/字段、错误scope/filter/type或无效编码422；游标不替代认证。正常同created_at按ID分页每项一次；反例limit201、空PATCH、status自报、service_s=null、跨过滤cursor、If-Match旧值均拒绝。

JobRequest是早期完整JobCommand映射，API能力生产者先以自己严格DTO解析，再保存不可变内容封装引用；GET result仍typed能力union，RESULT_NOT_READY/409明确错误映射。JobView不含内部租约或秘密。场景GET只返回严格ScenarioBundle，不合并测试invalid_cases.json期望。readiness必须真实依赖探针；本轮没有业务HTTP/DB实跑。
