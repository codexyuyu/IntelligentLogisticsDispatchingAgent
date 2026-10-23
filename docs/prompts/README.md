# 独立Coding Prompt索引

共109个Prompt，40个Phase，14个目录。编号Pxx-yy中的xx是Phase，目录数字不是Phase编号。每个文件可以完整交给新的Codex执行；先核验Dependencies，严格执行Gate。

[返回使用入口](../../AI-CODING-PLAN.md) · [Task Graph](../../TASK_GRAPH.md) · [Gate](../plan/PHASE_GATES.md)

## Phase 00 · 需求冻结与 Architecture Contract

- [P00-01 登记旧 demo 资产与目标目录迁移映射](00-master/P00-01-baseline-inventory.md)
- [P00-02 冻结单位、职责、错误和接口契约](00-master/P00-02-freeze-contracts.md)
- [P00-03 核验任务 DAG 与失败关闭的 Gate 规则](00-master/P00-03-gate-contract.md)

## Phase 01 · Monorepo 与工程基础

- [P01-01 建立目标 Monorepo 与可复现依赖环境](01-foundation/P01-01-workspace-bootstrap.md)
- [P01-02 建立分层检查、CI 与阶段证据执行器](01-foundation/P01-02-checks-and-gate-runner.md)
- [P01-03 建立新路径所有权及旧契约转换验收入口](01-foundation/P01-03-migration-governance.md)

## Phase 02 · Domain Model

- [P02-01 实现领域 ID、单位与唯一状态枚举](02-domain/P02-01-primitives-and-states.md)
- [P02-02 实现订单、货物与运仓资源领域模型](02-domain/P02-02-master-entities.md)
- [P02-03 实现任务、版本与优化结果领域模型](02-domain/P02-03-planning-entities.md)
- [P02-04 实现运行记录模型与 Schema 导出](02-domain/P02-04-runtime-contract-export.md)

## Phase 03 · PostgreSQL Schema + Migration

- [P03-01 创建主数据与资源迁移](03-database/P03-01-resource-schema.md)
- [P03-02 创建不可变计划、运行与审计迁移](03-database/P03-02-planning-schema.md)
- [P03-03 实现快照读取与事务工作单元](03-database/P03-03-repositories-and-snapshot.md)
- [P03-04 实现版本 CAS、资源预留与幂等存储](03-database/P03-04-atomic-version-store.md)

## Phase 04 · Seed / Synthetic Dataset

- [P04-01 生成可手算的合成场景与反例数据](01-foundation/P04-01-canonical-fixtures.md)
- [P04-02 实现可重复执行的数据库种子导入](01-foundation/P04-02-database-seed.md)

## Phase 05 · FastAPI 基础服务

- [P05-01 建立 FastAPI 组合根、错误协议与基础鉴权](04-api/P05-01-api-composition.md)
- [P05-02 实现主数据分页读写服务与资源日历 API](04-api/P05-02-master-data-services.md)
- [P05-03 实现作业租约、超时取消与受限 worker](04-api/P05-03-durable-jobs.md)

## Phase 06 · Transport Optimization Domain

- [P06-01 实现运输请求、结果和 Solver Protocol](05-transport-solver/P06-01-transport-contract.md)
- [P06-02 实现版本化道路距离和时间矩阵提供器](05-transport-solver/P06-02-distance-matrix.md)

## Phase 07 · Transport Solver

- [P07-01 实现多起终点车辆路径基本求解](05-transport-solver/P07-01-vrp-base.md)
- [P07-02 实现重量、容积和提送货载荷约束](05-transport-solver/P07-02-capacity-and-pickup.md)
- [P07-03 实现服务时间、等待、班次与硬时间窗](05-transport-solver/P07-03-time-windows.md)
- [P07-04 实现温区、货物类型与车辆允许集合](05-transport-solver/P07-04-temperature-and-cargo.md)
- [P07-05 实现可解释费用与可选订单目标函数](05-transport-solver/P07-05-objective-function.md)
- [P07-06 实现运输结果提取、状态映射和独立重算](05-transport-solver/P07-06-result-status-validation.md)
- [P07-07 装配运输 Solver 并验证数值与预算边界](05-transport-solver/P07-07-transport-adapter.md)

## Phase 08 · Warehouse Optimization Domain

- [P08-01 实现仓储任务与资源日历协议](06-warehouse-solver/P08-01-warehouse-contract.md)
- [P08-02 实现库存占用和仓运交接约束模型](06-warehouse-solver/P08-02-inventory-and-handoffs.md)

## Phase 09 · Warehouse Scheduler

- [P09-01 实现仓储区间、互斥资源与任务依赖](06-warehouse-solver/P09-01-intervals-precedence.md)
- [P09-02 实现人员、设备和温区容量限制](06-warehouse-solver/P09-02-cumulative-resources.md)
- [P09-03 实现库位库存区间和冷链容量约束](06-warehouse-solver/P09-03-storage-capacity.md)
- [P09-04 实现清洁及月台、温区、分拣切换时间](06-warehouse-solver/P09-04-sequence-setup.md)
- [P09-05 装配仓储目标、结果提取与独立校验](06-warehouse-solver/P09-05-warehouse-result.md)

## Phase 10 · Constraint Validator

- [P10-01 实现统一校验报告与约束覆盖注册表](06-warehouse-solver/P10-01-validator-protocol.md)
- [P10-02 实现跨仓运链、库存和资源完整校验](06-warehouse-solver/P10-02-joint-validator.md)
- [P10-03 建立独立硬约束反例与小规模 oracle 套件](06-warehouse-solver/P10-03-validator-adversarial-suite.md)

## Phase 11 · Simulation Domain

- [P11-01 实现仿真场景、状态、快照与随机源契约](07-simulation/P11-01-simulation-contract.md)
- [P11-02 实现订单、车辆和仓库执行状态转换](07-simulation/P11-02-execution-state-machine.md)

## Phase 12 · SimPy Digital Twin

- [P12-01 实现 SimPy 时间推进与稳定事件调度内核](07-simulation/P12-01-simpy-kernel.md)
- [P12-02 实现车辆移动、服务与订单交付过程](07-simulation/P12-02-transport-execution.md)
- [P12-03 实现仓储资源争用、作业与库存演化](07-simulation/P12-03-warehouse-execution.md)
- [P12-04 实现快照恢复和反事实分支隔离](07-simulation/P12-04-snapshot-replay.md)

## Phase 13 · Event Engine

- [P13-01 实现十类异常事件的校验、去重与排序](07-simulation/P13-01-event-ingestion.md)
- [P13-02 实现事件注入服务及持久化分发](07-simulation/P13-02-event-api-and-outbox.md)

## Phase 14 · Exception Impact Analyzer

- [P14-01 实现异常影响依赖图与最小闭包](08-exception/P14-01-impact-graph.md)
- [P14-02 实现不可逆事实、在途起点与重排边界提取](08-exception/P14-02-execution-freeze.md)

## Phase 15 · Local Rescheduling Engine

- [P15-01 实现局部候选策略与救援交接任务生成](08-exception/P15-01-candidate-policies.md)
- [P15-02 实现冻结边界下的局部重新求解](08-exception/P15-02-local-solve.md)
- [P15-03 实现局部扩展与全局剩余任务降级策略](08-exception/P15-03-bounded-escalation.md)
- [P15-04 实现版本差异与候选排序](08-exception/P15-04-version-diff.md)

## Phase 16 · Optimization API

- [P16-01 实现运输、仓储和重排作业 API](04-api/P16-01-optimization-job-api.md)
- [P16-02 实现有界仓运窗口反馈协调服务](04-api/P16-02-joint-planning-service.md)
- [P16-03 实现重新校验后的版本确认服务](04-api/P16-03-validated-commit-api.md)
- [P16-04 实现仿真控制、版本对比与结果查询 API](04-api/P16-04-simulation-query-api.md)

## Phase 17 · Agent Tool Protocol

- [P17-01 实现 Agent 标准工具注册、权限与参数协议](09-agents/P17-01-tool-schemas.md)
- [P17-02 实现工具到业务服务的唯一适配层](09-agents/P17-02-business-tools.md)

## Phase 18 · LLM Provider Abstraction

- [P18-01 实现模型供应商抽象与结构化响应边界](09-agents/P18-01-llm-provider.md)
- [P18-02 实现模型预算、重试、脱敏与故障降级](09-agents/P18-02-llm-resilience.md)

## Phase 19 · Coordinator Agent

- [P19-01 实现 Coordinator 意图及约束抽取](09-agents/P19-01-intent-extraction.md)
- [P19-02 实现 Coordinator 任务分解与有界运行状态机](09-agents/P19-02-coordinator-state-machine.md)

## Phase 20 · Transport Agent

- [P20-01 实现 TransportAgent 求解工具工作流](09-agents/P20-01-transport-agent-tools.md)
- [P20-02 实现有证据的运输结果解释](09-agents/P20-02-transport-explanation.md)

## Phase 21 · Warehouse Agent

- [P21-01 实现 WarehouseAgent 排程与窗口报价工作流](09-agents/P21-01-warehouse-agent-tools.md)
- [P21-02 实现仓储甘特与资源瓶颈解释数据](09-agents/P21-02-warehouse-explanation.md)

## Phase 22 · Exception Agent

- [P22-01 实现 ExceptionAgent 九步处置工作流](09-agents/P22-01-exception-agent-tools.md)
- [P22-02 实现异常处置链和版本差异解释](09-agents/P22-02-exception-explanation.md)

## Phase 23 · Agent Orchestration

- [P23-01 实现四角色路由、取消与有界协调](09-agents/P23-01-agent-orchestration.md)
- [P23-02 实现 Agent 会话 API 与攻击性输入验收](09-agents/P23-02-agent-api-safety.md)

## Phase 24 · React Application Shell

- [P24-01 建立 React 应用壳、路由与统一状态展示](10-frontend/P24-01-react-shell.md)
- [P24-02 建立 OpenAPI 生成客户端和数据请求层](10-frontend/P24-02-generated-api-client.md)

## Phase 25 · Orders / Vehicles / Warehouses UI

- [P25-01 实现订单查询、编辑和取消事件入口](10-frontend/P25-01-orders-ui.md)
- [P25-02 实现车辆、司机和可用日历页面](10-frontend/P25-02-vehicles-ui.md)
- [P25-03 实现仓库、温区、库位及作业资源页面](10-frontend/P25-03-warehouses-ui.md)

## Phase 26 · Transport Scheduling UI

- [P26-01 实现运输请求、作业进度与不可行诊断页面](10-frontend/P26-01-transport-request-ui.md)
- [P26-02 实现路线、逐站执行表和候选确认视图](10-frontend/P26-02-transport-plan-ui.md)

## Phase 27 · Warehouse Scheduling UI

- [P27-01 实现仓储请求和资源甘特图](10-frontend/P27-01-warehouse-gantt-ui.md)
- [P27-02 实现仓运交接与联合方案对照视图](10-frontend/P27-02-joint-handoff-ui.md)

## Phase 28 · Digital Twin UI

- [P28-01 实现数字孪生场景、暂停、步进和事件注入](10-frontend/P28-01-simulation-controls-ui.md)
- [P28-02 实现快照回放和反事实分支对比](10-frontend/P28-02-replay-comparison-ui.md)

## Phase 29 · Exception Center UI

- [P29-01 实现异常列表、影响图和处置流水](10-frontend/P29-01-exception-center-ui.md)
- [P29-02 实现候选比较、版本差异和重排确认](10-frontend/P29-02-reschedule-diff-ui.md)

## Phase 30 · Agent Chat UI

- [P30-01 实现聊天、澄清和工具执行状态页面](10-frontend/P30-01-agent-chat-ui.md)
- [P30-02 实现有证据的建议确认与风险提示](10-frontend/P30-02-agent-confirmation-ui.md)

## Phase 31 · WebSocket Real-time System

- [P31-01 实现带游标的实时事件与断线补偿服务](10-frontend/P31-01-websocket-events.md)
- [P31-02 实现前端实时订阅与轮询回退](10-frontend/P31-02-frontend-realtime.md)

## Phase 32 · Metrics / Evaluation

- [P32-01 实现14项调度指标与统一统计口径](11-evaluation/P32-01-metric-calculators.md)
- [P32-02 实现指标持久化、版本比较与 Dashboard 聚合](11-evaluation/P32-02-metrics-api.md)
- [P32-03 实现 Dashboard 与 Metrics 图表页面](11-evaluation/P32-03-metrics-dashboard-ui.md)

## Phase 33 · Experiment Framework

- [P33-01 实现对照实验、配对随机种子与结果留档](11-evaluation/P33-01-experiment-runner.md)
- [P33-02 实现实验创建、进度、结果与导出工作台](11-evaluation/P33-02-experiments-api-ui.md)

## Phase 34 · End-to-End Integration

- [P34-01 建立真实数据库运输请求到确认的端到端验收](12-integration/P34-01-transport-e2e.md)
- [P34-02 建立仓运联合与异常重排的完整端到端验收](12-integration/P34-02-joint-exception-e2e.md)
- [P34-03 建立崩溃、并发、模型断线与陈旧提交验收](12-integration/P34-03-failure-recovery-e2e.md)

## Phase 35 · Demo Scenario

- [P35-01 交付 Scenario A 正常冷链运输演示](12-integration/P35-01-demo-normal.md)
- [P35-02 交付 Scenario B 仓储和运输联合演示](12-integration/P35-02-demo-joint.md)
- [P35-03 交付 Scenario C1 车辆故障局部重排演示](12-integration/P35-03-demo-vehicle-failure.md)
- [P35-04 交付 Scenario C2 订单取消局部重排演示](12-integration/P35-04-demo-order-cancel.md)
- [P35-05 交付 Scenario C3 天气变化与一键复现演示包](12-integration/P35-05-demo-weather.md)

## Phase 36 · Performance Optimization

- [P36-01 建立可重复的容量、耗时和内存基准](12-integration/P36-01-benchmark-harness.md)
- [P36-02 实现有内存上限的版本化矩阵缓存并复验](12-integration/P36-02-bounded-performance-fix.md)

## Phase 37 · Security / Audit / Observability

- [P37-01 验证并修复访问控制、输入边界和依赖安全](12-integration/P37-01-security-boundary.md)
- [P37-02 实现全链追踪、指标端点和审计可检索性](12-integration/P37-02-observability-audit.md)
- [P37-03 验证数据库备份恢复、迁移回滚与作业恢复](12-integration/P37-03-backup-and-recovery.md)

## Phase 38 · Documentation

- [P38-01 交付与实际实现一致的架构、API和算法文档](13-release/P38-01-developer-docs.md)
- [P38-02 交付演示、异常处置、运维和模型配置手册](13-release/P38-02-operator-docs.md)

## Phase 39 · Release

- [P39-01 生成可安装发布候选及完整性清单](13-release/P39-01-release-candidate.md)
- [P39-02 签收发布 Gate 与复现证据索引](13-release/P39-02-release-gate.md)
