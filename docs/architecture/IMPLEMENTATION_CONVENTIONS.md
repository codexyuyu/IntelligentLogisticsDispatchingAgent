# 实现约定、内部接口与接线

这些约定是为避免后续Coding Agent猜测模块接线，属于Architecture Contract 2.0.0。只描述待实现结构，本轮不创建应用代码。

## 包和入口

根级`pyproject.toml`为uv workspace；Python3.12，包路径`packages/<name>/src/logistics_<name>`，backend在`apps/backend/src/logistics_backend`。在根目录`uv run pytest ...`能导入所有workspace包，dev依赖含pytest/ruff/类型检查与必需集成测试工具。`package.json`为npm workspace，前端位于apps/frontend；根脚本`test:e2e`调用Playwright，前端脚本`test`调用Vitest、`build`执行类型检查和Vite构建、`contracts:generate/check`处理OpenAPI类型。Phase01锁文件必须真实安装生成，不手写假锁。

测试目录由根pytest配置统一发现，`tests/conftest.py`提供隔离PostgreSQL连接、事务/worker fixture；没有TEST_DATABASE_URL则相关集成测试明确未运行，Gate拒绝关键skip。测试可共用固定输入数据，不能共用solver内部规则作为独立oracle。Windows命令用当前项目锁定环境，不假定Unix shell；P01环境手册给出Docker PostgreSQL与本地PostgreSQL两种明确启动方式，不能隐式连接个人数据库。

## 早期类型图与模块内上下文

P02先定义所有实体以及它们直接引用的纯值类型，Schema能立即导出；后续Phase的“Domain”指更具体Problem/Request组装与业务算法，不能重新定义Order/Vehicle/TwinState。

| 类型 / 所有文件 | 最小字段与使用限制 |
| --- | --- |
| ResourceBundle / domain.resources | warehouses/zones/locations/docks/workers/equipment均为各自tuple；calendars绑定resource_id和version |
| TransportPlan / domain.planning | routes:tuple[Route]; unserved_order_ids:tuple[UUID]; cost:CostBreakdown；只存纯业务结构 |
| WarehousePlan / domain.planning | assignments:tuple[OperationAssignment]; storage_intervals:tuple[StorageInterval]; setup_operations:tuple[SetupOperation]; cost:CostBreakdown |
| JointProblem / domain.joint（P08-02） | transport:TransportProblem; warehouse:WarehouseProblem; handoffs:tuple[HandoffConstraint]; boundary:RescheduleBoundary or None; policy:JointPolicy(max_rounds=3,max_warehouses_per_order=2)；boundary字段使用P02完整定义的冻结计划值对象，P14只实现提取，不重复定义 |
| JointPlanningSolver / domain.ports.joint（P08-02） | solve(problem:JointProblem,budget:SolveBudget)->JointCandidateSolution(status,candidate,validation,rounds)；P15-02在optimization.coordination.joint实现纯窗口反馈kernel，P16服务复用；局部与正常联合不能维护两套反馈算法 |
| ExecutionLocation / domain.execution | at_node(node_id) 或 on_arc(from_node_id,to_node_id,departed_at_s,expected_arrival_s,progress_numerator,progress_denominator)，判别联合 |
| ExecutionSnapshot / domain.execution | id/time_s、TwinState、source_version_id、资源修订向量、content_hash；t由同一事实边界定义 |
| RoutingModelContext / optimization.transport.base_model | manager:RoutingIndexManager; routing:RoutingModel; node_bindings:tuple[NodeIndexBinding]; vehicle_bindings:tuple[VehicleIndexBinding]; dimensions:RoutingDimensions; callbacks:tuple[RegisteredCallback]。仅optimization.transport内部使用，不穿API/Agent/Simulation |
| NodeIndexBinding / 同上 | node_id:UUID; external_position:int; routing_index:int; stop_kind:RoutingNodeKind；起终点同业务节点可有不同routing_index，禁止一ID只存一个index导致覆盖 |
| RoutingDimensions / 同上 | time:RoutingDimension or None; weight:RoutingDimension or None; volume:RoutingDimension or None；未添加的构件显式None，只能在adapter内部阶段组装使用 |
| WarehouseModelContext / optimization.warehouse.intervals | model:CpModel; task_vars:tuple[OperationVars]; resource_vars:tuple[ResourceVars]; setup_arcs:tuple[SetupArcVars]；仅warehouse内部 |
| OperationVars / 同上 | task_id、start/end整数变量、assignments:tuple[ResourceAssignmentVars]；每assignment含resource_id/presence/optional_interval |
| ResourceVars / 同上 | resource_id、base_capacity、assigned_interval_refs、calendar_blocker_refs；同质池和具名独占资源分别描述 |
| ToolContext / agents.tools.protocol | actor:ActorContext; agent_role:AgentRole; run_id; trace_id; deadline; budget:SharedBudgetHandle；不得包含db_session或SQL执行器 |
| ServiceBundle / backend.agent_tools | snapshot_service、optimization_service、joint_planning_service、reschedule_service、schedule_service、simulation_service、job_service、impact_service、comparison_service；全为具名Protocol字段，禁止任意dict定位服务 |
| MetricValue / domain.runtime | code、definition_version、source、unit、value:number or None、numerator:number or None、denominator:number or None、reason:MissingReason or None、sample_count |
| ScenarioSpec / domain.runtime | 完整schema/id/version/generator_version/seed/epoch/horizon/size/policy/events及独立输入按DATA本轮决定；唯一events在spec；生成策略枚举而非可执行脚本字符串 |
| DemoEvidence / scripts.demo_support | scenario_ref、input_hash、commands、result_refs、validation_reports、base/new_version_refs、event_log_ref、snapshot_refs、diff_ref、metrics_ref、environment、outcome；不包含预制成功方案 |

模块内部可以为高效索引使用已标注key/value类型的`Mapping[UUID, T]`，但不得作为未经Schema定义的跨模块消息；以上表格选tuple使序列化顺序可控。OR-Tools对象只在同一solver adapter内部，纯domain ports输入输出始终无引擎类型。

冷链额外数据：所有可能暴露环节（装/卸、等待、救援）须有`ThermalSegment(controlled:bool, start_s,end_s, measured_temp_decic?:int)`，实际事件或已验证作业资源给出controlled；货物累计不受控时长不得超过Cargo.max_exposure_s。T1普通路段/服务默认显式controlled=true，暴露0；救援例交接60秒为uncontrolled且上限120。未知controlled不能默默按true；需此规则但信息不足返回unsupported/manual_required，不引入高精度热模型。

## 组合根与HTTP路由

`bootstrap.py`唯一实例化数据库adapter、solver、SimPy、LLMProvider并注入application服务。`api/router.py`只注册已实现的FastAPI router，路由函数通过dependencies取服务；不得在router里构造solver。每个API新增任务的Files包含bootstrap/router和生成OpenAPI，允许仅做该能力的接线。未完成能力在注册表显式disabled，不能装配fake成功adapter。

P02 `scripts/export_contracts.py`先导出types JSON Schema；P05-01增加已实现app的OpenAPI导出。`--check`只比较当前能够生成的产物，未启用未来路由不应导致P02导出失败。P24后任何API变化都同步生成TS；生成文件不能手改。

## 前端注册与并行范围

P24在router固定11个URL及它们的feature module路径，使用Vite构建期`import.meta.glob('./features/**/Page.tsx')`发现已存在页面；每个模块导出default Page，缺失模块显示明确未启用视图。不得在壳阶段创建假业务实现，也不能直接import尚不存在的Page导致编译失败。

页面路径：dashboard、orders、vehicles、warehouses、transport、warehouse-scheduling、simulation、exceptions、agent-chat、metrics、experiments。各页面内部组合本feature组件。P25三页无需同时编辑公共router，因此可独立执行；P26等后续细化视图任务显式允许修改本feature/Page.tsx；P31只在App接统一实时订阅。公共API层和枚举不在页面自行扩展。

## 文件变更与证据

P00-01另外输出`BASELINE_INVENTORY.json`，格式`{schema_version, entries:[{source_path,sha256,target_path,owner,disposition,capability_evidence}]}`；source_path为仓库内实际旧文件相对路径，owner=A/B，disposition=reference/reuse/adapt/rewrite，至少覆盖demo/README、DEV_LOG、OWNERSHIP、contracts/README及backend/app/contracts下的实际源码。P00-02输出`CONTRACT_FREEZE.json`，格式`{schema_version,plan_version,reviewed_at,reviewer,unresolved_blocking_issues:[],artifacts:[{path,sha256}]}`，覆盖Master、TaskGraph、架构总览、Domain/Data/Internal接口、API、三份算法契约、测试fixture和Gate协议。规划检查器核对实际hash，不接受只写一句架构已冻结。

任务Files为预期白名单，包括精确实现文件、测试、必要接线与专属报告。禁止把`packages/**`当通用写许可。新增只用于包导出的`__init__.py`需在报告逐一列明，不能引入新业务API。阻断契约问题按changes/issue流程做最小迁移；非阻断不扩Scope。共享文档统一在契约变更任务集成，普通任务只写专属implementation文档避免写冲突。

TASK_MANIFEST中的planned/not_run是这份规划的初始状态，不作为新的实时项目管理系统；未来实际完成状态以任务报告、有效Gate证据及已有外部任务系统为准。不要为了标done改机器清单并破坏规划校验。修改规划本身时，应改catalog/render源、重新生成、静态检查，并单独记录计划版本变更。


## N01-R01 早期配置与HTTP闭包

以下为本轮设计决定，完整字段见[规范JSON附表](../../contracts/changes/N01-R01-contract-decisions.json)与[DATA字段表](DATA_CONTRACTS.md#规范具名定义与字段附表)。不是已经实施的源码类。

- ImportCount(entity_kind,inserted,unchanged)与ImportReceipt(schema_version,scenario_ref,status,counts,inserted,unchanged,error)唯一P04-02 cli/seed.py。kind不重复；顶层计数等于分项和；imported inserted>0/error=null，no_change inserted=0/error=null，rejected counts空且全部计数0/error非空/CLI非零。FK失败全事务回滚，不把暂存计数写成提交成功；相同ID/version不同hash409 IDEMPOTENCY_CONFLICT；不包含连接串/原请求/stack。scenario_ref已包含dataset_version，不复制另一个字符串版本字段。
- SecretValue 是bootstrap内部红acted秘密值包装（底层str，repr/序列化固定遮罩，公开API无此类型）；Settings和CredentialGrant唯一P05-01 bootstrap.py。全部核心字段按DATA表，默认bind_host=127.0.0.1、bind_port=8000、max_body_bytes=2097152、request_timeout_s=10；开发/测试限loopback，端口1..65535，body/timeout可下调不可超契约上限。database_url必需PostgreSQL、scope UUID必需、credentials映射可信actor/两角色，token只存64hex SHA256且不可重复/不得装配默认凭据。未知配置字段拒绝，SecretValue不可写日志或响应；未启用未来adapter不导入其配置类型。无必需配置启动失败；DB不可达实际ready503，不能按URL存在宣称ready。
- HealthResponse(schema_version,status=alive)只说明进程活着，200；ReadinessResponse(schema_version,status,database,trace_id)来自真实有时限DB探针，available→ready/200，否则not_ready/503。没有秘密/DB URL/完整环境指纹，未跑探针不允许ready结论。本轮并未运行DB或模型smoke。
- P02-04 execution先定义EventPayload十类及ExecutionLocation等纯值；runtime引用execution/scenario/job；不得execution导入runtime。P03消费所有早期完整类型。JobRequest映射JobCommand在P02-04 contracts.runtime首次定义；P05只能复用，不重复声明。CalendarDTO在P02-02 entities首次映射；HTTP只复用。P16-01精确白名单由catalog补contracts.runtime，仅映射已有业务结果且不重新定义JobResultRef。
- 主数据Create/Update/Filter/Page唯一P05-02 http具名投影；MasterDataView是entity_kind/value九个具名响应包装，update返回的branch与command.entity_kind一致。ResourceDTO仍只有五类资源，Vehicle/Driver/Warehouse独立DTO。Schema导出先依早期types，后OpenAPI和TS，无未来路由导入。

内部合法示例：ImportCount order1/cargo1→inserted2；同hash二次no_change/0。违规：分项2但总3、rejected仍inserted1、no_change带error拒绝。设置合法loopback/有效显式凭据/隔离DB URL仅代表配置可解析；DB未通却ready200、明文SecretValue日志、development绑定公网、缺scope/重复token hash均拒绝。测试必须在原任务验证实际行为，本轮文档检查不冒称环境通过。
