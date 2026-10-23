# Task Graph · 严格阶段屏障下的DAG

共109个独立Task、40个Gate节点。箭头为先完成→后启动。机器事实见[任务清单](docs/plan/TASK_MANIFEST.json)。所有Task初始planned，Gate初始not_run；下表不是实时项目状态，也未修改外部Linear。

Dependencies列包含前阶段Gate以及必要同阶段任务；每个Gate依赖本阶段全部Task。Blocks是直接反向边（并非所有传递后继）。Can Run In Parallel只列同阶段无传递依赖且写文件不冲突的候选；启动时仍要求各自所有Dependencies有效。未通过Gate不能通过并行跳阶段。

```mermaid
flowchart LR
  G00 -->|依次通过中间各Gate| G05
  G05 -->|依次通过中间各Gate| G10
  G10 -->|依次通过中间各Gate| G16
  G16 -->|依次通过中间各Gate| G23
  G23 -->|依次通过中间各Gate| G33
  G33 -->|依次通过中间各Gate| G35
  G35 -->|依次通过中间各Gate| G39
```

以上仅为里程碑Gate投影，连线不能跳过中间Gate；完整可机读任务边在manifest，下表列出全部149个Task/Gate节点。

## Phase 00 · 需求冻结与 Architecture Contract

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P00-01 · 登记旧 demo 资产与目标目录迁移映射](docs/prompts/00-master/P00-01-baseline-inventory.md) |  | P00-02, G00 | 无 |
| [P00-02 · 冻结单位、职责、错误和接口契约](docs/prompts/00-master/P00-02-freeze-contracts.md) | P00-01 | P00-03, G00 | 无 |
| [P00-03 · 核验任务 DAG 与失败关闭的 Gate 规则](docs/prompts/00-master/P00-03-gate-contract.md) | P00-02 | G00 | 无 |
| **G00：阶段验收证据** | P00-01, P00-02, P00-03 | P01-01, P01-02, P01-03 | 无，屏障 |

旧demo资产有逐项证据；单位/32实体/错误/Protocol冻结；任务DAG与需求追踪无缺口，G00签收不能用本轮静态报告替代。

## Phase 01 · Monorepo 与工程基础

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P01-01 · 建立目标 Monorepo 与可复现依赖环境](docs/prompts/01-foundation/P01-01-workspace-bootstrap.md) | G00 | P01-02, G01 | 无 |
| [P01-02 · 建立分层检查、CI 与阶段证据执行器](docs/prompts/01-foundation/P01-02-checks-and-gate-runner.md) | G00, P01-01 | P01-03, G01 | 无 |
| [P01-03 · 建立新路径所有权及旧契约转换验收入口](docs/prompts/01-foundation/P01-03-migration-governance.md) | G00, P01-02 | G01 | 无 |
| **G01：阶段验收证据** | P01-01, P01-02, P01-03 | P02-01, P02-02, P02-03, P02-04 | 无，屏障 |

干净安装、六包导入与分层检查通过；依赖锁可复现；Gate执行器非零命令必失败；旧demo未被覆盖。

## Phase 02 · Domain Model

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P02-01 · 实现领域 ID、单位与唯一状态枚举](docs/prompts/02-domain/P02-01-primitives-and-states.md) | G01 | P02-02, G02 | 无 |
| [P02-02 · 实现订单、货物与运仓资源领域模型](docs/prompts/02-domain/P02-02-master-entities.md) | G01, P02-01 | P02-03, G02 | 无 |
| [P02-03 · 实现任务、版本与优化结果领域模型](docs/prompts/02-domain/P02-03-planning-entities.md) | G01, P02-02 | P02-04, G02 | 无 |
| [P02-04 · 实现运行记录模型与 Schema 导出](docs/prompts/02-domain/P02-04-runtime-contract-export.md) | G01, P02-03 | G02 | 无 |
| **G02：阶段验收证据** | P02-01, P02-02, P02-03, P02-04 | P03-01, P03-02, P03-03, P03-04 | 无，屏障 |

32实体及辅助记录可表达，非法状态/单位/额外字段拒绝；Schema确定导出；domain无框架依赖。

## Phase 03 · PostgreSQL Schema + Migration

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P03-01 · 创建主数据与资源迁移](docs/prompts/03-database/P03-01-resource-schema.md) | G02 | P03-02, G03 | 无 |
| [P03-02 · 创建不可变计划、运行与审计迁移](docs/prompts/03-database/P03-02-planning-schema.md) | G02, P03-01 | P03-03, G03 | 无 |
| [P03-03 · 实现快照读取与事务工作单元](docs/prompts/03-database/P03-03-repositories-and-snapshot.md) | G02, P03-02 | P03-04, G03 | 无 |
| [P03-04 · 实现版本 CAS、资源预留与幂等存储](docs/prompts/03-database/P03-04-atomic-version-store.md) | G02, P03-03 | G03 | 无 |
| **G03：阶段验收证据** | P03-01, P03-02, P03-03, P03-04 | P04-01, P04-02 | 无，屏障 |

真实PostgreSQL迁移、回滚与FK通过；一致快照；最后一份资源并发提交恰一成功；事务失败无半版本。

## Phase 04 · Seed / Synthetic Dataset

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P04-01 · 生成可手算的合成场景与反例数据](docs/prompts/01-foundation/P04-01-canonical-fixtures.md) | G03 | P04-02, G04 | 无 |
| [P04-02 · 实现可重复执行的数据库种子导入](docs/prompts/01-foundation/P04-02-database-seed.md) | G03, P04-01 | G04 | 无 |
| **G04：阶段验收证据** | P04-01, P04-02 | P05-01, P05-02, P05-03 | 无，屏障 |

T1/W1/I1/M1数据hash可复现；反例各有原因；同种子二次导入不重复，不清空既有库。

## Phase 05 · FastAPI 基础服务

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P05-01 · 建立 FastAPI 组合根、错误协议与基础鉴权](docs/prompts/04-api/P05-01-api-composition.md) | G04 | P05-02, G05 | 无 |
| [P05-02 · 实现主数据分页读写服务与资源日历 API](docs/prompts/04-api/P05-02-master-data-services.md) | G04, P05-01 | P05-03, G05 | 无 |
| [P05-03 · 实现作业租约、超时取消与受限 worker](docs/prompts/04-api/P05-03-durable-jobs.md) | G04, P05-02 | G05 | 无 |
| **G05：阶段验收证据** | P05-01, P05-02, P05-03 | P06-01, P06-02 | 无，屏障 |

API认证、错误、分页、revision与持久Job可验收；杀worker后租约可重领；无长求解阻塞请求。

## Phase 06 · Transport Optimization Domain

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P06-01 · 实现运输请求、结果和 Solver Protocol](docs/prompts/05-transport-solver/P06-01-transport-contract.md) | G05 | G06 | P06-02 |
| [P06-02 · 实现版本化道路距离和时间矩阵提供器](docs/prompts/05-transport-solver/P06-02-distance-matrix.md) | G05 | G06 | P06-01 |
| **G06：阶段验收证据** | P06-01, P06-02 | P07-01, P07-02, P07-03, P07-04, P07-05, P07-06, P07-07 | 无，屏障 |

运输typed输入/矩阵节点顺序/版本明确；不可达与0区分；天气倍率100→150秒可手算。

## Phase 07 · Transport Solver

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P07-01 · 实现多起终点车辆路径基本求解](docs/prompts/05-transport-solver/P07-01-vrp-base.md) | G06 | P07-02, G07 | 无 |
| [P07-02 · 实现重量、容积和提送货载荷约束](docs/prompts/05-transport-solver/P07-02-capacity-and-pickup.md) | G06, P07-01 | P07-03, G07 | 无 |
| [P07-03 · 实现服务时间、等待、班次与硬时间窗](docs/prompts/05-transport-solver/P07-03-time-windows.md) | G06, P07-02 | P07-04, G07 | 无 |
| [P07-04 · 实现温区、货物类型与车辆允许集合](docs/prompts/05-transport-solver/P07-04-temperature-and-cargo.md) | G06, P07-03 | P07-05, G07 | 无 |
| [P07-05 · 实现可解释费用与可选订单目标函数](docs/prompts/05-transport-solver/P07-05-objective-function.md) | G06, P07-04 | P07-06, G07 | 无 |
| [P07-06 · 实现运输结果提取、状态映射和独立重算](docs/prompts/05-transport-solver/P07-06-result-status-validation.md) | G06, P07-05 | P07-07, G07 | 无 |
| [P07-07 · 装配运输 Solver 并验证数值与预算边界](docs/prompts/05-transport-solver/P07-07-transport-adapter.md) | G06, P07-06 | G07 | 无 |
| **G07：阶段验收证据** | P07-01, P07-02, P07-03, P07-04, P07-05, P07-06, P07-07 | P08-01, P08-02 | 无，屏障 |

真实OR-Tools T1=9000m/1400分；容量/提送/硬窗/温区/状态各有反例；独立校验通过，无假成功。

## Phase 08 · Warehouse Optimization Domain

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P08-01 · 实现仓储任务与资源日历协议](docs/prompts/06-warehouse-solver/P08-01-warehouse-contract.md) | G07 | P08-02, G08 | 无 |
| [P08-02 · 实现库存占用和仓运交接约束模型](docs/prompts/06-warehouse-solver/P08-02-inventory-and-handoffs.md) | G07, P08-01 | G08 | 无 |
| **G08：阶段验收证据** | P08-01, P08-02 | P09-01, P09-02, P09-03, P09-04, P09-05 | 无，屏障 |

五类仓储作业、所有资源与库存/交接具名；DAG环拒绝；初始库存与存储区间契约可验证。

## Phase 09 · Warehouse Scheduler

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P09-01 · 实现仓储区间、互斥资源与任务依赖](docs/prompts/06-warehouse-solver/P09-01-intervals-precedence.md) | G08 | P09-02, G09 | 无 |
| [P09-02 · 实现人员、设备和温区容量限制](docs/prompts/06-warehouse-solver/P09-02-cumulative-resources.md) | G08, P09-01 | P09-03, G09 | 无 |
| [P09-03 · 实现库位库存区间和冷链容量约束](docs/prompts/06-warehouse-solver/P09-03-storage-capacity.md) | G08, P09-02 | P09-04, G09 | 无 |
| [P09-04 · 实现清洁及月台、温区、分拣切换时间](docs/prompts/06-warehouse-solver/P09-04-sequence-setup.md) | G08, P09-03 | P09-05, G09 | 无 |
| [P09-05 · 装配仓储目标、结果提取与独立校验](docs/prompts/06-warehouse-solver/P09-05-warehouse-result.md) | G08, P09-04 | G09 | 无 |
| **G09：阶段验收证据** | P09-01, P09-02, P09-03, P09-04, P09-05 | P10-01, P10-02, P10-03 | 无，屏障 |

真实CP-SAT W1=25秒；工序/资源/库存/setup反例通过；UNKNOWN不当INFEASIBLE；返回资源时间轴。

## Phase 10 · Constraint Validator

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P10-01 · 实现统一校验报告与约束覆盖注册表](docs/prompts/06-warehouse-solver/P10-01-validator-protocol.md) | G09 | P10-02, G10 | 无 |
| [P10-02 · 实现跨仓运链、库存和资源完整校验](docs/prompts/06-warehouse-solver/P10-02-joint-validator.md) | G09, P10-01 | P10-03, G10 | 无 |
| [P10-03 · 建立独立硬约束反例与小规模 oracle 套件](docs/prompts/06-warehouse-solver/P10-03-validator-adversarial-suite.md) | G09, P10-02 | G10 | 无 |
| **G10：阶段验收证据** | P10-01, P10-02, P10-03 | P11-01, P11-02 | 无，屏障 |

所有required硬约束有checked或unsupported记录；J1联合冲突检出；每条硬约束单点破坏反例检出。

## Phase 11 · Simulation Domain

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P11-01 · 实现仿真场景、状态、快照与随机源契约](docs/prompts/07-simulation/P11-01-simulation-contract.md) | G10 | P11-02, G11 | 无 |
| [P11-02 · 实现订单、车辆和仓库执行状态转换](docs/prompts/07-simulation/P11-02-execution-state-machine.md) | G10, P11-01 | G11 | 无 |
| **G11：阶段验收证据** | P11-01, P11-02 | P12-01, P12-02, P12-03, P12-04 | 无，屏障 |

仿真状态/事件/RNG/快照类型冻结；非法执行状态拒绝；计划和真实执行事实分离。

## Phase 12 · SimPy Digital Twin

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P12-01 · 实现 SimPy 时间推进与稳定事件调度内核](docs/prompts/07-simulation/P12-01-simpy-kernel.md) | G11 | P12-02, P12-03, G12 | 无 |
| [P12-02 · 实现车辆移动、服务与订单交付过程](docs/prompts/07-simulation/P12-02-transport-execution.md) | G11, P12-01 | P12-04, G12 | P12-03 |
| [P12-03 · 实现仓储资源争用、作业与库存演化](docs/prompts/07-simulation/P12-03-warehouse-execution.md) | G11, P12-01 | P12-04, G12 | P12-02 |
| [P12-04 · 实现快照恢复和反事实分支隔离](docs/prompts/07-simulation/P12-04-snapshot-replay.md) | G11, P12-02, P12-03 | G12 | 无 |
| **G12：阶段验收证据** | P12-01, P12-02, P12-03, P12-04 | P13-01, P13-02 | 无，屏障 |

真实SimPy T1终态1020秒；t400恢复一致；同秒事件稳定排序；分支隔离、资源无死锁、取消无伪完成。

## Phase 13 · Event Engine

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P13-01 · 实现十类异常事件的校验、去重与排序](docs/prompts/07-simulation/P13-01-event-ingestion.md) | G12 | P13-02, G13 | 无 |
| [P13-02 · 实现事件注入服务及持久化分发](docs/prompts/07-simulation/P13-02-event-api-and-outbox.md) | G12, P13-01 | G13 | 无 |
| **G13：阶段验收证据** | P13-01, P13-02 | P14-01, P14-02 | 无，屏障 |

十类异常payload全覆盖；重复去重、乱序/迟到有明确处理；事件与outbox原子保存。

## Phase 14 · Exception Impact Analyzer

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P14-01 · 实现异常影响依赖图与最小闭包](docs/prompts/08-exception/P14-01-impact-graph.md) | G13 | P14-02, G14 | 无 |
| [P14-02 · 实现不可逆事实、在途起点与重排边界提取](docs/prompts/08-exception/P14-02-execution-freeze.md) | G13, P14-01 | G14 | 无 |
| **G14：阶段验收证据** | P14-01, P14-02 | P15-01, P15-02, P15-03, P15-04 | 无，屏障 |

I1闭包只有T1/T2；T3冻结；在途起点和剩余载荷真实；已执行事实不可改写。

## Phase 15 · Local Rescheduling Engine

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P15-01 · 实现局部候选策略与救援交接任务生成](docs/prompts/08-exception/P15-01-candidate-policies.md) | G14 | P15-02, G15 | 无 |
| [P15-02 · 实现冻结边界下的局部重新求解](docs/prompts/08-exception/P15-02-local-solve.md) | G14, P15-01 | P15-03, G15 | 无 |
| [P15-03 · 实现局部扩展与全局剩余任务降级策略](docs/prompts/08-exception/P15-03-bounded-escalation.md) | G14, P15-02 | P15-04, G15 | 无 |
| [P15-04 · 实现版本差异与候选排序](docs/prompts/08-exception/P15-04-version-diff.md) | G14, P15-03 | G15 | 无 |
| **G15：阶段验收证据** | P15-01, P15-02, P15-03, P15-04 | P16-01, P16-02, P16-03, P16-04 | 无，屏障 |

局部→扩大→全局剩余共享预算；救援无瞬移；完整合并方案重验；六项diff正确；失败给诊断/暂停建议。

## Phase 16 · Optimization API

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P16-01 · 实现运输、仓储和重排作业 API](docs/prompts/04-api/P16-01-optimization-job-api.md) | G15 | P16-02, G16 | 无 |
| [P16-02 · 实现有界仓运窗口反馈协调服务](docs/prompts/04-api/P16-02-joint-planning-service.md) | G15, P16-01 | P16-03, G16 | 无 |
| [P16-03 · 实现重新校验后的版本确认服务](docs/prompts/04-api/P16-03-validated-commit-api.md) | G15, P16-02 | P16-04, G16 | 无 |
| [P16-04 · 实现仿真控制、版本对比与结果查询 API](docs/prompts/04-api/P16-04-simulation-query-api.md) | G15, P16-03 | G16 | 无 |
| **G16：阶段验收证据** | P16-01, P16-02, P16-03, P16-04 | P17-01, P17-02 | 无，屏障 |

运输/仓储/联合/重排/仿真API真实连通；J1反馈消除交接冲突；并发/过期确认409；V1不覆盖。

## Phase 17 · Agent Tool Protocol

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P17-01 · 实现 Agent 标准工具注册、权限与参数协议](docs/prompts/09-agents/P17-01-tool-schemas.md) | G16 | P17-02, G17 | 无 |
| [P17-02 · 实现工具到业务服务的唯一适配层](docs/prompts/09-agents/P17-02-business-tools.md) | G16, P17-01 | G17 | 无 |
| **G17：阶段验收证据** | P17-01, P17-02 | P18-01, P18-02 | 无，屏障 |

白名单Tool typed args/role/scope/deadline/幂等生效；不直写数据库；未确认commit被拒绝。

## Phase 18 · LLM Provider Abstraction

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P18-01 · 实现模型供应商抽象与结构化响应边界](docs/prompts/09-agents/P18-01-llm-provider.md) | G17 | P18-02, G18 | 无 |
| [P18-02 · 实现模型预算、重试、脱敏与故障降级](docs/prompts/09-agents/P18-02-llm-resilience.md) | G17, P18-01 | G18 | 无 |
| **G18：阶段验收证据** | P18-01, P18-02 | P19-01, P19-02 | 无，屏障 |

真实供应商适配契约smoke有脱敏证据；schema/429/超时/预算/无密钥降级通过；fake不能冒充真实smoke。

## Phase 19 · Coordinator Agent

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P19-01 · 实现 Coordinator 意图及约束抽取](docs/prompts/09-agents/P19-01-intent-extraction.md) | G18 | P19-02, G19 | 无 |
| [P19-02 · 实现 Coordinator 任务分解与有界运行状态机](docs/prompts/09-agents/P19-02-coordinator-state-machine.md) | G18, P19-01 | G19 | 无 |
| **G19：阶段验收证据** | P19-01, P19-02 | P20-01, P20-02 | 无，屏障 |

意图抽取保留原文/实体证据；缺字段先澄清；有界状态机在预算耗尽停止，不自造ID。

## Phase 20 · Transport Agent

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P20-01 · 实现 TransportAgent 求解工具工作流](docs/prompts/09-agents/P20-01-transport-agent-tools.md) | G19 | P20-02, G20 | 无 |
| [P20-02 · 实现有证据的运输结果解释](docs/prompts/09-agents/P20-02-transport-explanation.md) | G19, P20-01 | G20 | 无 |
| **G20：阶段验收证据** | P20-01, P20-02 | P21-01, P21-02 | 无，屏障 |

TransportAgent仅通过工具取得候选；无解不造路线；T1数值解释与证据一致。

## Phase 21 · Warehouse Agent

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P21-01 · 实现 WarehouseAgent 排程与窗口报价工作流](docs/prompts/09-agents/P21-01-warehouse-agent-tools.md) | G20 | P21-02, G21 | 无 |
| [P21-02 · 实现仓储甘特与资源瓶颈解释数据](docs/prompts/09-agents/P21-02-warehouse-explanation.md) | G20, P21-01 | G21 | 无 |
| **G21：阶段验收证据** | P21-01, P21-02 | P22-01, P22-02 | 无，屏障 |

WarehouseAgent报价非预留且会过期；资源瓶颈解释引用真实任务/诊断，不能杜撰利用率。

## Phase 22 · Exception Agent

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P22-01 · 实现 ExceptionAgent 九步处置工作流](docs/prompts/09-agents/P22-01-exception-agent-tools.md) | G21 | P22-02, G22 | 无 |
| [P22-02 · 实现异常处置链和版本差异解释](docs/prompts/09-agents/P22-02-exception-explanation.md) | G21, P22-01 | G22 | 无 |
| **G22：阶段验收证据** | P22-01, P22-02 | P23-01, P23-02 | 无，屏障 |

ExceptionAgent九步有完整记录；缺救援数据manual_required；解释区分建议与已确认版本。

## Phase 23 · Agent Orchestration

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P23-01 · 实现四角色路由、取消与有界协调](docs/prompts/09-agents/P23-01-agent-orchestration.md) | G22 | P23-02, G23 | 无 |
| [P23-02 · 实现 Agent 会话 API 与攻击性输入验收](docs/prompts/09-agents/P23-02-agent-api-safety.md) | G22, P23-01 | G23 | 无 |
| **G23：阶段验收证据** | P23-01, P23-02 | P24-01, P24-02 | 无，屏障 |

四角色有界协调、父取消传播、工具注入/越权拒绝；确认令牌绑定对象/actor/revision并防重放。

## Phase 24 · React Application Shell

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P24-01 · 建立 React 应用壳、路由与统一状态展示](docs/prompts/10-frontend/P24-01-react-shell.md) | G23 | P24-02, G24 | 无 |
| [P24-02 · 建立 OpenAPI 生成客户端和数据请求层](docs/prompts/10-frontend/P24-02-generated-api-client.md) | G23, P24-01 | G24 | 无 |
| **G24：阶段验收证据** | P24-01, P24-02 | P25-01, P25-02, P25-03 | 无，屏障 |

11导航可达；375px可用；loading/empty/error分开；OpenAPI生成类型无漂移。

## Phase 25 · Orders / Vehicles / Warehouses UI

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P25-01 · 实现订单查询、编辑和取消事件入口](docs/prompts/10-frontend/P25-01-orders-ui.md) | G24 | G25 | P25-02, P25-03 |
| [P25-02 · 实现车辆、司机和可用日历页面](docs/prompts/10-frontend/P25-02-vehicles-ui.md) | G24 | G25 | P25-01, P25-03 |
| [P25-03 · 实现仓库、温区、库位及作业资源页面](docs/prompts/10-frontend/P25-03-warehouses-ui.md) | G24 | G25 | P25-01, P25-02 |
| **G25：阶段验收证据** | P25-01, P25-02, P25-03 | P26-01, P26-02 | 无，屏障 |

订单/车辆/仓库资源页使用真实API；If-Match冲突可见；执行中变更走事件；无业务规则复制。

## Phase 26 · Transport Scheduling UI

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P26-01 · 实现运输请求、作业进度与不可行诊断页面](docs/prompts/10-frontend/P26-01-transport-request-ui.md) | G25 | P26-02, G26 | 无 |
| [P26-02 · 实现路线、逐站执行表和候选确认视图](docs/prompts/10-frontend/P26-02-transport-plan-ui.md) | G25, P26-01 | G26 | 无 |
| **G26：阶段验收证据** | P26-01, P26-02 | P27-01, P27-02 | 无，屏障 |

运输请求/Job/取消/诊断/路线表/费用/确认可操作；T1数值一致，TIMEOUT不显示成功。

## Phase 27 · Warehouse Scheduling UI

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P27-01 · 实现仓储请求和资源甘特图](docs/prompts/10-frontend/P27-01-warehouse-gantt-ui.md) | G26 | P27-02, G27 | 无 |
| [P27-02 · 实现仓运交接与联合方案对照视图](docs/prompts/10-frontend/P27-02-joint-handoff-ui.md) | G26, P27-01 | G27 | 无 |
| **G27：阶段验收证据** | P27-01, P27-02 | P28-01, P28-02 | 无，屏障 |

仓储甘特显示任务/setup/日历，J1交接冲突可见；只能统一确认有效联合候选。

## Phase 28 · Digital Twin UI

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P28-01 · 实现数字孪生场景、暂停、步进和事件注入](docs/prompts/10-frontend/P28-01-simulation-controls-ui.md) | G27 | P28-02, G28 | 无 |
| [P28-02 · 实现快照回放和反事实分支对比](docs/prompts/10-frontend/P28-02-replay-comparison-ui.md) | G27, P28-01 | G28 | 无 |
| **G28：阶段验收证据** | P28-01, P28-02 | P29-01, P29-02 | 无，屏障 |

仿真暂停/步进/注入/快照/分支比较可操作；正式状态不污染，3D不是必要依赖。

## Phase 29 · Exception Center UI

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P29-01 · 实现异常列表、影响图和处置流水](docs/prompts/10-frontend/P29-01-exception-center-ui.md) | G28 | P29-02, G29 | 无 |
| [P29-02 · 实现候选比较、版本差异和重排确认](docs/prompts/10-frontend/P29-02-reschedule-diff-ui.md) | G28, P29-01 | G29 | 无 |
| **G29：阶段验收证据** | P29-01, P29-02 | P30-01, P30-02 | 无，屏障 |

异常九步、原因路径、六项diff可检查；原方案/候选/新版本区分，失效候选不可确认。

## Phase 30 · Agent Chat UI

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P30-01 · 实现聊天、澄清和工具执行状态页面](docs/prompts/10-frontend/P30-01-agent-chat-ui.md) | G29 | P30-02, G30 | 无 |
| [P30-02 · 实现有证据的建议确认与风险提示](docs/prompts/10-frontend/P30-02-agent-confirmation-ui.md) | G29, P30-01 | G30 | 无 |
| **G30：阶段验收证据** | P30-01, P30-02 | P31-01, P31-02 | 无，屏障 |

聊天澄清/工具状态/取消/刷新恢复可用；建议卡数值有证据，脚本注入不执行，明确点击才确认。

## Phase 31 · WebSocket Real-time System

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P31-01 · 实现带游标的实时事件与断线补偿服务](docs/prompts/10-frontend/P31-01-websocket-events.md) | G30 | P31-02, G31 | 无 |
| [P31-02 · 实现前端实时订阅与轮询回退](docs/prompts/10-frontend/P31-02-frontend-realtime.md) | G30, P31-01 | G31 | 无 |
| **G31：阶段验收证据** | P31-01, P31-02 | P32-01, P32-02, P32-03 | 无，屏障 |

WS授权/补发/重复去重/过期cursor重取/慢客户端限额通过；断线轮询继续获得正确终态。

## Phase 32 · Metrics / Evaluation

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P32-01 · 实现14项调度指标与统一统计口径](docs/prompts/11-evaluation/P32-01-metric-calculators.md) | G31 | P32-02, G32 | 无 |
| [P32-02 · 实现指标持久化、版本比较与 Dashboard 聚合](docs/prompts/11-evaluation/P32-02-metrics-api.md) | G31, P32-01 | P32-03, G32 | 无 |
| [P32-03 · 实现 Dashboard 与 Metrics 图表页面](docs/prompts/11-evaluation/P32-03-metrics-dashboard-ui.md) | G31, P32-02 | G32 | 无 |
| **G32：阶段验收证据** | P32-01, P32-02, P32-03 | P33-01, P33-02 | 无，屏障 |

14指标逐项M1及边界通过；source/窗口/定义明确；Dashboard与Metrics不伪造null为0。

## Phase 33 · Experiment Framework

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P33-01 · 实现对照实验、配对随机种子与结果留档](docs/prompts/11-evaluation/P33-01-experiment-runner.md) | G32 | P33-02, G33 | 无 |
| [P33-02 · 实现实验创建、进度、结果与导出工作台](docs/prompts/11-evaluation/P33-02-experiments-api-ui.md) | G32, P33-01 | G33 | 无 |
| **G33：阶段验收证据** | P33-01, P33-02 | P34-01, P34-02, P34-03 | 无，屏障 |

至少10次配对seed、同预算实验；规则/solver/Agent与local/global对照；失败样本保留；实验UI/导出真实。

## Phase 34 · End-to-End Integration

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P34-01 · 建立真实数据库运输请求到确认的端到端验收](docs/prompts/12-integration/P34-01-transport-e2e.md) | G33 | P34-02, G34 | 无 |
| [P34-02 · 建立仓运联合与异常重排的完整端到端验收](docs/prompts/12-integration/P34-02-joint-exception-e2e.md) | G33, P34-01 | P34-03, G34 | 无 |
| [P34-03 · 建立崩溃、并发、模型断线与陈旧提交验收](docs/prompts/12-integration/P34-03-failure-recovery-e2e.md) | G33, P34-02 | G34 | 无 |
| **G34：阶段验收证据** | P34-01, P34-02, P34-03 | P35-01, P35-02, P35-03, P35-04, P35-05 | 无，屏障 |

真实PostgreSQL+OR-Tools+SimPy+浏览器完整闭环；worker崩溃/陈旧提交/并发冲突/模型断线可恢复。

## Phase 35 · Demo Scenario

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P35-01 · 交付 Scenario A 正常冷链运输演示](docs/prompts/12-integration/P35-01-demo-normal.md) | G34 | P35-02, G35 | 无 |
| [P35-02 · 交付 Scenario B 仓储和运输联合演示](docs/prompts/12-integration/P35-02-demo-joint.md) | G34, P35-01 | P35-03, G35 | 无 |
| [P35-03 · 交付 Scenario C1 车辆故障局部重排演示](docs/prompts/12-integration/P35-03-demo-vehicle-failure.md) | G34, P35-02 | P35-04, G35 | 无 |
| [P35-04 · 交付 Scenario C2 订单取消局部重排演示](docs/prompts/12-integration/P35-04-demo-order-cancel.md) | G34, P35-03 | P35-05, G35 | 无 |
| [P35-05 · 交付 Scenario C3 天气变化与一键复现演示包](docs/prompts/12-integration/P35-05-demo-weather.md) | G34, P35-04 | G35 | 无 |
| **G35：阶段验收证据** | P35-01, P35-02, P35-03, P35-04, P35-05 | P36-01, P36-02 | 无，屏障 |

A/B/C1/C2/C3五演示均有输入hash、实际解、硬校验、事件、版本diff、指标和回放证据；重复可复现。

## Phase 36 · Performance Optimization

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P36-01 · 建立可重复的容量、耗时和内存基准](docs/prompts/12-integration/P36-01-benchmark-harness.md) | G35 | P36-02, G36 | 无 |
| [P36-02 · 实现有内存上限的版本化矩阵缓存并复验](docs/prompts/12-integration/P36-02-bounded-performance-fix.md) | G35, P36-01 | G36 | 无 |
| **G36：阶段验收证据** | P36-01, P36-02 | P37-01, P37-02, P37-03 | 无，屏障 |

参考机10次基准齐备；20单4车2仓HTTP目标与求解预算按Master验收；缓存64MiB有界且换版本失效，所有正确性回归通过。

## Phase 37 · Security / Audit / Observability

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P37-01 · 验证并修复访问控制、输入边界和依赖安全](docs/prompts/12-integration/P37-01-security-boundary.md) | G36 | P37-02, G37 | 无 |
| [P37-02 · 实现全链追踪、指标端点和审计可检索性](docs/prompts/12-integration/P37-02-observability-audit.md) | G36, P37-01 | P37-03, G37 | 无 |
| [P37-03 · 验证数据库备份恢复、迁移回滚与作业恢复](docs/prompts/12-integration/P37-03-backup-and-recovery.md) | G36, P37-02 | G37 | 无 |
| **G37：阶段验收证据** | P37-01, P37-02, P37-03 | P38-01, P38-02 | 无，屏障 |

访问控制/注入/依赖/密钥负例无未处置阻断项；trace可追V2；备份恢复到隔离库保持历史与账本。

## Phase 38 · Documentation

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P38-01 · 交付与实际实现一致的架构、API和算法文档](docs/prompts/13-release/P38-01-developer-docs.md) | G37 | P38-02, G38 | 无 |
| [P38-02 · 交付演示、异常处置、运维和模型配置手册](docs/prompts/13-release/P38-02-operator-docs.md) | G37, P38-01 | G38 | 无 |
| **G38：阶段验收证据** | P38-01, P38-02 | P39-01, P39-02 | 无，屏障 |

开发/使用/运维文档对真实实现，无夸大能力；干净环境命令可执行，缺模型密钥降级有明确指南。

## Phase 39 · Release

| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |
| --- | --- | --- | --- |
| [P39-01 · 生成可安装发布候选及完整性清单](docs/prompts/13-release/P39-01-release-candidate.md) | G38 | P39-02, G39 | 无 |
| [P39-02 · 签收发布 Gate 与复现证据索引](docs/prompts/13-release/P39-02-release-gate.md) | G38, P39-01 | G39 | 无 |
| **G39：阶段验收证据** | P39-01, P39-02 | 发布候选签收完成 | 无，屏障 |

G00–G38证据未失效；发布候选hash/SBOM/锁/迁移完整；干净安装五演示通过；没有凭据，限制与恢复点明确。
