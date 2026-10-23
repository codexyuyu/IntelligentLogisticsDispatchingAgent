"""Planning metadata only. Does not implement or execute logistics business code."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
PLAN_VERSION = '1.0.3'
GENERATED_DATE = '2026-10-03'
TASKS = []
PHASES = [
    '需求冻结与 Architecture Contract','Monorepo 与工程基础','Domain Model',
    'PostgreSQL Schema + Migration','Seed / Synthetic Dataset','FastAPI 基础服务',
    'Transport Optimization Domain','Transport Solver','Warehouse Optimization Domain',
    'Warehouse Scheduler','Constraint Validator','Simulation Domain','SimPy Digital Twin',
    'Event Engine','Exception Impact Analyzer','Local Rescheduling Engine','Optimization API',
    'Agent Tool Protocol','LLM Provider Abstraction','Coordinator Agent','Transport Agent',
    'Warehouse Agent','Exception Agent','Agent Orchestration','React Application Shell',
    'Orders / Vehicles / Warehouses UI','Transport Scheduling UI','Warehouse Scheduling UI',
    'Digital Twin UI','Exception Center UI','Agent Chat UI','WebSocket Real-time System',
    'Metrics / Evaluation','Experiment Framework','End-to-End Integration','Demo Scenario',
    'Performance Optimization','Security / Audit / Observability','Documentation','Release',
]

def add(p, slug, title, files, interface, model, rule, algorithm, cases, after='chain', kind='python'):
    number = sum(t['phase'] == p for t in TASKS) + 1
    task_id = f'P{p:02d}-{number:02d}'
    prior = [t for t in TASKS if t['phase'] == p]
    deps = ([prior[-1]['id']] if prior else []) if after == 'chain' else list(after)
    TASKS.append(dict(id=task_id, phase=p, slug=slug, title=title, files=files.split(';'),
        interface=interface, model=model, rule=rule, algorithm=algorithm,
        cases=cases.split(' / '), deps=deps, kind=kind))

add(0,'baseline-inventory','登记旧 demo 资产与目标目录迁移映射',
    'docs/architecture/BASELINE_INVENTORY.md;docs/architecture/BASELINE_INVENTORY.json;docs/architecture/MIGRATION_MAP.md',
    'BaselineInventory(source_path, sha256, owner, capability, disposition) -> MigrationMap',
    '旧 v0.1 contracts、ports、展示页面、A/B 所有权',
    '只读检查 demo；501 和教学探针不计为正式求解实现；不得改 Linear 状态。',
    '列出路径、当前能力证据、保留/迁移/重写分类；B 映射到运输与仿真路径；转换差异登记。',
    'demo 的业务骨架返回 501 => 记录未实现 / 同一源文件两条目标主契约 => 检查失败',kind='docs')
add(0,'freeze-contracts','冻结单位、职责、错误和接口契约',
    'docs/architecture/CONTRACT_FREEZE.md;docs/architecture/CONTRACT_FREEZE.json;docs/architecture/issues/README.md',
    'ContractFreeze(version="2.0.0", decisions, source_hashes) -> FreezeRecord',
    '全部领域实体、Schema、Protocol',
    '冻结本包 DOMAIN_CATALOG、DATA_CONTRACTS、API_CONTRACT、OPTIMIZATION_CONTRACT；不另写冲突接口。',
    '核对需求到定义映射；明确批准设计与真实代码完成不同；存在阻断矛盾先记录 issue 并阻止 Gate。',
    'duration=1.5 秒 => 整数时间契约拒绝 / 旧分钟输入 2 => 显式转换成 120 秒且记录旧版本',kind='docs')
add(0,'gate-contract','核验任务 DAG 与失败关闭的 Gate 规则',
    'docs/plan/GATE_EXECUTION_CONTRACT.md',
    'GateEvidence(phase, revision, commands, exit_codes, artifact_hashes) -> GateDecision',
    'TaskManifest、GateEvidence、需求追踪矩阵',
    '规划静态校验通过不等于 G00 业务签收；后续 Gate 缺证据/跳过测试均失败。',
    '校验 DAG、反向阻塞边、文件范围、40 个 Gate 和每项需求；写阶段证据签收字段与失效传播。',
    '依赖 P99-01 => 检查失败 / G00 缺少命令退出码 => 不允许 P01 启动',kind='docs')

add(1,'workspace-bootstrap','建立目标 Monorepo 与可复现依赖环境',
    'pyproject.toml;package.json;apps/backend/pyproject.toml;apps/frontend/package.json;packages/domain/pyproject.toml;packages/contracts/pyproject.toml;packages/optimization/pyproject.toml;packages/simulation/pyproject.toml;packages/agents/pyproject.toml;packages/evaluation/pyproject.toml;uv.lock;package-lock.json;.python-version;.node-version',
    'workspace install -> import logistics_domain, logistics_contracts, logistics_optimization, logistics_simulation, logistics_agents, logistics_evaluation',
    '包依赖图和迁移映射',
    'Python 3.12、Node 22 作为兼容基线而非最新版本承诺；精确锁版本并实际安装；不搬走或删除 demo。',
    '使用 uv workspace 和 npm workspace，src-layout；模块 public __init__ 仅导出；记录已验证的工具版本。',
    '干净环境 uv sync --frozen => 成功导入六包 / npm ci 重复执行 => 锁文件无变化')
add(1,'checks-and-gate-runner','建立分层检查、CI 与阶段证据执行器',
    'scripts/gates.py;scripts/check_architecture.py;.github/workflows/ci.yml;tests/conftest.py;apps/frontend/vitest.config.ts;apps/frontend/src/test/setup.ts',
    'python scripts/gates.py --phase NN --revision REV -> artifacts/gates/GNN.json',
    'GateEvidence、import boundary rules',
    'Gate 读取 manifest 要求命令并亲自执行；失败不得写 passed；不接受用户手填成功；原始日志与哈希必须保存。',
    '运行各任务命令及阶段附加验收，核验前 Gate 与证据依赖；用子进程参数数组；提供 --check-only 与过期检查。',
    '命令 exit=1 => G01 failed 且进程非零 / domain 导入 fastapi => 层边界检查失败 / 缺少 Codex review 或 ZCode 输入哈希过期 => G01 failed 且进程非零 / --check-only => 不写 Gate 记录或日志，已有记录保持原字节')
add(1,'migration-governance','建立新路径所有权及旧契约转换验收入口',
    'OWNERSHIP.json;docs/architecture/LEGACY_ADAPTATION.md;contracts/changes/README.md;scripts/check_ownership.py',
    'resolve_owner(path: str) -> Literal["A", "B"]',
    'OwnerRule、LegacyMapping',
    '新根级工程是唯一正式目标；旧 demo 保持只读基线；仅在未来对应任务复用已验收逻辑，不装配旧占位适配器。',
    '最长路径前缀决定 owner；B=transport/matrix/simulation 与对应测试，其余 A；列明 v0.1 命名、单位、枚举转换。',
    'packages/simulation/src/logistics_simulation/engine.py => B / 未映射 v0.1 状态 => 明确拒绝而非猜测')

add(2,'primitives-and-states','实现领域 ID、单位与唯一状态枚举',
    'packages/domain/src/logistics_domain/primitives.py;packages/domain/src/logistics_domain/states.py;packages/domain/src/logistics_domain/errors.py',
    'TimeWindow(earliest_s: int, latest_s: int); transition(state: EntityState, event: Transition) -> EntityState',
    '所有 ID / Enum、TimeWindow、Money、ViolationCode、CalendarInterval、ResourceCalendar、JobKind、JobStatus、JobOptimizationMode',
    'UUID、UTC 时间、整数秒/米/克/立方厘米/分/十分之一摄氏度；资源占用 [start,end)；服务开始窗闭区间。 JobStatus/JobKind/JobOptimizationMode唯一在states.py定义；JobKind序列化值固定optimization/simulation/reschedule/experiment/metric，优化mode固定transport/warehouse/joint，JobStatus保留queued/running/completed/failed/cancelled。CalendarInterval与ResourceCalendar唯一在primitives.py完整定义，calendar必填epoch_utc/version/intervals；P02-02直接引用，不在resource/DTO重复定义。按N01-R01本轮决定及contracts/changes/N01-R01-contract-decisions.json实施。',
    '不可变值对象；按实体状态转换表显式校验；错误只用领域类型，不依赖 Pydantic。',
    '[0,10) 和 [10,20) => 不冲突 / delivered -> draft => INVALID_TRANSITION / JobKind=simulation与JobOptimizationMode=transport各自序列化 => 固定唯一值 / JobKind=routing => 拒绝未知枚举 / CalendarInterval(start_s=10,end_s=10) => 拒绝 / calendar缺epoch_utc => 拒绝')
add(2,'master-entities','实现订单、货物与运仓资源领域模型',
    'packages/domain/src/logistics_domain/orders.py;packages/domain/src/logistics_domain/resources.py;packages/contracts/src/logistics_contracts/entities.py',
    'OrderDTO.to_domain() -> Order; ResourceDTO.to_domain() -> Resource',
    'Order、Cargo、Vehicle、Driver、Warehouse、WarehouseZone、StorageLocation、Dock、Worker、Equipment；Resource五类kind/value联合、ResourceDTO、CalendarDTO',
    'cargo 属于唯一订单；车辆固定温控点须落在全部货物允许区间；资源版本必须非负。 Resource是zone/location/dock/worker/equipment五个具名kind/value分支，不新增独立资源实体；ResourceDTO在contracts/entities.py映射同一纯union；CalendarDTO同文件仅映射P02-01 ResourceCalendar(epoch_utc/version/intervals)，P05复用。按DATA_CONTRACTS及N01-R01本轮决定实现。',
    '依 DOMAIN_CATALOG 建纯实体与边界 DTO 映射，拒绝负容量及悬空关联；实体不查询数据库。',
    '需求 1001g 与车辆 1000g => 数据可表示、分配规则判容量违规 / cargo.temperature=[80,20] => 输入无效 / Resource(kind=worker,value=Worker) => 合法映射 / Resource(kind=worker,value=Dock) => 拒绝 / CalendarDTO与公共ResourceCalendar三字段逐项往返 => 同值')
add(2,'planning-entities','实现任务、版本与优化结果领域模型',
    'packages/domain/src/logistics_domain/planning.py;packages/contracts/src/logistics_contracts/planning.py',
    'ScheduleVersion(parent_version_id: UUID | None, snapshot_id: UUID, tasks: tuple[ScheduleTask,...])',
    'TransportTask、WarehouseTask、Route、RouteStop、Schedule、ScheduleTask、ScheduleVersion、Constraint、OptimizationRequest、OptimizationResult、RescheduleRequest、RescheduleResult',
    '稳定 task_id 与 version_id 分开；版本内容不可变；可行解状态与校验状态分别表达；优化结果绝不是确认。',
    '实现不可变计划聚合、状态和显式关联；版本 lineage 无环；result 无 incumbent 时 candidate 必须为空。',
    'status=TIMEOUT 且 candidate=null => 合法失败结果 / parent_version_id 指向自身 => 拒绝')
add(2,'runtime-contract-export','实现运行记录模型与 Schema 导出',
    'packages/domain/src/logistics_domain/runtime.py;packages/contracts/src/logistics_contracts/runtime.py;packages/contracts/src/logistics_contracts/common.py;scripts/export_contracts.py;contracts/schemas.json',
    'export_contracts() -> SchemaBundle; ErrorEnvelope(code, message, trace_id, details: tuple[ErrorDetail,...])',
    'Simulation、SimulationSnapshot、Event、ExceptionEvent、AgentRun、ToolCall、DecisionRecord、Experiment、Metric、ExperimentResult；辅助实体见目录',
    '边界 extra=forbid；discriminated union；业务 enum 只从 domain 引入；JSONB 也绑定 versioned schema。',
    '逐一映射运行实体；导出确定排序 JSON Schema；生成文件只由脚本更新并提供 --check。',
    'Event(kind=vehicle_failure,payload 缺 vehicle_id) => 校验失败 / 两次 export => 字节一致')

add(3,'resource-schema','创建主数据与资源迁移',
    'apps/backend/src/logistics_backend/persistence/resource_models.py;apps/backend/migrations/env.py;apps/backend/migrations/versions/0001_resources.py;alembic.ini',
    'alembic upgrade head -> PostgreSQL resource tables',
    'Order、Cargo、Vehicle、Driver、Warehouse、WarehouseZone、StorageLocation、Dock、Worker、Equipment',
    'FK、CHECK、唯一键、timestamptz、row_version；不使用 SQLite 代替正式数据库验收；历史被引用对象只停用。',
    '按关系拓扑建表；将领域约束中的可表达部分加入数据库；显式 enum/check 命名便于迁移。',
    'Cargo.order_id 不存在 => FK 拒绝 / warehouse_code 重复 => 唯一约束拒绝')
add(3,'planning-schema','创建不可变计划、运行与审计迁移',
    'apps/backend/src/logistics_backend/persistence/planning_models.py;apps/backend/src/logistics_backend/persistence/runtime_models.py;apps/backend/migrations/versions/0002_planning_runtime.py',
    'persist_version(version: ScheduleVersionDTO) -> VersionRef',
    '其余 22 个必需实体与 Job、Outbox、Idempotency、Reservation、PlanningSnapshot、InventoryLedger、AuditEntry',
    'ScheduleVersion 内容和审计追加不可覆盖；active_version_id 单独保存；唯一(schedule_id,version_no)；JSONB 有 schema_version。',
    '计划任务用 (version_id,task_id) 关联；金额 bigint；索引覆盖 job 状态、事件游标、parent_version_id；迁移往返检查。',
    '同 schedule 两个 version_no=2 => 拒绝 / 删除被 V1 引用的 Order => 拒绝')
add(3,'repositories-and-snapshot','实现快照读取与事务工作单元',
    'packages/domain/src/logistics_domain/ports/storage.py;apps/backend/src/logistics_backend/persistence/snapshots.py;apps/backend/src/logistics_backend/persistence/uow.py',
    'PlanningSnapshotStore.capture(scope: PlanningScope) -> PlanningSnapshot; UnitOfWork.commit() -> None',
    'PlanningSnapshot、ResourceRevision、InventoryLedger',
    'REPEATABLE READ 捕获一致快照；包含矩阵和日历版本；ORM 不传出 adapter。',
    '一次事务读取范围内实体与版本向量；规范化序列化计算 hash；DTO 映射到纯领域 snapshot。',
    '并发更新车容量 => 单一快照不混合新旧读 / UoW 内抛错 => 全部回滚')
add(3,'atomic-version-store','实现版本 CAS、资源预留与幂等存储',
    'apps/backend/src/logistics_backend/persistence/version_store.py;apps/backend/src/logistics_backend/persistence/reservations.py;apps/backend/src/logistics_backend/persistence/idempotency.py',
    'PlanCommitStore.commit(cmd: CommitCommand, report: ValidationReport) -> CommitReceipt',
    'ScheduleVersion、Reservation、Idempotency、Outbox、AuditEntry',
    '此阶段只测试存储事务，尚不得公开正式提交路由；校验报告必须匹配候选与快照 hash。',
    '固定顺序锁资源行，复核版本和时段容量，CAS active_version，原子写新版本/预留/审计/outbox；相同 key 同 hash 返回原 receipt。',
    '两个事务争最后 1 个 dock => 恰好一方成功 / 同幂等 key 不同 body => IDEMPOTENCY_CONFLICT')

add(4,'canonical-fixtures','生成可手算的合成场景与反例数据',
    'data/scenarios/manifest.json;data/scenarios/tiny_transport.json;data/scenarios/tiny_warehouse.json;data/scenarios/invalid_cases.json;scripts/generate_scenarios.py',
    'generate_scenario(spec: ScenarioSpec, seed: int) -> ScenarioBundle',
    'ScenarioSpec、订单/资源/矩阵/任务依赖、expected invariants',
    '使用 docs/plan/TEST_FIXTURES.md 精确数据；明确 synthetic；UUID 用稳定 uuid5；不可把期望方案装入运行实现。',
    '按独立 RNG 生成并规范序列化；正例经手算 oracle、反例标注唯一触发规则；保存 seed/schema/hash。',
    'tiny_transport => 最短距离 9000m / 同 seed=42 同 generator version => 文件 hash 一致')
add(4,'database-seed','实现可重复执行的数据库种子导入',
    'apps/backend/src/logistics_backend/cli/seed.py;data/seed/README.md',
    'python -m logistics_backend.cli.seed --scenario tiny_transport --database-url-env TEST_DATABASE_URL',
    'ScenarioBundle、ImportReceipt',
    '仅显式测试/演示库；禁止默认清空数据库；fixture ID 稳定；已有关联事实不得被覆盖。',
    '验证 schema/hash 后事务插入；已有相同 hash 返回 no_change；内容变化要求新 dataset_version。',
    '同数据导入两次 => 第二次 inserted=0 / 第二个对象 FK 无效 => 本次全回滚')

add(5,'api-composition','建立 FastAPI 组合根、错误协议与基础鉴权',
    'apps/backend/src/logistics_backend/main.py;apps/backend/src/logistics_backend/bootstrap.py;apps/backend/src/logistics_backend/api/dependencies.py;apps/backend/src/logistics_backend/api/errors.py',
    'create_app(settings: Settings) -> FastAPI; GET /api/v1/health -> HealthResponse',
    'Settings、ActorContext、ErrorEnvelope、HealthResponse',
    '仅 bootstrap 装配 adapters；API 不 import OR-Tools；MVP viewer/operator 简单角色；开发模式只绑定本机。',
    'lifespan 管理连接；trace_id 贯穿；认证和 body 限额中间件；ready 与 live 分离。',
    '无凭据请求受保护写接口 => 401 / 数据库不可用 => ready=503 且 live=200')
add(5,'master-data-services','实现主数据分页读写服务与资源日历 API',
    'apps/backend/src/logistics_backend/application/master_data.py;apps/backend/src/logistics_backend/api/master_data.py;packages/contracts/src/logistics_contracts/http.py;contracts/openapi.json',
    'MasterDataService.update(cmd: MasterDataUpdate, expected_revision: int) -> MasterDataView; GET /api/v1/orders -> OrderPage',
    'Order、Vehicle、Warehouse、资源子项与日历；API_CONTRACT 主数据表',
    '只允许 draft 订单修改需求；已下发变更走事件；生成 OpenAPI；分页 limit 1..200；排序稳定。',
    'API DTO → application → UoW → domain 校验 → adapter；按 If-Match 防丢更新；停用不硬删除。',
    'If-Match=2、实际 revision=3 => 409 / limit=201 => 422')
add(5,'durable-jobs','实现作业租约、超时取消与受限 worker',
    'apps/backend/src/logistics_backend/application/jobs.py;apps/backend/src/logistics_backend/persistence/jobs.py;apps/backend/src/logistics_backend/worker.py;apps/backend/src/logistics_backend/api/jobs.py',
    'JobService.submit(request: JobRequest, key: str) -> JobRef; Worker.run_once() -> WorkOutcome',
    'Job/JobCommand/JobRequest复用P02-04；JobKind/JobStatus复用P02-01；JobRef、JobView、CancelCommand、LeaseToken、Deadline、WorkOutcome',
    'PostgreSQL 持久化 job；进程并发默认 1；不以 FastAPI BackgroundTasks 运行重求解；lease epoch 防旧 worker 写回。',
    'SKIP LOCKED 领取、心跳续约、独立进程 deadline；取消标志与终态 CAS；过期租约回收、重试有上限。',
    'worker 领取后崩溃 => 租约到期可重领 / 旧 lease 写结果 => 拒绝且不覆盖新结果')

add(6,'transport-contract','实现运输请求、结果和 Solver Protocol',
    'packages/domain/src/logistics_domain/transport.py;packages/domain/src/logistics_domain/ports/transport.py;packages/contracts/src/logistics_contracts/transport.py',
    'TransportSolver.solve(request: TransportProblem, budget: SolveBudget) -> TransportSolution',
    'TransportRequestDTO、TransportProblem、TransportSolution、VehicleState、RoutingNode',
    '每单完整交付不拆单；单车单趟固定温区；起终点逐车定义；提送点显式不同；拒绝不支持的多车厢。',
    '解析 typed node 及订单映射；静态输入预检；构造一套纯 problem，保留全部用户约束来源。',
    'request 两个同 node_id => INVALID_INPUT / vehicle start_node!=end_node => 合法开放起终点')
add(6,'distance-matrix','实现版本化道路距离和时间矩阵提供器',
    'packages/domain/src/logistics_domain/ports/matrix.py;packages/optimization/src/logistics_optimization/transport/matrix.py;packages/contracts/src/logistics_contracts/matrix.py',
    'TravelMatrixProvider.get_matrix(query: MatrixQuery) -> TravelMatrix',
    'TravelMatrix、MatrixQuery、ArcState、WeatherProfile',
    '节点顺序、车辆 profile、版本、观测时间必填；不对称允许；不可达不是 0；缓存不能跨天气版本混用。',
    '离线矩阵校验方阵和节点覆盖；天气变更按有理系数向上取整生成新版本；求解前读取，不在回调联网。',
    'time(D,A)=100、倍率 3/2 => 150 秒 / A->B unreachable => 禁止弧而非免费通行',after=[])

add(7,'vrp-base','实现多起终点车辆路径基本求解',
    'packages/optimization/src/logistics_optimization/transport/base_model.py',
    'build_routing_model(problem: TransportProblem) -> RoutingModelContext',
    'RoutingNode、VehicleState、Route、RouteStop',
    '必服务节点恰好访问一次；车辆不可用则排除；空请求成功空计划只适用于零需求。',
    'RoutingIndexManager 映射业务 ID；NextVar/VehicleVar/ActiveVar；弧成本=距离；起终点固定；返回业务 ID 禁止泄漏内部 index。',
    'T1 两单一车 => 路线 D-A-B-D、9000m / 必服务单但无可用车 => 无候选并有诊断',kind='solver')
add(7,'capacity-and-pickup','实现重量、容积和提送货载荷约束',
    'packages/optimization/src/logistics_optimization/transport/capacity.py',
    'add_capacity_constraints(ctx: RoutingModelContext, problem: TransportProblem) -> None',
    'Cargo、PickupDeliveryPair、LoadState',
    '重量与容积独立；载荷按各路段实际剩余量；纯配送起始载荷=车上分配货物总和，提货为正、送货为负。',
    '两个 load dimensions；非零 start load 绑定路线分配；提送同车和先后；逐弧 0<=load<=capacity；不把累计已送量当实际载荷。',
    'T1 载重 800000g => 路段载荷 800000/400000/0 / T1 容量降至 799999g 且单趟 => 不可行',kind='solver')
add(7,'time-windows','实现服务时间、等待、班次与硬时间窗',
    'packages/optimization/src/logistics_optimization/transport/time_windows.py',
    'add_time_constraints(ctx: RoutingModelContext, problem: TransportProblem) -> None',
    'ServiceWindow、RouteStop、DriverShift',
    'CumulVar 表服务开始；递推 start[j]>=start[i]+service[i]+travel[i,j]；arrival/start/depart 分开；硬窗不能用罚分购买。',
    'Time dimension 含等待 slack；每站硬窗、车辆出发窗与最迟回场；逐车驾驶资格在预检过滤。',
    'T1 A窗[350,350] => arrival=300/start=350/depart=410 / 沿用A固定350变体再设B硬截止600 => A后最早610，返回不可行',kind='solver')
add(7,'temperature-and-cargo','实现温区、货物类型与车辆允许集合',
    'packages/optimization/src/logistics_optimization/transport/compatibility.py',
    'eligible_vehicles(order: Order, vehicles: tuple[Vehicle,...]) -> tuple[VehicleId,...]',
    'CargoTemperature、CargoType、VehicleCapability',
    '固定车厢温控点落在每个货物温区；整条路线兼容；禁配货物不得同时载运；不能只检查温度区间相交。',
    '形成 allowed vehicle IDs 并设置 VehicleVar 域；动态同载冲突用显式载荷区段约束或保守整趟分组并声明限制。',
    '货物[20,80]、车设定40 => 可用 / 冷冻[-250,-180] 与冷藏[20,80] 同固定温控车 => 拒绝',kind='solver')
add(7,'objective-function','实现可解释费用与可选订单目标函数',
    'packages/optimization/src/logistics_optimization/transport/objective.py',
    'build_objective(problem: TransportProblem, policy: ObjectivePolicy) -> ObjectiveBreakdown',
    'ObjectivePolicy、CostBreakdown、OptionalOrder',
    '硬订单不得 AddDisjunction 丢弃；费用整数分；惩罚有上界分析防溢出；软迟到和硬截止分字段。',
    '业务成本=逐弧四舍五入分+车辆启用费+服务费；objective另加软迟到罚分和可选未服务罚分，禁止把罚分重复计入真实成本；默认固定策略记录版本。',
    'T1 9000m、100分/km、启用500分 => 1400分 / optional 惩罚10000分、服务成本1400分 => 应服务',kind='solver')
add(7,'result-status-validation','实现运输结果提取、状态映射和独立重算',
    'packages/optimization/src/logistics_optimization/transport/result.py;packages/optimization/src/logistics_optimization/validation/transport.py',
    'extract_transport(ctx: RoutingModelContext) -> TransportSolution; validate_transport(plan: TransportPlan, snapshot: PlanningSnapshot) -> ValidationReport',
    'SolveStatus、TransportSolution、ValidationReport',
    '未知/超时无 incumbent 不等于已证明无解；运输校验不读取 solver 变量；结果逐站列出时间、服务、载荷、成本。',
    '从 assignment 提取；保存 engine_status；独立按矩阵重算覆盖率/路径/载荷/窗/成本；存在违规时候选不得有效。',
    '伪造 9000m 为 1m => COST_OR_DISTANCE_MISMATCH / TIMEOUT 无解 => candidate=null、feasibility=UNKNOWN',kind='solver')
add(7,'transport-adapter','装配运输 Solver 并验证数值与预算边界',
    'packages/optimization/src/logistics_optimization/transport/solver.py',
    'OrToolsTransportSolver.solve(problem: TransportProblem, budget: SolveBudget) -> TransportSolution',
    '完整 TransportProblem、SolveBudget、EngineMetadata',
    '固定依赖版本与策略；默认 5s 总预算；worker 外壳控制硬截止；不承诺跨平台路线字节级相同。',
    '依次装配预检/路径/容量/时间/温控/目标；减去已消耗预算；只对非空 assignment 提取与校验；错误映射类型化。',
    'T1 => FEASIBLE 且独立校验零违规 / 超大系数潜在 int64 溢出 => INVALID_INPUT 而非运行崩溃',kind='solver')

add(8,'warehouse-contract','实现仓储任务与资源日历协议',
    'packages/domain/src/logistics_domain/warehouse.py;packages/domain/src/logistics_domain/ports/warehouse.py;packages/contracts/src/logistics_contracts/warehouse.py',
    'WarehouseScheduler.solve(problem: WarehouseProblem, budget: SolveBudget) -> WarehouseSolution',
    'WarehouseTask、ResourceCalendar、OperationKind、ResourceRequirement',
    '入库/出库/分拣/装车/卸货明确区分；操作不可抢占；资源需求有单位和数量；工序依赖必须 DAG。',
    '建立 typed operation 和资源需求；拓扑检测环；资源日历合并同类不可用段；ready_at 不是正式资源预留。',
    'A依赖B且B依赖A => DEPENDENCY_CYCLE / 同工人日历[0,10) [10,20) => 可合并')
add(8,'inventory-and-handoffs','实现库存占用和仓运交接约束模型',
    'packages/domain/src/logistics_domain/inventory.py;packages/domain/src/logistics_domain/joint.py;packages/domain/src/logistics_domain/ports/joint.py;packages/contracts/src/logistics_contracts/handoff.py',
    'derive_handoffs(tasks: tuple[WarehouseTask,...], legs: tuple[TransportTask,...]) -> tuple[HandoffConstraint,...]',
    'StorageLocation、InventoryLedger、HandoffConstraint、StorageInterval',
    '库存从入库完成占用到出库开始；初始库存进入 horizon；装车结束<=车辆离开；卸货开始>=车辆到达。',
    '由实物任务链生成占用区间、数量守恒与交接节点；不得只改 warehouse_id 表示货物移动。',
    '初始库存8、库容10、[0,20)再入3 => 容量违规 / 装车结束500、车辆离开499 => HANDOFF_VIOLATION')

add(9,'intervals-precedence','实现仓储区间、互斥资源与任务依赖',
    'packages/optimization/src/logistics_optimization/warehouse/intervals.py',
    'build_intervals(problem: WarehouseProblem) -> WarehouseModelContext',
    'OperationAssignment、WarehouseTask、Dock',
    'CP-SAT 全整数；候选资源用 presence optional intervals；每项必需任务恰选一个可用资源。',
    'start/end/duration 整数变量；ExactlyOne assignment；NoOverlap 月台；precedence 与硬窗约束。',
    'W1无setup变体、两个10秒任务同月台 => 最短 makespan20 / t2依赖t1 => t2.start>=t1.end',kind='solver')
add(9,'cumulative-resources','实现人员、设备和温区容量限制',
    'packages/optimization/src/logistics_optimization/warehouse/resources.py',
    'add_resource_constraints(ctx: WarehouseModelContext, problem: WarehouseProblem) -> None',
    'Worker、Equipment、WarehouseZone、CalendarCapacity',
    '需求数量与资源单位一致；技能/温区资格预过滤；故障段作为不可用/减容处理。',
    '人员与设备池用 Cumulative；具体独占设备用 NoOverlap；可变容量用固定 blocker intervals 占用基准容量差。',
    '容量2、两作业各需2 => 不可重叠 / 设备[5,15)不可用、任务时长10 => 不能安排[0,10)',kind='solver')
add(9,'storage-capacity','实现库位库存区间和冷链容量约束',
    'packages/optimization/src/logistics_optimization/warehouse/storage.py',
    'add_storage_constraints(ctx: WarehouseModelContext, problem: WarehouseProblem) -> None',
    'StorageInterval、InventoryLedger、StorageLocation',
    '入库/出库端点由任务决定；初始存量从 t=0 开始；存储温控点必须满足所有同存货物。',
    '建立可变长度 interval 与重量/容积 cumulative；终点未出库则延续到 horizon；校验出库量不大于可用量。',
    '库容10、初始8直到20、新3从10入 => 不可行 / 新3从20入 => 库容可行',kind='solver')
add(9,'sequence-setup','实现清洁及月台、温区、分拣切换时间',
    'packages/optimization/src/logistics_optimization/warehouse/setup.py',
    'add_sequence_setup(ctx: WarehouseModelContext, policy: SetupPolicy) -> None',
    'SetupPolicy、SetupOperation、SequenceArc',
    'NoOverlap 不会自动处理准备时间；用相邻关系，不可对所有非相邻作业重复收清洁费；准备若用工人设备也要占用。',
    '每资源局部 circuit 含 dummy 和可选任务自环，选中弧 i->j 强制 start[j]>=end[i]+setup(i,j)；准备区间占资源。',
    'W1 顺序A->B清洁5 => makespan25 / A->C->B => 不额外叠加非相邻A->B准备',kind='solver')
add(9,'warehouse-result','装配仓储目标、结果提取与独立校验',
    'packages/optimization/src/logistics_optimization/warehouse/solver.py;packages/optimization/src/logistics_optimization/validation/warehouse.py',
    'CpSatWarehouseScheduler.solve(problem: WarehouseProblem, budget: SolveBudget) -> WarehouseSolution',
    'WarehouseSolution、WarehouseCost、ValidationReport',
    '目标 soft_tardiness_cost + overtime_cost + setup_cost + makespan_weight*makespan；保留 bound/gap；UNKNOWN 不是 INFEASIBLE。',
    '装配各约束，单 worker、seed42、5s 默认；读取被选任务；独立 sweep-line 验容量/工序/准备；保存所有目标分项。',
    'W1清洁5 => 25秒且校验通过 / 人为删掉 setup interval => SETUP_VIOLATION',kind='solver')

add(10,'validator-protocol','实现统一校验报告与约束覆盖注册表',
    'packages/domain/src/logistics_domain/ports/validation.py;packages/contracts/src/logistics_contracts/validation.py;packages/optimization/src/logistics_optimization/validation/registry.py',
    'ConstraintValidator.validate(plan: CandidatePlan, snapshot: PlanningSnapshot) -> ValidationReport',
    'Constraint、Violation、ValidationReport、ConstraintCoverage',
    '未知 required constraint fail closed；report 绑定 candidate_hash/snapshot_hash/rules_version；不能用空违规列表假装全部检查。',
    '注册 constraint_id/version 到纯校验函数；返回 checked/required/unsupported 列表及位置、实际值、期望值。',
    'required含未注册规则 => valid=false / 输入候选 hash 变化 => 旧 report 不可复用')
add(10,'joint-validator','实现跨仓运链、库存和资源完整校验',
    'packages/optimization/src/logistics_optimization/validation/joint.py',
    'validate_joint(plan: CandidatePlan, snapshot: PlanningSnapshot) -> ValidationReport',
    'CandidatePlan、HandoffConstraint、TransportTask、WarehouseTask、库存与资源',
    '组合各域 validator，并独立验证装卸时间、实物数量、订单覆盖、同车冲突、司机班次和温控。',
    '按稳定 task_id 合并有向事件链；时间排序 sweep 库存与容量；检查首末实物去向和所有跨域约束。',
    '各子解可行但装车end500/发车490 => joint invalid / 同一箱货分给两车 => INVENTORY_CONSERVATION')
add(10,'validator-adversarial-suite','建立独立硬约束反例与小规模 oracle 套件',
    'tests/solver/oracles.py;tests/solver/test_constraint_mutations.py;docs/algorithms/VALIDATOR_COVERAGE.md',
    'mutate_valid_plan(plan: CandidatePlan, mutation: ViolationMutation) -> CandidatePlan',
    '全部硬约束 ID 与 deterministic oracle',
    '只在测试使用枚举 oracle；不得用同一 solver 代码校验自己；每个核心硬约束至少一个精确反例。',
    '从 T1/W1 手算解一次只改变一个字段；<=7 节点枚举路线最小值；记录漏检与错误定位断言。',
    'T1最优9000m与oracle一致 / 对每条核心硬约束单独破坏 => 对应 violation code 必须出现',kind='solver')

add(11,'simulation-contract','实现仿真场景、状态、快照与随机源契约',
    'packages/domain/src/logistics_domain/simulation.py;packages/domain/src/logistics_domain/ports/simulation.py;packages/contracts/src/logistics_contracts/simulation.py',
    'SimulationEngine.run(request: SimulationRequest) -> SimulationResult; ScenarioEngine.load(ref: ScenarioRef) -> ScenarioBundle',
    'Simulation、SimulationSnapshot、ScenarioSpec、TwinState、RngState',
    '仿真时间用相对整数秒，wall clock 独立；每分支 RNG；输入计划必须有有效校验报告；禁止直接写真实订单。',
    '定义状态投影、可序列化待执行事件、随机流种子及状态、任务执行游标；恢复不 pickle SimPy generator。',
    'scenario has same seed but branch_id不同 => 状态隔离 / snapshot 缺 RNG state => 不允许精确恢复')
add(11,'execution-state-machine','实现订单、车辆和仓库执行状态转换',
    'packages/simulation/src/logistics_simulation/state.py;packages/simulation/src/logistics_simulation/projection.py',
    'DigitalTwinEngine.apply(state: TwinState, event: ExecutionEvent) -> TwinState',
    'OrderExecution、VehicleExecution、WarehouseExecution、ExecutionEvent',
    '计划状态与执行事实分开；车辆位置携带路段/进度，货物位置唯一；不可凭 ETA 写 delivered。',
    '纯 reducer 验事件前置状态、时间与版本；同 event_id 去重；每次转换追加可回放事实。',
    '未装车订单收到 delivery_complete => INVALID_TRANSITION / 同 arrival 事件两次 => 状态与版本只推进一次')

add(12,'simpy-kernel','实现 SimPy 时间推进与稳定事件调度内核',
    'packages/simulation/src/logistics_simulation/engine.py',
    'SimPySimulationEngine.run(request: SimulationRequest) -> SimulationResult',
    'EventQueueItem、TwinState、SimulationControl',
    '统一按 (occurred_at_s, priority, insertion_seq) 排序；fault/cancel priority0，completion1，dispatch2，observation3。',
    '显式调度队列驱动 env；advance_to(t) 处理所有 time<=t 事件含边界；pause 不推进时钟；禁止隐式依赖 env.run(until=t) 包含 t。',
    't=10故障与t=10装车完成 => 先故障再处理完成事件 / advance_to(10) => t=10所有合法事件已处理',kind='simulation')
add(12,'transport-execution','实现车辆移动、服务与订单交付过程',
    'packages/simulation/src/logistics_simulation/transport.py',
    'execute_route(route: Route, state: TwinState, scheduler: EventScheduler) -> ExecutionHandle',
    'RouteStop、VehicleExecution、OrderExecution、CargoLocation',
    '使用场景矩阵与速度扰动；等待/服务/行车分别记账；演示动画不得改变仿真状态。',
    '为出发、到达、服务完成排事件；行车保存 road_segment/start/end/progress；每单完成由事件确证。',
    'T1无扰动 => A到300、B到560、回仓1020 / 暂停t150 => D-A路段进度1/2且订单未交付',kind='simulation')
add(12,'warehouse-execution','实现仓储资源争用、作业与库存演化',
    'packages/simulation/src/logistics_simulation/warehouse.py',
    'execute_operations(plan: WarehousePlan, state: TwinState, scheduler: EventScheduler) -> ExecutionHandle',
    'WarehouseExecution、ResourceUsage、InventoryLedger',
    '同时申请多资源采用统一排序与原子 admission，避免部分占有死锁；前驱完成才可启动；清洁是真实作业。',
    '按计划事件检查资源与前驱，资源不足进入队列；完成释放；中断保留已执行事实并显式记录剩余工作。',
    '两作业均需同月台 => 不重叠 / 故障发生于作业中 => interrupted且不伪造原完成时间',after=['P12-01'],kind='simulation')
add(12,'snapshot-replay','实现快照恢复和反事实分支隔离',
    'packages/simulation/src/logistics_simulation/snapshots.py;packages/simulation/src/logistics_simulation/scenarios.py',
    'restore(snapshot: SimulationSnapshot) -> SimulationSession; fork(snapshot: SimulationSnapshot, policy: BranchPolicy) -> SimulationSession',
    'SimulationSnapshot、PendingEvent、RngState、ScenarioBranch',
    '只在已排空同时间事件批次的安全边界快照；保存待执行事件和剩余时长；不序列化活跃生成器；共同随机数按稳定业务 key。',
    '从投影重建资源占用与事件队列；恢复 RNG 各流状态；分支写独立 simulation_id；规范化 hash 排除 wall-time。',
    'T1 t400快照恢复至结束 => 与不停机轨迹和指标一致 / 分支天气倍率2 => 原分支 hash 不变',after=['P12-02','P12-03'],kind='simulation')

add(13,'event-ingestion','实现十类异常事件的校验、去重与排序',
    'packages/contracts/src/logistics_contracts/events.py;packages/simulation/src/logistics_simulation/events.py;apps/backend/src/logistics_backend/application/event_ingestion.py',
    'EventEngine.ingest(envelope: EventEnvelope) -> EventReceipt',
    'Event、ExceptionEvent、10 种 typed payload',
    '车辆故障、延误、交通、天气、货物异常、取消、需求增/减、设备故障、资源不可用全部有判别 payload；迟到事件不静默倒带。',
    '来源/事件ID幂等；occurred/received 分存；同秒稳定排序；迟到事实进入需要重投影标志并隔离已提交版本。',
    '同 source/event_id 重复 => 同 receipt / demand_increase delta=0 => INVALID_INPUT')
add(13,'event-api-and-outbox','实现事件注入服务及持久化分发',
    'apps/backend/src/logistics_backend/api/events.py;apps/backend/src/logistics_backend/application/outbox.py;apps/backend/src/logistics_backend/persistence/outbox.py',
    'POST /api/v1/events -> EventReceipt; OutboxDispatcher.dispatch_batch(limit: int) -> DispatchReceipt',
    'EventEnvelope、OutboxRecord、DeliveryCursor',
    '仿真注入必须含 simulation_id；正式事件有 operator 权限；同一事务保存事件和 outbox；按至少一次交付设计消费者。',
    '校验后写入事件，outbox 批量领取重试，ack 幂等；轮询读取事件在 WebSocket 之前可用。',
    'DB commit 后分发进程崩溃 => 重启仍能消费 / 重复 outbox delivery => 影响记录不重复')

add(14,'impact-graph','实现异常影响依赖图与最小闭包',
    'packages/optimization/src/logistics_optimization/rescheduling/impact.py;packages/contracts/src/logistics_contracts/rescheduling.py',
    'ImpactAnalyzer.analyze(event: ExceptionEvent, snapshot: ExecutionSnapshot, plan: ScheduleVersion) -> ImpactReport',
    'ImpactReport、TaskDependency、ResourceInterval、AffectedOrder',
    '事件识别必须引用已登记资源；闭包包括实物依赖与共享资源时段；不把所有任务默认标影响。',
    '事件实体映射种子节点，沿任务/货物/资源重叠边扩展到边界稳定；每条 affected task 保存 reason path。',
    'I1 T1->T2 与独立T3，T1车故障 => affected={T1,T2} / 无共享时段的同仓任务 => 不被无理由扩展')
add(14,'execution-freeze','实现不可逆事实、在途起点与重排边界提取',
    'packages/optimization/src/logistics_optimization/rescheduling/boundary.py',
    'build_boundary(impact: ImpactReport, execution: ExecutionSnapshot) -> RescheduleBoundary',
    'FrozenPrefix、InFlightCargo、VirtualStart、InterruptedOperation',
    '已执行事实永不改；正常不可抢占任务固定；故障中断任务只排剩余部分；取消在途单仍需实物去向。',
    '按 event_time 切分 completed/active/future；建立虚拟起点、剩余载荷和班次；外部未受影响资源作为固定占用。',
    't150 T1在D-A半程 => 虚拟起点不能是D / 已交付订单取消 => 拒绝改历史并记录业务冲突')

add(15,'candidate-policies','实现局部候选策略与救援交接任务生成',
    'packages/optimization/src/logistics_optimization/rescheduling/candidates.py',
    'generate_candidates(boundary: RescheduleBoundary, policy: ReschedulePolicy) -> tuple[AdjustmentSpec,...]',
    'AdjustmentSpec、RescueTransfer、ReturnTask、ReschedulePolicy',
    '候选是受限策略和约束修改，不是未求解的正式路线；默认最多3个；救援需要位置、到达时间、交接时长和温控数据。',
    '生成换车/顺延/替代资源三类合法邻域；取消增加返仓或既定处置任务；缺救援事实返回 MANUAL_REQUIRED。',
    '故障车载货但无救援位置 => MANUAL_REQUIRED / 在途取消100箱 => 生成100箱返仓实物任务')
add(15,'local-solve','实现冻结边界下的局部重新求解',
    'packages/domain/src/logistics_domain/ports/rescheduling.py;packages/optimization/src/logistics_optimization/rescheduling/solver.py;packages/optimization/src/logistics_optimization/coordination/joint.py',
    'RescheduleSolver.solve(request: RescheduleProblem, budget: SolveBudget) -> RescheduleSolution',
    'RescheduleProblem、RescheduleBoundary、CandidatePlan',
    '未受影响任务固定车/资源/时刻/顺序；不可逆前缀不作为可变变量；全局 validator 仍检查完整合并方案。',
    '裁剪变量并把外部占用建固定约束；纯JointPlanningSolver kernel在同一budget内最多3轮传递ready/arrival窗口调用运输/仓储；合并稳定task_id并完整校验；该kernel后续P16直接复用，不写数据库。',
    'I1仅T1/T2受影响 => T3所有字段保持 / 局部方案抢用T3月台 => 完整校验拒绝',kind='solver')
add(15,'bounded-escalation','实现局部扩展与全局剩余任务降级策略',
    'packages/optimization/src/logistics_optimization/rescheduling/escalation.py',
    'solve_with_escalation(request: RescheduleProblem, budget: SolveBudget) -> RescheduleSolution',
    'SearchScope、EscalationReason、BudgetLedger',
    'local -> expanded -> all_unexecuted 最多3层，共用15秒默认预算；不能放松硬时间窗；局部无解不等于全局无解。',
    '记录每轮范围/hash/耗时/engine_status；无候选才按策略扩大；旧计划在新事实下重验，失效受影响任务进入暂停建议。',
    '第一轮用6秒 => 后两轮共剩<=9秒 / 全部超时 => TIMEOUT+暂停建议，禁止声称新方案成功',kind='solver')
add(15,'version-diff','实现版本差异与候选排序',
    'packages/optimization/src/logistics_optimization/rescheduling/diff.py;packages/optimization/src/logistics_optimization/rescheduling/ranking.py',
    'compare_versions(base: ScheduleVersion, candidate: CandidatePlan) -> ScheduleDiff; rank_candidates(items: tuple[CandidateEvaluation,...]) -> tuple[CandidateEvaluation,...]',
    'ScheduleDiff、CandidateEvaluation、DecisionRecord',
    '输出 changed_tasks、added_cost、delay_difference、resource_changes、affected_orders、constraint_results；先可行再按明确指标比较。',
    '按稳定 task_id 对齐；区分added/removed/modified；未来任务数归一扰动；排序键=(optional_unserved,soft_delay_s,cost_cents,disturbance)并声明不保证词典序全局最优。',
    'V1成本1000、V2=1200 => added_cost=200 / 4项未来任务中改派1项 => changed_tasks=1、改派比例1/4')

add(16,'optimization-job-api','实现运输、仓储和重排作业 API',
    'apps/backend/src/logistics_backend/application/optimization.py;apps/backend/src/logistics_backend/api/optimization.py;apps/backend/src/logistics_backend/api/rescheduling.py',
    'POST /api/v1/optimizations/transport -> JobRef; POST /api/v1/optimizations/warehouse -> JobRef; POST /api/v1/reschedules -> JobRef',
    'OptimizationRequestDTO、RescheduleRequestDTO、JobRef',
    '202返回持久化job；调用前捕获版本化快照；幂等key必填；budget 上限服务端控制；结果查询与候选确认分离。',
    'DTO→用例→快照→持久化job；worker 通过ports运行并存 typed result；异常状态透传不伪装200成功。',
    '重复同key请求 => 同job_id / 求解超时 => job终态 completed、result.solve_status=TIMEOUT且无候选')
add(16,'joint-planning-service','实现有界仓运窗口反馈协调服务',
    'apps/backend/src/logistics_backend/application/joint_planning.py;apps/backend/src/logistics_backend/api/joint_planning.py',
    'JointPlanningService.solve(request: JointPlanningRequest) -> JointPlanningResult; POST /api/v1/optimizations/joint -> JobRef',
    'WarehouseWindowOffer、HandoffConstraint、JointPlanningResult',
    '每单最多2个候选仓，默认3轮/15秒总预算；报价不预留；非全局联合最优承诺；冲突不可只靠LLM解释消除。',
    '应用服务复用P15-02的纯JointPlanningSolver kernel：候选仓资格→仓储ready windows→运输→真实到达时间仓储再排→收紧窗口/切换候选→完整校验；重复候选hash停止震荡；不在application重写约束。',
    '装车需要到500、车原发490 => 下轮发车>=500 / 三轮仍冲突 => NO_FEASIBLE_CANDIDATE且无可提交版本')
add(16,'validated-commit-api','实现重新校验后的版本确认服务',
    'apps/backend/src/logistics_backend/application/commit_schedule.py;apps/backend/src/logistics_backend/api/schedules.py',
    'ScheduleService.commit(cmd: CommitCommand, actor: ActorContext) -> CommitReceipt; POST /api/v1/schedules/{id}/versions/commit -> CommitReceipt',
    'CandidatePlan、ValidationReport、CommitCommand、ScheduleVersion',
    '只有此服务发布正式版本；候选必须关联可信worker保存的OR-Tools求解证据且assignment_hash匹配；确认前重取事实并校验；事务内复核版本向量/CAS；候选过期失败而非覆盖历史。',
    '核验actor/确认令牌/候选hash；独立全链validate；PlanCommitStore原子写Vn+1与outbox；不在持锁时做长求解。',
    'V1两请求都期待active=V1 => 恰好一个V2成功 / 校验后车辆revision变更 => STALE_SNAPSHOT / 手造候选无可信OR-Tools求解记录 => UNVERIFIED_SOLVER_RESULT')
add(16,'simulation-query-api','实现仿真控制、版本对比与结果查询 API',
    'apps/backend/src/logistics_backend/application/simulation.py;apps/backend/src/logistics_backend/api/simulations.py;apps/backend/src/logistics_backend/api/results.py',
    'POST /api/v1/simulations -> JobRef; POST /api/v1/simulations/{id}/control -> SimulationView; GET /api/v1/schedules/{id}/diff -> ScheduleDiff',
    'SimulationRequestDTO、SimulationControl、SimulationView、ScheduleDiff',
    'pause/resume/step 使用版本化control_seq；正式计划只读；查询对象验证归属和分页；前端可以轮询。',
    '持久化控制命令由worker消费；幂等回执；快照和事件分表查询；分支结果明确source=simulation。',
    '重复step control_seq=3 => 只推进一次 / compare不同schedule的版本 => 422',after=['P16-03'])

add(17,'tool-schemas','实现 Agent 标准工具注册、权限与参数协议',
    'packages/agents/src/logistics_agents/tools/protocol.py;packages/agents/src/logistics_agents/tools/registry.py;packages/contracts/src/logistics_contracts/tools.py',
    'ToolExecutor.execute(call: ToolCallRequest, context: ToolContext) -> ToolResult',
    'ToolSpec、ToolCallRequest、ToolResult、ToolPermission、ActorContext',
    '白名单工具名称、Schema参数、截止时间、幂等key、expected_revision；工具返回typed结果引用；禁止eval/shell/任意URL工具。',
    '注册表生成 JSON Schema；按Actor权限与Agent角色交集授权；校验args后分发；保存调用输入hash与trace。',
    'transport_agent调用commit_schedule => TOOL_FORBIDDEN / 参数多出sql字段 => INVALID_TOOL_ARGUMENTS')
add(17,'business-tools','实现工具到业务服务的唯一适配层',
    'apps/backend/src/logistics_backend/agent_tools.py;packages/agents/src/logistics_agents/tools/results.py',
    'build_tool_registry(services: ServiceBundle) -> ToolRegistry',
    'read_snapshot、submit_transport、submit_warehouse、submit_joint、get_job、validate_candidate、analyze_impact、submit_reschedule、compare_versions、start_simulation、commit_schedule',
    '工具不得直接操作repository；写操作继承actor、幂等、版本检查；commit需要用户明确确认绑定candidate_hash的短期令牌。',
    '逐个ToolSpec映射已有服务；job轮询有间隔和deadline；ToolCall审计包含服务结果引用，不复制敏感全量数据。',
    '同submit工具重试 => 同job / 无confirmation_token提交 => CONFIRMATION_REQUIRED')

add(18,'llm-provider','实现模型供应商抽象与结构化响应边界',
    'packages/agents/src/logistics_agents/llm/protocol.py;packages/agents/src/logistics_agents/llm/provider.py;packages/contracts/src/logistics_contracts/llm.py',
    'LLMProvider.complete(request: LLMRequest) -> LLMResponse',
    'LLMRequest、LLMResponse、ToolProposal、UsageRecord',
    '模型名/endpoint/密钥来自配置；密钥只在后端；本阶段不锁某供应商为领域依赖；tests替身不得装配正式启动。',
    '选一种实际供应商adapter验证tool/structured output能力；映射usage与请求id；解析后再Pydantic验证；禁止接受模型排程数组。',
    '响应缺必填tool_args => PROVIDER_SCHEMA_ERROR / 未配置密钥 => PROVIDER_UNAVAILABLE且表单求解仍可用')
add(18,'llm-resilience','实现模型预算、重试、脱敏与故障降级',
    'packages/agents/src/logistics_agents/llm/resilience.py;packages/agents/src/logistics_agents/llm/redaction.py',
    'complete_with_policy(request: LLMRequest, policy: LLMPolicy) -> LLMResponse',
    'LLMPolicy、BudgetLedger、ProviderError、RedactedMessage',
    '仅429/暂态网络/5xx指数退避最多2次并尊重总deadline；schema错误最多1次修复；不可重试已执行业务写工具。',
    '请求前脱敏和token预算；响应后计量；失败转结构化表单/确定性模板解释，不把模板冒充模型输出。',
    '供应商持续429 => bounded失败且请求次数<=3 / 返回含api_key的错误 => 日志不含原密钥')

add(19,'intent-extraction','实现 Coordinator 意图及约束抽取',
    'packages/agents/src/logistics_agents/coordinator/intent.py;packages/contracts/src/logistics_contracts/intents.py',
    'CoordinatorAgent.parse(message: UserMessage, context: AgentContext) -> IntentDraft',
    'IntentDraft、ConstraintProposal、ClarificationRequest、EntityReference',
    '每个抽取字段保留原文证据；只引用服务查得的ID；缺时间/单位/对象必须澄清；不得推测容量和道路距离。',
    '模型抽取候选→Schema校验→实体解析工具→领域检查；把不确定字段列为questions，禁止自动进入求解。',
    '把O1改到明天 => 缺时区/目标时窗时返回澄清 / 用户说冷藏但没温区 => 不自填2–8摄氏度')
add(19,'coordinator-state-machine','实现 Coordinator 任务分解与有界运行状态机',
    'packages/agents/src/logistics_agents/coordinator/agent.py',
    'CoordinatorAgent.run(request: AgentRequest, executor: ToolExecutor) -> AgentOutcome',
    'AgentRun、AgentPlan、AgentStep、IntentDraft',
    '固定可用任务类型；最多12次工具调用/2轮修复/60秒；waiting_input不是failed；确认之前只产生候选引用。',
    'received→clarify或plan→execute→validate→explain→await_confirmation/done；工具失败显式状态迁移并持久记录。',
    '第13次工具调用 => BUDGET_EXCEEDED / 意图缺订单ID => waiting_input且不调用solver')

add(20,'transport-agent-tools','实现 TransportAgent 求解工具工作流',
    'packages/agents/src/logistics_agents/transport/agent.py',
    'TransportAgent.run(task: TransportAgentTask, executor: ToolExecutor) -> TransportAgentOutcome',
    'TransportAgentTask、JobRef、OptimizationResultRef',
    '仅read_snapshot/submit_transport/get_job/validate_candidate；输入约束来自已确认IntentDraft；不新造路线。',
    '读取快照→提交typed request→等待job→验证结果→返回candidate/result引用；超时或无解保留原状态。',
    'solver无候选 => agent不输出伪造路线 / 工具成功返回candidate C1 => outcome只引用C1及校验证据')
add(20,'transport-explanation','实现有证据的运输结果解释',
    'packages/agents/src/logistics_agents/transport/explain.py',
    'explain_transport(result: TransportResultView) -> EvidenceExplanation',
    'EvidenceExplanation、FactRef、CostBreakdown',
    '所有数字由结果格式化；模型仅组织语言；引用失配时回退确定性模板；不声称启发式全局最优。',
    '提取路线/服务/费用/违规事实表；解释句绑定fact_ids；后验校验数值与状态断言。',
    'T1成本1400分 => 显示14.00元 / 模型声称10元 => 拒绝该解释并用事实模板')

add(21,'warehouse-agent-tools','实现 WarehouseAgent 排程与窗口报价工作流',
    'packages/agents/src/logistics_agents/warehouse/agent.py',
    'WarehouseAgent.run(task: WarehouseAgentTask, executor: ToolExecutor) -> WarehouseAgentOutcome',
    'WarehouseAgentTask、WarehouseWindowOffer、OptimizationResultRef',
    '报价带snapshot_hash/有效期，非正式资源承诺；不改库存；只调用仓储业务工具。',
    '读取资格资源→构造仓储请求→提交求解→返回已验证窗口与约束诊断；不跨域直接改车辆路线。',
    '报价过期 => OFFER_EXPIRED / 无可用月台 => 诊断引用对应constraint_id')
add(21,'warehouse-explanation','实现仓储甘特与资源瓶颈解释数据',
    'packages/agents/src/logistics_agents/warehouse/explain.py',
    'explain_warehouse(result: WarehouseResultView) -> EvidenceExplanation',
    'WarehouseTask、ResourceUsage、FactRef',
    '清洁/等待/作业分别解释；资源利用率使用evaluation契约口径，尚未实现时不自行计算第二套指标。',
    '按真实任务区间生成事实与瓶颈证据；仅从明确诊断解释等待，不凭顺序猜原因。',
    'W1 A10+清洁5+B10 => 解释总25秒 / 无阻塞原因记录 => 文案明确原因未记录')

add(22,'exception-agent-tools','实现 ExceptionAgent 九步处置工作流',
    'packages/agents/src/logistics_agents/exception/agent.py',
    'ExceptionAgent.run(task: ExceptionAgentTask, executor: ToolExecutor) -> ExceptionAgentOutcome',
    'ExceptionEvent、ImpactReport、AdjustmentSpec、RescheduleResult、DecisionRecord',
    '依次事件识别→影响→任务→候选→局部求解→硬校验→比较→建议→记录；不能省略失败轮次。',
    '状态机只调用已实现业务工具；保留每阶段输入输出引用；需要救援事实时返回人工补充而不自造。',
    '故障缺位置 => manual_required且无commit / 局部结果无效 => 不进入建议确认状态')
add(22,'exception-explanation','实现异常处置链和版本差异解释',
    'packages/agents/src/logistics_agents/exception/explain.py',
    'explain_exception(record: DecisionRecordView) -> EvidenceExplanation',
    'DecisionRecord、ScheduleDiff、MetricDelta、FactRef',
    '清楚区分事实/预测/建议；引用原版本、新候选、变化范围与剩余风险；不能称未确认方案已生效。',
    '组合事件时间线、影响路径和diff事实；按规则模板兜底；数值只从工具结果取值。',
    'V2候选未确认 => 文案使用待确认 / added_cost=200分 => 明确增加2.00元')

add(23,'agent-orchestration','实现四角色路由、取消与有界协调',
    'packages/agents/src/logistics_agents/orchestration.py;apps/backend/src/logistics_backend/application/agent_runs.py',
    'AgentOrchestrator.run(request: AgentRequest) -> AgentOutcome',
    'AgentRun、RoleAssignment、CoordinationRound、ToolCall',
    '逻辑角色不强制独立模型进程；联合排程仍由JointPlanningService确定性协调；不无限互聊；同run共享预算。',
    'Coordinator分派typed子任务，允许独立只读任务并行；候选统一汇总校验；取消传播到子job与工具deadline。',
    '父run取消 => 子job收到取消且不得commit / 两角色重复求解同key => 共用幂等job')
add(23,'agent-api-safety','实现 Agent 会话 API 与攻击性输入验收',
    'apps/backend/src/logistics_backend/api/agents.py;tests/integration/test_agent_injection.py',
    'POST /api/v1/agent-runs -> AgentRunRef; POST /api/v1/agent-runs/{id}/messages -> AgentRunView; POST /api/v1/agent-runs/{id}/confirm -> CommitReceipt',
    'UserMessage、AgentRunView、ConfirmationToken',
    '聊天内容、工具返回、外部资料均不授予权限；确认令牌绑定actor/run/candidate_hash/revision/过期时间，服务端核验。',
    '提供会话历史与typed步骤；测试越权/注入/超额/过期确认/重放；实际供应商smoke独立标注，离线fake不能冒充通过。',
    '消息忽略规则直接写SQL => 无SQL能力且拒绝 / 确认C1令牌用于C2 => 409')

add(24,'react-shell','建立 React 应用壳、路由与统一状态展示',
    'apps/frontend/src/App.tsx;apps/frontend/src/router.tsx;apps/frontend/src/components/AppShell.tsx;apps/frontend/src/components/AsyncState.tsx;apps/frontend/src/styles.css',
    'AppShell({children}: AppShellProps) -> ReactElement; AsyncState<T>({state,render}: AsyncStateProps<T>) -> ReactElement',
    '11个导航入口、QueryState、ActorView',
    'Dashboard/Orders/Vehicles/Warehouses/Transport/WarehouseScheduling/Simulation/Exceptions/AgentChat/Metrics/Experiments 全部有路由；未交付页明确未启用。',
    '桌面与窄屏布局；loading/empty/error/ready组件；键盘焦点与路由懒加载；不内置调度假数据。',
    '视口375px => 导航可达无横向溢出 / 未实现Metrics页 => 显示待接入而非虚构指标',kind='frontend')
add(24,'generated-api-client','建立 OpenAPI 生成客户端和数据请求层',
    'apps/frontend/scripts/contracts.mjs;apps/frontend/src/client/generated.ts;apps/frontend/src/client/api.ts;apps/frontend/src/client/query.ts',
    'createApiClient(config: ApiConfig) -> ApiClient; queryKey(resource: ResourceRef) -> readonly unknown[]',
    '全部OpenAPI请求/响应/enum、ErrorEnvelope',
    '只生成类型，不手写业务enum；HTTP请求经客户端；401/409/422/503分别展示；token不写日志或源码。',
    '生成脚本读取contracts/openapi.json并支持--check；缓存键含version/filter；中止过期请求；轮询有退避上限。',
    'OpenAPI enum新增值 => contracts:check失败直到再生成 / 两次刷新乱序响应 => 旧响应不覆盖新状态',kind='frontend')

add(25,'orders-ui','实现订单查询、编辑和取消事件入口',
    'apps/frontend/src/features/orders/Page.tsx;apps/frontend/src/features/orders/OrderForm.tsx',
    'OrdersPage() -> ReactElement; OrderForm({order,onSaved}: OrderFormProps) -> ReactElement',
    'OrderDTO、OrderPage、OrderUpdate、OrderCancellationPayload',
    '时间带时区、重量/容积单位明确；前端仅输入格式检查；已下发取消通过事件API；冲突显示最新revision。',
    '分页筛选→详情→表单请求→服务错误定位；取消展示影响提示并提交typed事件，等待后端处置。',
    '草稿O1修改weight => 使用If-Match / 执行中O1取消 => 调events而非直接改status',kind='frontend')
add(25,'vehicles-ui','实现车辆、司机和可用日历页面',
    'apps/frontend/src/features/vehicles/Page.tsx;apps/frontend/src/features/vehicles/VehicleForm.tsx',
    'VehiclesPage() -> ReactElement',
    'VehicleDTO、DriverDTO、ResourceCalendar',
    '展示容量/温控点/资格/班次/状态；停用已执行车辆走故障事件；不在UI自行判断可服务订单。',
    '读写主数据，车辆与司机关联选择；服务端错误逐字段回显；日历用统一UTC转换。',
    '容量字段-1 => 服务端422可见 / viewer进入 => 只读且服务端同样拒写',after=[],kind='frontend')
add(25,'warehouses-ui','实现仓库、温区、库位及作业资源页面',
    'apps/frontend/src/features/warehouses/Page.tsx;apps/frontend/src/features/warehouses/ResourceEditor.tsx',
    'WarehousesPage() -> ReactElement; ResourceEditor({resource}: ResourceEditorProps) -> ReactElement',
    'WarehouseDTO、ZoneDTO、StorageLocationDTO、DockDTO、WorkerDTO、EquipmentDTO',
    '层级关系只从API读取；人员/设备能力单位明确；资源故障提交事件；不把展示占用当真实预留。',
    '主从详情和分页资源表；编辑走相同revision契约；空温区、停用资源与日历冲突有明确状态。',
    '仓库无温区 => 空状态而非崩溃 / equipment故障 => event引用设备ID',after=[],kind='frontend')

add(26,'transport-request-ui','实现运输请求、作业进度与不可行诊断页面',
    'apps/frontend/src/features/transport/RequestPanel.tsx;apps/frontend/src/features/transport/JobStatus.tsx',
    'TransportRequestPanel() -> ReactElement',
    'TransportRequestDTO、JobRef、SolveStatus、ValidationReport',
    '请求可复查所选快照与约束；超时/无解/失败/取消分开；按钮防重但服务端幂等仍必须使用。',
    '表单提交202→轮询job→结果/诊断；取消作业→等待终态；不自动确认候选。',
    'TIMEOUT null candidate => 不显示成功路线 / 双击提交 => 一个幂等key对应一个job',kind='frontend')
add(26,'transport-plan-ui','实现路线、逐站执行表和候选确认视图',
    'apps/frontend/src/features/transport/PlanView.tsx;apps/frontend/src/features/transport/RouteDiagram.tsx',
    'TransportPlanView({version}: TransportPlanViewProps) -> ReactElement',
    'Route、RouteStop、CostBreakdown、CommitReceipt',
    '2D节点示意不冒充GIS真实几何；到达/开始/离开分列；地图不可用仍展示表；确认绑定候选hash。',
    '生成只读路线图/车辆筛选/逐站表/费用分项；提交确认后显示新version；409要求刷新和重新审核。',
    'T1 => 9000m、14元且站时正确 / 确认返回STALE_SNAPSHOT => 不显示已生效',kind='frontend')

add(27,'warehouse-gantt-ui','实现仓储请求和资源甘特图',
    'apps/frontend/src/features/warehouse-scheduling/Page.tsx;apps/frontend/src/features/warehouse-scheduling/Gantt.tsx',
    'WarehouseGantt({tasks,resources}: WarehouseGanttProps) -> ReactElement',
    'WarehouseRequestDTO、WarehouseTask、SetupOperation、CalendarBlock',
    '等待/作业/清洁/不可用区间不同标识并有文字；不支持拖动直接改计划；业务冲突由后端返回。',
    '提交作业并轮询；按资源分泳道，统一时间尺度；任务详情展示前驱与资源需求。',
    'W1 => A[0,10)、clean[10,15)、B[15,25) / 无解 => 展示诊断无虚构甘特',kind='frontend')
add(27,'joint-handoff-ui','实现仓运交接与联合方案对照视图',
    'apps/frontend/src/features/warehouse-scheduling/HandoffView.tsx',
    'HandoffView({result}: HandoffViewProps) -> ReactElement',
    'JointPlanningResult、HandoffConstraint、ValidationReport',
    '显示仓储完成/车辆到达/离开与联合校验；不对各子解单独确认；联动事实只读。',
    '对齐订单任务链，展示每轮反馈与最后候选；不满足交接的条目标红并禁止确认入口。',
    'load.end500 departure490 => 显示冲突且确认禁用 / 有效候选 => 仅提供统一版本确认',kind='frontend')

add(28,'simulation-controls-ui','实现数字孪生场景、暂停、步进和事件注入',
    'apps/frontend/src/features/simulation/Page.tsx;apps/frontend/src/features/simulation/Controls.tsx',
    'SimulationPage() -> ReactElement',
    'SimulationView、SimulationControl、EventEnvelope',
    '明确simulation时间与现实时间；control_seq幂等；3D非依赖；仿真注入不修改正式订单。',
    '选场景/版本→启动→轮询→暂停/步进/恢复；事件表单使用typed payload和simulation_id。',
    '暂停t150 => 时钟保持150 / 注入天气事件 => 请求含当前simulation_id',kind='frontend')
add(28,'replay-comparison-ui','实现快照回放和反事实分支对比',
    'apps/frontend/src/features/simulation/Replay.tsx;apps/frontend/src/features/simulation/BranchCompare.tsx',
    'BranchCompare({base,alternative}: BranchCompareProps) -> ReactElement',
    'SimulationSnapshot、ScenarioBranch、MetricDelta',
    '滑块读取快照/回放视图，不能修改历史；分支指标口径一致；尚未接metrics API时只列事件与原始量。',
    '按branch_id隔离缓存；展示事件时间线、订单状态与车辆位置；不同随机策略标注不可直接配对。',
    '查看fork分支 => 原分支轨迹不变 / 恢复t400 => 选中同一快照hash',kind='frontend')

add(29,'exception-center-ui','实现异常列表、影响图和处置流水',
    'apps/frontend/src/features/exceptions/Page.tsx;apps/frontend/src/features/exceptions/ImpactView.tsx',
    'ExceptionCenterPage() -> ReactElement',
    'ExceptionEvent、ImpactReport、DecisionRecordView',
    '完整展示九步链；每个affected task可查看原因路径；人工补充状态不得显示自动修复成功。',
    '事件筛选→详情→影响图→处置阶段日志；来源事实与LLM解释分区标识。',
    'I1 => 显示T1/T2受影响、T3未变 / MANUAL_REQUIRED => 显示缺失字段',kind='frontend')
add(29,'reschedule-diff-ui','实现候选比较、版本差异和重排确认',
    'apps/frontend/src/features/exceptions/CandidateCompare.tsx;apps/frontend/src/features/exceptions/VersionDiff.tsx',
    'VersionDiffView({diff}: VersionDiffViewProps) -> ReactElement',
    'ScheduleDiff、CandidateEvaluation、CommitCommand',
    '必列六项diff字段；原方案、新候选、已确认版本状态区分；失败候选可检查但不能确认。',
    '按服务端排序展示候选；变化任务按稳定ID对齐；确认结果链接新版本及历史版本。',
    '增加200分 => 显示+2元 / constraint_results含硬违规 => 确认禁用',kind='frontend')

add(30,'agent-chat-ui','实现聊天、澄清和工具执行状态页面',
    'apps/frontend/src/features/agent-chat/Page.tsx;apps/frontend/src/features/agent-chat/RunSteps.tsx',
    'AgentChatPage() -> ReactElement',
    'AgentRunView、UserMessage、ClarificationRequest、ToolCallView',
    '展示用户可理解的工具目的和结果；不暴露密钥或模型内部思维；服务端消息作为不可信文本渲染。',
    '发送消息→轮询run→澄清表单→步骤与结果卡；取消run支持；刷新恢复会话。',
    'waiting_input => 展示缺字段且不显示已求解 / 消息含script标签 => 仅文本、不执行',kind='frontend')
add(30,'agent-confirmation-ui','实现有证据的建议确认与风险提示',
    'apps/frontend/src/features/agent-chat/DecisionCard.tsx;apps/frontend/src/features/agent-chat/ConfirmDialog.tsx',
    'DecisionCard({decision}: DecisionCardProps) -> ReactElement',
    'EvidenceExplanation、CandidateRef、ConfirmationToken',
    '卡片数字来自工具结果；只有用户点击确认后向服务端申请/使用绑定令牌；不因模型说已批准而提交。',
    '显示约束检查、版本变化和证据链接；明确确认对象；409/过期令牌要求刷新结果。',
    'LLM文本要求自动批准 => 不触发confirm请求 / 确认成功 => 显示receipt.version_id',kind='frontend')

add(31,'websocket-events','实现带游标的实时事件与断线补偿服务',
    'apps/backend/src/logistics_backend/api/websocket.py;packages/contracts/src/logistics_contracts/realtime.py',
    'WS /api/v1/ws?after_seq=N -> RealtimeEnvelope; GET /api/v1/changes?after_seq=N -> ChangePage',
    'RealtimeEnvelope(seq,event_id,topic,entity_ref,revision,payload)',
    '鉴权/Origin校验；不把密钥放URL；outbox持久化序号；至少一次推送；慢客户端有队列上限。',
    '连接绑定actor范围→补发cursor之后事件→订阅live；过期cursor通知resync；ack不影响业务事务。',
    '断线seq10后发生11/12 => 重连补发11/12 / cursor已清理 => RESYNC_REQUIRED而非静默丢事件')
add(31,'frontend-realtime','实现前端实时订阅与轮询回退',
    'apps/frontend/src/client/realtime.ts;apps/frontend/src/client/realtime-query.ts',
    'subscribeChanges(options: SubscriptionOptions) -> Unsubscribe',
    'RealtimeEnvelope、ChangeCursor、QueryInvalidation',
    'event_id去重、revision阻止倒退；推送只是状态通知，必要时重取服务端视图；保留轮询降级。',
    '退避重连→游标补发→失效query；resync时全量重取；切换用户清空缓存和cursor。',
    'revision5后收到4 => 视图仍为5 / WS关闭 => 轮询继续获得job终态',kind='frontend')

add(32,'metric-calculators','实现14项调度指标与统一统计口径',
    'packages/evaluation/src/logistics_evaluation/metrics.py;packages/contracts/src/logistics_contracts/metrics.py',
    'MetricCalculator.compute(input: EvaluationInput) -> MetricSet',
    'MetricDefinition、EvaluationInput、MetricSet',
    '采用METRICS_CONTRACT；无分母返回null+reason；计划值/仿真值/实际值分开；不漏失败订单。',
    '按订单或任务粒度聚合明确分子分母；合并资源区间再计算利用率；elapsed时间用单调时钟差。',
    '5有效需求、4交付、3按时 => 满足率0.8、准时率0.6 / 无可用dock时间 => 利用率null')
add(32,'metrics-api','实现指标持久化、版本比较与 Dashboard 聚合',
    'apps/backend/src/logistics_backend/application/metrics.py;apps/backend/src/logistics_backend/api/metrics.py',
    'GET /api/v1/metrics?scope_id=ID&source=simulation -> MetricSet; GET /api/v1/dashboard -> DashboardView',
    'MetricSet、MetricDelta、DashboardView、ExperimentResult',
    '同metric version/单位/观察窗才能比较；查询不重跑实验；响应含source、sample_count、coverage。',
    '提交事件/仿真终态触发指标作业；按唯一(scope,source,definition_version)保存；Dashboard聚合已存结果。',
    'actual与planned直接做delta => 拒绝或显式跨源标注 / 同数据重复计算 => 同值无重复记录')
add(32,'metrics-dashboard-ui','实现 Dashboard 与 Metrics 图表页面',
    'apps/frontend/src/features/dashboard/Page.tsx;apps/frontend/src/features/metrics/Page.tsx;apps/frontend/src/features/metrics/MetricChart.tsx',
    'MetricsPage() -> ReactElement; DashboardPage() -> ReactElement',
    'MetricSet、DashboardView、MetricDefinition',
    '显示单位/来源/统计窗/样本数；null不是0；基线与新方案相同尺度；不手算第二套KPI。',
    '接metrics API绘图和可访问数据表；筛选版本/分支；展示失败/缺失数据；错误可重试。',
    'utilization=null => 未定义并显示原因 / 满足率0.8 => 80%且分母5可查看',kind='frontend')

add(33,'experiment-runner','实现对照实验、配对随机种子与结果留档',
    'packages/evaluation/src/logistics_evaluation/experiments.py;packages/evaluation/src/logistics_evaluation/baselines.py;data/experiments/default.json',
    'ExperimentRunner.run(spec: ExperimentSpec) -> ExperimentResultBundle',
    'Experiment、ExperimentSpec、BaselinePolicy、ExperimentResult',
    '对照：规则顺序+确定性可行校验、solver-only、LLM+solver、local重排与all_unexecuted重排；规则候选仅用于隔离实验，若正式采用须先经OR-Tools固定赋值可行性检查再独立校验。',
    '相同数据/预算/硬件/配对seed跑至少10次；失败不删；保存版本/配置/原始结果；聚合中位数、p95、配对差和不确定性。',
    '10次中2次超时 => success_rate=0.8且保留10条 / 两策略使用不同预算 => 标记不可公平比较')
add(33,'experiments-api-ui','实现实验创建、进度、结果与导出工作台',
    'apps/backend/src/logistics_backend/api/experiments.py;apps/frontend/src/features/experiments/Page.tsx;apps/frontend/src/features/experiments/Results.tsx',
    'POST /api/v1/experiments -> JobRef; GET /api/v1/experiments/{id}/results -> ExperimentResultBundle',
    'ExperimentSpec、ExperimentResultBundle、ExperimentExport',
    '这是一个窄端到端切片，只接已实现runner；不能在请求里执行全实验；导出CSV防公式注入。',
    '提交持久job→进度查询→图表/原始表→JSON与CSV导出；绑定definition_version和重复次数。',
    '10条结果含2失败 => 页面展示8/10及失败原因 / CSV名称以=开头 => 安全转义',kind='fullstack')

add(34,'transport-e2e','建立真实数据库运输请求到确认的端到端验收',
    'tests/e2e/transport.spec.ts;tests/integration/test_transport_full_stack.py',
    'T1 -> HTTP job -> real OR-Tools -> validator -> PostgreSQL V1 -> UI',
    '真实服务端到端边界',
    '不用solver fake；浏览器走真实API；隔离测试库；固定矩阵代替外部地图但明确synthetic。',
    '种子数据→创建请求→等待结果→核对路线/成本→确认→重启API读取版本；保存截图和原始结果。',
    'T1 => 9000m、1400分、V1已提交 / 重复确认 => 同receipt而非V2',kind='e2e')
add(34,'joint-exception-e2e','建立仓运联合与异常重排的完整端到端验收',
    'tests/e2e/joint-exception.spec.ts;tests/integration/test_joint_exception_full_stack.py',
    'joint V1 -> simulation event -> impact -> local solve -> validate -> V2 -> diff',
    '联合调度、异常九步链、ScheduleVersion',
    '断言未受影响任务和历史事实不变；真实PostgreSQL/OR-Tools/SimPy；Agent可测试替身但必须标明未验真实模型。',
    '联合确认V1→仿真注入故障→影响与候选→确认V2→对比→恢复快照验证回放；每步追踪同trace链。',
    'I1故障 => T3不变且V1仍可查 / 无救援条件 => 人工处置状态，禁止空路线成功',kind='e2e')
add(34,'failure-recovery-e2e','建立崩溃、并发、模型断线与陈旧提交验收',
    'tests/integration/test_failure_recovery.py;tests/e2e/degraded-mode.spec.ts',
    'FaultInjectionSpec -> RecoveryEvidence',
    'JobLease、Idempotency、Outbox、ActorContext',
    '仅测试环境注入故障；在真实进程边界终止worker；不能模拟返回成功掩盖恢复缺陷。',
    'job处理中终止→重领；DB提交后断推送→补发；LLM不可用→表单求解；同时提交竞争资源。',
    '两请求抢同dock => 一个成功一个409 / 模型不可用 => UI清楚降级且solver流程可完成',kind='e2e')

add(35,'demo-normal','交付 Scenario A 正常冷链运输演示',
    'data/scenarios/demo_a.json;docs/demo/SCENARIO_A.md;scripts/demo_support.py',
    'DemoRunner.run(scenario="demo_a", seed=42) -> DemoEvidence',
    'Scenario A：1仓、2车、8订单、冷藏/冷冻两组',
    '全部硬需求必须满足，温区分车；固定数据来自生成器，不能固定求解答案；展示实际求解结果。',
    '按明确资源容量生成有解实例；种子导入→求解→校验→确认→仿真→指标；记录所有ID与版本。',
    'demo_a => 8/8交付且硬违规0 / 冷冻车不可用且冷冻订单必服务 => 明确无可行候选',kind='scenario')
add(35,'demo-joint','交付 Scenario B 仓储和运输联合演示',
    'data/scenarios/demo_b.json;docs/demo/SCENARIO_B.md',
    'DemoRunner.run(scenario="demo_b", seed=42) -> DemoEvidence',
    'Scenario B：2仓、4车、20订单、温区/库位/月台/人员/分拣及搬运设备',
    '覆盖入库/卸货/分拣/出库/装车；至少一个清洁切换与共享月台瓶颈；整体交接校验必须通过。',
    '创建可手工解释瓶颈的任务链；跑有限反馈；保存每轮窗口、最终联合计划和资源甘特；不要求全局最优。',
    'demo_b => 20单完整链、硬违规0 / 月台[0,horizon)不可用 => 诊断明确引用该月台',kind='scenario')
add(35,'demo-vehicle-failure','交付 Scenario C1 车辆故障局部重排演示',
    'data/scenarios/demo_c_vehicle.json;docs/demo/SCENARIO_C_VEHICLE.md',
    'DemoRunner.run(scenario="demo_c_vehicle", seed=42) -> DemoEvidence',
    'C1：Scenario B分支、故障车、救援车、实物交接',
    '故障时刻为所选车辆真实departure+150秒（I1小例为t150），明示当前位置、剩余货物、救援到达与交接60秒；原版不可覆盖。',
    'V1运行→故障→影响闭包→生成救援候选→局部求解→验证→V2→diff→继续仿真；记录九步链。',
    '故障后 => 无货物瞬移，交接耗时>=60 / 独立车辆无受影响任务 => task字段不变',kind='scenario')
add(35,'demo-order-cancel','交付 Scenario C2 订单取消局部重排演示',
    'data/scenarios/demo_c_cancel.json;docs/demo/SCENARIO_C_CANCEL.md',
    'DemoRunner.run(scenario="demo_c_cancel", seed=42) -> DemoEvidence',
    'C2：未装车取消与在途取消两次独立运行',
    '未装车释放未来预留；在途取消仍保留返仓/交接实物任务；历史交付不可撤回。',
    '分别在装车前和在途快照注入取消；闭包→局部解→差异；展示cancelled需求的指标分母处理。',
    '未装车取消 => 未来交付任务移除 / 在途取消100箱 => 末态库存/返仓数量合计100箱',kind='scenario')
add(35,'demo-weather','交付 Scenario C3 天气变化与一键复现演示包',
    'data/scenarios/demo_c_weather.json;docs/demo/SCENARIO_C_WEATHER.md;scripts/run_demo.py;docs/demo/RUNBOOK.md',
    'python scripts/run_demo.py --scenario all --seed 42 --output artifacts/demo',
    'C3：天气矩阵版本变更、DemoEvidence、ReplayManifest',
    '受影响道路行驶时间倍率3/2，距离不变；只影响尚未发生行程事实；五演示均有运行入口。',
    '注入新矩阵版本→影响→局部解→V2；打包场景/hash/命令/实际结果/截图索引；离线模式不伪称真实LLM在线。',
    '道路100秒 => 新矩阵150秒、旧版本保留 / 同版本同seed重放 => 事件轨迹与指标一致',kind='scenario')

add(36,'benchmark-harness','建立可重复的容量、耗时和内存基准',
    'benchmarks/run.py;benchmarks/profiles.json;docs/performance/BASELINE.md',
    'python benchmarks/run.py --profile mvp --repeat 10 -> BenchmarkReport',
    'BenchmarkProfile、EnvironmentFingerprint、LatencySamples',
    '20单4车2仓为MVP；100单20车4仓为扩展观测；记录CPU/RAM/OS/版本/worker数；性能目标不冒充测量值。',
    '预热后10次计时；分别测排队/构建/求解/校验/持久化；API与worker并发压力；导出p50/p95和峰值RSS。',
    '少于10样本 => 报告不满足基准Gate / 超时样本 => 保留并计入失败率',kind='benchmark')
add(36,'bounded-performance-fix','实现有内存上限的版本化矩阵缓存并复验',
    'packages/optimization/src/logistics_optimization/transport/matrix_cache.py;packages/optimization/src/logistics_optimization/transport/matrix.py;docs/performance/CHANGE_EVIDENCE.md;benchmarks/regression.json',
    'BoundedMatrixCache.get_or_load(query: MatrixQuery, loader: MatrixLoader) -> TravelMatrix',
    'BudgetLedger、MatrixCacheKey、BenchmarkReport',
    '仅实施矩阵缓存的内存上限、LRU淘汰和版本失效；不修改算法语义或公共矩阵接口；基准必须给出前后结果，即使无提速。',
    '以节点顺序/profile/time_bucket/matrix_version为键；默认64MiB上限，计算entry字节成本，超大entry不缓存；独立计算命中率/内存峰值/耗时并复验全部硬约束。',
    '缓存命中但matrix_version改变 => 必须失效 / p95改善却新增硬违规 => Gate失败',kind='benchmark')

add(37,'security-boundary','验证并修复访问控制、输入边界和依赖安全',
    'tests/integration/test_security_boundaries.py;docs/security/BOUNDARY_REVIEW.md',
    'SecurityBoundaryCases -> SecurityEvidence',
    'ActorContext、ObjectScope、ToolPermission、ConfirmationToken',
    '最小viewer/operator已在P05；本任务验证对象级权限/WS Origin/请求限额/注入/XSS/导出注入/密钥处理；不扩成复杂权限系统。',
    '对API/tool/WS同对象权限一致性测试；扫描锁文件依赖和源码密钥；实证缺陷限定补丁文件登记issue并补反例。',
    'viewer直接POST commit => 403 / 枚举他人agent_run_id => 403或一致404')
add(37,'observability-audit','实现全链追踪、指标端点和审计可检索性',
    'apps/backend/src/logistics_backend/observability.py;apps/backend/src/logistics_backend/api/audit.py;docs/operations/OBSERVABILITY.md',
    'GET /metrics -> PrometheusText; GET /api/v1/audit?trace_id=ID -> AuditPage',
    'TraceContext、AuditEntry、MetricLabelPolicy',
    'trace_id贯穿HTTP/Job/Agent/Tool/Solver/Sim/Event/Version；业务ID只放日志和trace不放高基数metric标签；日志脱敏。',
    '结构化JSON日志+OpenTelemetry边界spans+Prometheus低基数指标；审计按追加记录检索；失败路径也发span。',
    'V2 receipt.trace_id => 可查完整事件/工具/求解/提交链 / metric标签含order_id => 检查失败')
add(37,'backup-and-recovery','验证数据库备份恢复、迁移回滚与作业恢复',
    'scripts/backup.ps1;scripts/restore.ps1;docs/operations/RECOVERY.md;tests/integration/test_recovery.py',
    'BackupManifest -> RestoredDatabaseEvidence',
    'ScheduleVersion、InventoryLedger、Event、Outbox、Job',
    '恢复到明确隔离目标库；脚本验证目标并不默认覆盖在线库；备份含版本lineage和事件；记录实测RPO/RTO。',
    '备份测试库→新库恢复→重验hash/FK/版本diff→重领过期job→outbox去重；不可逆迁移用roll-forward说明。',
    '恢复V1/V2 => lineage和diff不变 / 目标库为正式配置且无明确restore参数 => 脚本拒绝')

add(38,'developer-docs','交付与实际实现一致的架构、API和算法文档',
    'docs/DEVELOPER_GUIDE.md;docs/api/IMPLEMENTED_API.md;docs/algorithms/IMPLEMENTED_CAPABILITIES.md',
    'ImplementedCapabilityManifest -> DeveloperDocumentation',
    'Capability、OpenAPI、ContractVersion、GateEvidence',
    '区分设计与实现；运行生成OpenAPI命令；列出未支持约束、原始solver状态口径和迁移方式。',
    '从代码与Gate证据逐条核对能力；文档命令在干净环境执行；链接到真实测试和schema而非聊天。',
    '文档声称multi-compartment但无实现 => 检查失败 / 安装与最小求解示例 => 实际执行成功',kind='docs')
add(38,'operator-docs','交付演示、异常处置、运维和模型配置手册',
    'docs/USER_GUIDE.md;docs/operations/RUNBOOK.md;docs/operations/LLM_CONFIGURATION.md',
    'ReleaseCandidate -> OperatorRunbook',
    '用户角色、三类Demo、错误码、恢复路径',
    '配置示例仅变量名无真密钥；列模型不可用/求解超时/资源冲突处理；3D明确可选。',
    '按安装→导数据→规划→确认→仿真→异常→比较→导出→恢复编排；由未参与开发者按文档复现并记录偏差。',
    '无模型密钥 => 按手册仍能完成结构化Demo A / 遇409 => 手册要求刷新重验而非强制覆盖',kind='docs')

add(39,'release-candidate','生成可安装发布候选及完整性清单',
    'deploy/compose.yml;deploy/backend.Dockerfile;deploy/frontend.Dockerfile;scripts/package_release.py;docs/release/RELEASE_NOTES.md',
    'python scripts/package_release.py --version VERSION -> ReleaseBundle',
    'ReleaseManifest、DependencyLock、SBOM、MigrationRevision',
    '仅本地生成候选；不自动推镜像/部署公网；包含锁版本/迁移/场景/hash/许可证与限制；排除凭据、缓存、私有数据。',
    '构建API+worker+frontend+PostgreSQL本地compose；干净安装跑演示；生成sha256/SBOM/来源；只打包Gate对应revision。',
    '发布包解压到新目录 => 按手册启动并完成A/B/C / 包中检测到.env真实密钥 => 打包失败')
add(39,'release-gate','签收发布 Gate 与复现证据索引',
    'docs/release/RELEASE_ACCEPTANCE.md;docs/release/KNOWN_LIMITATIONS.md;docs/release/EVIDENCE_INDEX.md',
    'ReleaseManifest + G00..G38 + SmokeEvidence -> ReleaseAcceptance',
    'GateEvidence、DemoEvidence、BenchmarkReport、SecurityEvidence',
    '所有核心Gate有效才可签收；本任务生成可审查候选和签收记录；外部发布若将来需要，按当时用户授权执行。',
    '核对产物hash、freshness、五场景、真实LLM smoke证据与离线回退；汇总风险责任人；记录发布版本和回滚点。',
    'G15证据被依赖变更失效 => release失败 / 只有UI截图没有solver结果 => 不可签收',kind='docs')

GROUPS = {
    **{p:'00-master' for p in [0]}, **{p:'01-foundation' for p in [1,4]},
    2:'02-domain',3:'03-database',5:'04-api',16:'04-api',
    **{p:'05-transport-solver' for p in [6,7]},
    **{p:'06-warehouse-solver' for p in [8,9,10]},
    **{p:'07-simulation' for p in [11,12,13]},
    **{p:'08-exception' for p in [14,15]},
    **{p:'09-agents' for p in range(17,24)},
    **{p:'10-frontend' for p in range(24,32)},
    **{p:'11-evaluation' for p in [32,33]},
    **{p:'12-integration' for p in range(34,38)},
    **{p:'13-release' for p in [38,39]},
}

def enrich():
    # Enumerate package markers and generated artifacts; never authorize broad folders.
    bootstrap=TASKS[next(i for i,t in enumerate(TASKS) if t['id']=='P01-01')]
    bootstrap['files'] += [f'packages/{p}/src/logistics_{p}/__init__.py' for p in ('domain','contracts','optimization','simulation','agents','evaluation')]
    bootstrap['files'] += ['apps/backend/src/logistics_backend/__init__.py','playwright.config.ts']
    early_runtime=next(t for t in TASKS if t['id']=='P02-04')
    early_runtime['files'].append('packages/domain/src/logistics_domain/execution.py')
    early_runtime['rule'] += ' P02必须把所有实体引用的纯值类型完整定义，含TwinState/ExecutionEvent/PendingEvent/RngState/AgentBudget/ExperimentSpec；后续领域阶段复用它们，只实现Problem/Request映射和算法，不重复实体。'
    early_runtime['model'] += '；ScenarioSpec、ScenarioRef、ScenarioBundle、Job、JobAttempt、ActorContext、RequestRef、RequestMetadata、JobCommand、JobPayload五分支、JobRequest、JobResultRef、JobFailure及其完整纯值引用；JobKind/JobStatus/JobOptimizationMode只引用P02-01 states.py唯一枚举'
    early_runtime['rule'] += ' N01-R01本轮设计决定见DATA_CONTRACTS及contracts/changes/N01-R01-contract-decisions.json。ScenarioSpec/ScenarioRef/ScenarioBundle、ActorContext、RequestRef/JobCommand/五类payload、Job/JobAttempt/JobResultRef/JobFailure唯一纯值定义归domain/runtime.py；JobRequest等完整边界映射归contracts/runtime.py，供P05和后续任务复用。引用必须固定request_id/version/schema_version/hash/family；JobCommand.kind、payload.family与RequestRef.family一致，optimization额外mode固定transport/warehouse/joint。正式运行输入与场景期望数据隔离；hash复算不接受空值、旧version或改字节。domain不导入contracts或未来P06/P11/P14/P32请求DTO；JobKind/JobStatus/JobOptimizationMode仅复用P02-01 states.py。P03只持久化，P05只实现行为和边界复用；严格schema和真实handler未启用时不装配成功实现、不入队。'
    early_runtime['cases'] += [
        'JobCommand五个kind/family及optimization三个mode映射 => 各自严格解析唯一分支',
        'JobRequest(kind=simulation,payload.family=metric) => 拒绝且不创建Job',
        'RequestRef指向固定版本原字节且sha256一致 => 引用成立',
        '相同request_id/version改字节或空hash => 拒绝',
        'ScenarioRef指向完整版本bundle且运行映射不含期望数据 => 引用成立',
        '正式运行输入携带场景期望解或bundle内容hash不符 => 拒绝',
        '运行纯值导入future请求DTO或contracts.ErrorEnvelope => 层边界与类型闭包检查拒绝',
    ]
    durable_jobs=next(t for t in TASKS if t['id']=='P05-03')
    durable_jobs['cases'] += [
        '元数据hash与固定引用成立且真实schema parser/handler启用 => 幂等提交同job_id',
        '元数据正确但真实schema parser/handler未启用 => 501且不创建Job',
        '引用不存在/旧version/hash不符 => 分别404/409/422且无副作用',
        'completed没有typed result_ref或INFEASIBLE被映射worker failed => 拒绝',
    ]
    definition_rules = {
        'P04-01': ' 复用P02-04完整ScenarioSpec/ScenarioRef/ScenarioBundle纯定义及N01-R01版本/hash/隔离规则；生成内容与期望说明分离，不在本任务创建同名类型，不把期望解交正式运行入口。',
        'P04-02': ' ImportReceipt为本任务cli/seed.py内完整具名CLI导入回执，不是领域实体；字段与拒绝语义按DATA_CONTRACTS及contracts/changes/N01-R01-contract-decisions.json本轮决定实现；复用P02-04 ScenarioBundle，不在P03/P04自造公共类型。',
        'P05-01': ' Settings唯一配置定义放bootstrap.py；HealthResponse/ReadinessResponse边界定义放contracts/http.py；ActorContext纯值复用P02-04并只由认证产生。字段、secret与scope校验按DATA_CONTRACTS及N01-R01本轮决定，不从body自报actor/权限。',
        'P05-02': ' MasterData不是独立类型名；MasterDataService定义在application/master_data.py；MasterDataView是entity_kind/value九个具名响应分支，value映射对应OrderDTO/VehicleDTO/DriverDTO/WarehouseDTO或五类具体资源DTO。MasterDataUpdate/分页请求归contracts/http.py，ResourceDTO与CalendarDTO复用P02-02 contracts/entities.py，不在http.py复制公共DTO或ResourceCalendar。通用calendar端点仅location/dock/worker/equipment；zone无日历字段，返回INVALID_INPUT/422+UnsupportedDetail，不隐式修改仓库日历。完整字段、判别与版本语义按DATA_CONTRACTS及N01-R01本轮决定。',
        'P05-03': ' JobCommand/RequestRef/五分支payload/Job/JobAttempt/JobResultRef/JobFailure及JobRequest边界复用P02-04既有定义，JobKind/JobStatus/JobOptimizationMode复用P02-01 states.py。JobRef/JobView/CancelCommand边界映射仅放contracts/runtime.py；LeaseToken/Deadline/WorkOutcome为application/jobs.py内完整具名工作协议，按DATA_CONTRACTS及N01-R01本轮决定。引用元数据验证不替代真实能力schema；缺真实schema parser/handler开发期501且不入队，缺引用404、旧版本409、hash不符422。P05不导入未来请求DTO；后续能力先严格解析并冻结不可变请求，再封装同一早期JobCommand引用，handler执行前复算hash及租约epoch。',
        'P16-01': ' JobResult边界在contracts/runtime.py映射对应能力已有typed结果并复用P02-04 JobResultRef；应用服务先以本能力严格Schema解析请求、冻结不可变内容并注册元数据，再封装同一JobCommand，不重新定义JobRequest、payload或公共枚举。',
        'P16-02': ' 联合请求先严格解析并冻结不可变内容，以JobKind=optimization和mode=joint封装P02-04 JobCommand；复用早期引用与公共枚举，不在应用层创建第二份JobRequest。',
        'P16-04': ' 仿真请求先严格解析并冻结不可变内容，以JobKind=simulation封装P02-04 JobCommand；复用ScenarioRef/ScenarioBundle定义与期望隔离规则，不把oracle注入运行请求。',
        'P32-02': ' 异步指标作业以JobKind=metric封装P02-04 JobCommand，引用已按P32-01 EvaluationInput严格解析并冻结的请求内容；未实现真实handler不得入队或伪造结果。',
        'P33-02': ' 实验创建以JobKind=experiment封装P02-04 JobCommand，引用已严格解析并冻结的ExperimentSpec；复用早期纯值、版本hash和隔离规则，不创建自由dict payload。',
        'P36-02': ' 按文件分工：B实现matrix.py/matrix_cache.py及tests/solver的缓存正反例；A负责tests/unit、tests/integration、CHANGE_EVIDENCE、regression.json和跨域整合。A是整合主写者，仅整合B交付，不取得B路径编辑权；先B贡献、后A整合、再ZCode独立预验收/G36审查。',
    }
    wiring={
        'P05-01':['apps/backend/src/logistics_backend/api/router.py'],
        'P17-02':['apps/backend/src/logistics_backend/bootstrap.py'],
        'P23-01':['apps/backend/src/logistics_backend/bootstrap.py'],
        'P24-02':['apps/frontend/src/App.tsx'],
        'P26-01':['apps/frontend/src/features/transport/Page.tsx'],
        'P26-02':['apps/frontend/src/features/transport/Page.tsx'],
        'P27-02':['apps/frontend/src/features/warehouse-scheduling/Page.tsx'],
        'P28-02':['apps/frontend/src/features/simulation/Page.tsx'],
        'P29-02':['apps/frontend/src/features/exceptions/Page.tsx'],
        'P30-02':['apps/frontend/src/features/agent-chat/Page.tsx'],
        'P31-02':['apps/frontend/src/App.tsx'],
        'P37-02':['apps/backend/src/logistics_backend/main.py'],
    }
    for t in TASKS:
        t['files']+=wiring.get(t['id'],[])
        t['rule'] += definition_rules.get(t['id'], '')
        if t['id']=='P05-01': t['files'].append('packages/contracts/src/logistics_contracts/http.py')
        if t['id']=='P05-03': t['files'].append('packages/contracts/src/logistics_contracts/runtime.py')
        if t['id']=='P16-01': t['files'].append('packages/contracts/src/logistics_contracts/runtime.py')
        t['prompt'] = f"docs/prompts/{GROUPS[t['phase']]}/{t['id']}-{t['slug']}.md"
        t['phase_gate'] = f"G{t['phase']:02d}"
        if t['phase'] > 0:
            t['deps'].insert(0, f"G{t['phase']-1:02d}")
        short = t['id'].lower().replace('-','_')+'_'+t['slug'].replace('-','_')
        k = t['kind']
        t['unit_test'] = f'tests/unit/test_{short}.py'
        t['integration_test'] = f'tests/integration/test_{short}.py'
        t['special_test'] = f"tests/{'simulation' if k=='simulation' else 'solver'}/test_{short}.py" if k in ('simulation','solver') else None
        if t['id']=='P36-02': t['special_test']=f'tests/solver/test_{short}.py'
        if k in ('frontend','fullstack'):
            t['unit_test'] = f'apps/frontend/src/test/{short}.unit.test.tsx'
            t['integration_test'] = f'apps/frontend/src/test/{short}.integration.test.tsx'
        if k=='docs' and t['phase']==0:
            t['unit_test'] = 'tools/ai_coding_plan/validate_plan.py::run_self_tests'
            t['integration_test'] = f'tools/ai_coding_plan/validate_plan.py --task {t["id"]}'
        t['task_doc'] = f'docs/implementation/{t["id"]}.md'
        t['report'] = f'docs/implementation/reports/{t["id"]}.md'
        t['status'] = 'planned'
        t['owner'] = 'B' if t['phase'] in (6,7,11,12) else 'A'
        if t['id']=='P13-01': t['owner']='A (公共事件服务), B (simulation/events.py；按文件分工)'
        if t['id']=='P36-02': t['owner']='A (基准、回归与整合), B (矩阵源码及缓存验证；按文件分工)'
        if t['phase']==0:
            t['commands']=[f'python tools/ai_coding_plan/validate_plan.py --self-test --task {t["id"]}']
        elif k=='docs':
            t['commands']=[f'uv run pytest {t["unit_test"]} {t["integration_test"]} -q', 'python tools/ai_coding_plan/validate_plan.py']
        elif k in ('frontend','fullstack'):
            names=' '.join(Path(x).name for x in [t['unit_test'],t['integration_test']])
            t['commands']=[f'npm run test --workspace apps/frontend -- --run {names}', 'npm run contracts:check --workspace apps/frontend','npm run build --workspace apps/frontend']
            if k=='fullstack': t['commands'].insert(0,f'uv run pytest tests/integration/test_{short}.py -q')
        else:
            paths=[t['unit_test'],t['integration_test']]+([t['special_test']] if t['special_test'] else [])
            t['commands']=['uv run pytest '+' '.join(paths)+' -q','uv run python scripts/check_architecture.py']
            if k=='e2e':
                spec=next(f for f in t['files'] if f.endswith('.spec.ts'))
                t['commands'].append(f'npm run test:e2e -- {spec}')
        if t['id']=='P01-01':
            t['commands']=[t['commands'][0], 'uv sync --frozen','npm ci']
        if t['kind']=='fullstack':
            t['files'].append(f'tests/integration/test_{short}.py')
        api_producers={'P05-01','P05-02','P05-03','P13-02','P16-01','P16-02','P16-03','P16-04','P23-02','P31-01','P32-02','P33-02','P37-02'}
        if t['id'] in api_producers:
            t['files'].append('contracts/openapi.json')
            t['files']+=['apps/backend/src/logistics_backend/api/router.py','apps/backend/src/logistics_backend/bootstrap.py']
            if t['id']=='P05-01':t['files'].append('scripts/export_contracts.py')
            t['commands'].append('uv run python scripts/export_contracts.py --check')
            if t['phase']>=24:
                t['files'].append('apps/frontend/src/client/generated.ts')
                t['commands'].append('npm run contracts:check --workspace apps/frontend')
        t['files']=sorted(set(t['files']))
        tests=[v for v in [t['unit_test'],t['integration_test'],t['special_test']] if v and '::' not in v and ' --' not in v]
        t['allowed_files']=sorted(set(t['files']+tests+[t['task_doc'],t['report']]))
        if t['id']=='P36-02':
            t['contributions'] = {
                'B': [p for p in t['allowed_files'] if p.startswith(('packages/optimization/', 'tests/solver/'))],
                'A': [p for p in t['allowed_files'] if not p.startswith(('packages/optimization/', 'tests/solver/'))],
            }
            t['integration_owner'] = 'A'
    gates=[dict(id=f'G{p:02d}',phase=p,deps=[t['id'] for t in TASKS if t['phase']==p],status='not_run') for p in range(40)]
    nodes=TASKS+gates
    by_id={t['id']:t for t in nodes}
    for n in nodes: n['blocks']=[q['id'] for q in nodes if n['id'] in q['deps']]
    def ancestors(n):
        found=set()
        def visit(x):
            for d in by_id[x]['deps']:
                if d not in found: found.add(d); visit(d)
        visit(n)
        return found
    for t in TASKS:
        t['parallel']=[q['id'] for q in TASKS if q['id']!=t['id'] and q['phase']==t['phase']
            and q['id'] not in ancestors(t['id']) and t['id'] not in ancestors(q['id'])
            and not(set(t['allowed_files'])&set(q['allowed_files']))]
    return dict(plan_version=PLAN_VERSION,generated_date=GENERATED_DATE,implementation_status='not_started_by_this_plan',
        phase_names=PHASES,tasks=TASKS,gates=gates)

if __name__=='__main__':
    output=ROOT/'docs/plan/TASK_MANIFEST.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(enrich(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Wrote {len(TASKS)} tasks, 40 gates: {output}')
