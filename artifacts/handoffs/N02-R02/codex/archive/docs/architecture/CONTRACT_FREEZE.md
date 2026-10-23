# Architecture Contract 冻结记录 · 1.0.0

本文是 Task `P00-02`「冻结单位、职责、错误和接口契约」的冻结记录（Freeze Record）。它把已批准的设计基线固定为一组具名文档契约，并逐条列出冻结决定、来源与验证责任。契约版本为 `1.0.0`，设计日期 `2026-09-12`。

**批准的设计 ≠ 已完成的代码。** 本冻结只证明“文档契约已固定且可追溯”，不证明任何功能已实现：截至本记录，仓库内没有任何应用代码，任何应用测试都尚未运行过，本轮唯一实际执行的证据是规划静态检查器（`tools/ai_coding_plan/validate_plan.py`）。Phase 00 三个任务只处理架构文档，业务能力全部仍是 `planned`/`not_run`；本任务完成不等于 `G00` 通过，也不等于任何后续任务完成。

## 1. 冻结记录（Freeze Record）

| 字段 | 值 | 说明 |
| --- | --- | --- |
| `schema_version` | `1.0.0` | 冻结记录自身结构版本，与契约版本一致 |
| `plan_version` | `1.0.0` | 取自 `docs/plan/TASK_MANIFEST.json` 的 `plan_version` 字段实际值 |
| `reviewer` | `planner-checker:tools/ai_coding_plan/validate_plan.py --self-test --record-g00` | 与配套 JSON 的记录一致：本轮唯一实际执行的证据是规划静态检查器，`P00-02` 责任分工为 A（见 `PROJECT_MASTER_PLAN.md` 模块划分表） |
| `reviewed_at` | `2026-09-12T00:00:00+00:00` | 与配套 JSON 及本计划设计日期一致；不是运行期时间戳 |
| `unresolved_blocking_issues` | `[]` | 无阻断问题；非阻断观察见第 6 节 |
| 配套机器文件 | `docs/architecture/CONTRACT_FREEZE.json` | 由编排器单独写入，记录每个冻结源的 `sha256` |

`CONTRACT_FREEZE.json` 的字段形状为 `{schema_version, plan_version, reviewed_at, reviewer, frozen_contract_version, legacy_contract_version, code_revision, unresolved_blocking_issues: [], non_blocking_observations: [...], change_policy: {...}, artifacts: [{path, sha256, role, consumers}]}`。**每个冻结源文件的 `sha256` 一律以该 JSON 内的记录为准**：本文不复制、不复述任何哈希值，因为哈希只能在生成器实际读取文件时计算，手写进描述性文档即等于伪造证据。本文只声明冻结范围与语义。

被冻结的源文件路径为下列 12 条，`CONTRACT_FREEZE.json` 的 `artifacts` 必须且只需覆盖这 12 条：

```text
PROJECT_MASTER_PLAN.md
TASK_GRAPH.md
docs/architecture/ARCHITECTURE_OVERVIEW.md
docs/architecture/DOMAIN_CATALOG.md
docs/architecture/DATA_CONTRACTS.md
docs/architecture/IMPLEMENTATION_CONVENTIONS.md
docs/api/API_CONTRACT.md
docs/algorithms/OPTIMIZATION_CONTRACT.md
docs/algorithms/SIMULATION_CONTRACT.md
docs/algorithms/METRICS_CONTRACT.md
docs/plan/TEST_FIXTURES.md
docs/plan/PHASE_GATES.md
```

### 版本基线事实

- 设计基线契约版本为 `1.0.0`；旧协作骨架 `demo/contracts/VERSION` 固定为 `0.1.0`。
- **旧版本文件不得被覆盖**：`PROJECT_MASTER_PLAN.md` 与 `DATA_CONTRACTS.md` 兼容变更章节都写明已有 demo 0.1.0 仅迁移输入，不能悄悄改版本文件覆盖旧基线。
- 旧 demo 的单位与接口不得与新结构混用；v0.1 → v1 必须显式转换并记录旧版本（见第 5 节）。

## 2. 冻结制品与下游依赖

下表“下游任务”列列出以本制品为设计输入或验证依据的任务/Gate 节点。“依据”列为该列出的出处：`REQUIREMENTS_TRACEABILITY` 表示该行由需求追踪矩阵列出，`Gate` 表示由 `PHASE_GATES.md` 的 Gate 断言或必需任务列出，`P00-02 Prompt` 表示由本任务 Prompt 的 `Business Rules`/`Input` 与 `TASK_GRAPH` 的阶段依赖直接给出。完整任务边以 `docs/plan/TASK_MANIFEST.json` 与 `TASK_GRAPH.md` 为准。

| # | 冻结制品 | 冻结角色 / 为什么冻结 | 下游任务（读取或验证） | 依据 |
| --- | --- | --- | --- | --- |
| 1 | `PROJECT_MASTER_PLAN.md` | 总体设计、非目标、架构原则、交付链与 Definition of Done；性能目标与“不把目标写为既成事实”的口径来源 | `P00-02`、`P01-01`、`P36-02`、`G36`、`G39`；18 组需求的整体范围和里程碑映射 | REQUIREMENTS_TRACEABILITY、Gate、P00-02 Prompt |
| 2 | `TASK_GRAPH.md` | 109 个 Task 与 40 个 Gate 节点的依赖/反向边/并行候选；严格阶段屏障的图形事实 | `P00-03`、`G00` | REQUIREMENTS_TRACEABILITY、Gate |
| 3 | `docs/architecture/ARCHITECTURE_OVERVIEW.md` | 模块图、代码依赖方向、阶段计划、主要风险与最迟 Gate；3D 只读不得进核心 Gate | `P00-02`、`P24-01`、`P28-01`、`P38-02`、`G38` | REQUIREMENTS_TRACEABILITY、Gate、P00-02 Prompt |
| 4 | `docs/architecture/DOMAIN_CATALOG.md` | 32 实体逐项状态、生命周期、字段、共同继承字段、单位与不变量、数据库约束与索引 | `P02-01`、`P02-02`、`P02-03`、`P02-04`、`P03-01`、`P03-02`、`G02`、`G03` | REQUIREMENTS_TRACEABILITY、Gate |
| 5 | `docs/architecture/DATA_CONTRACTS.md` | 公共类型、状态枚举、错误表与映射、关键 Schema、EventPayload 十类、冻结的 Protocol 方法与允许副作用、兼容变更规则 | `P00-02`、`P01-02`、`P02-04`、`P06-01`、`P08-01`、`P08-02`、`P10-01`、`P11-01`、`P13-01`、`P17-01`、`P18-01`、`P32-01`、`G02`、`G05`、`G11`、`G17` | REQUIREMENTS_TRACEABILITY、Gate、P00-02 Prompt |
| 6 | `docs/architecture/IMPLEMENTATION_CONVENTIONS.md` | uv/npm workspace 与包路径、分层与唯一组合根、早期类型图与模块内上下文、生成物与证据约定、`CONTRACT_FREEZE.json` 自身格式 | `P00-01`、`P00-02`、`P01-01`、`P01-02`、`P01-03`、`P05-01`、`G01` | P00-02 Prompt、Gate |
| 7 | `docs/api/API_CONTRACT.md` | `/api/v1` 端点表、分页、`If-Match`/`Idempotency-Key`、202 JobRef 与结果查询分离、状态码转换、Agent 工具白名单与角色/Effect | `P05-01`、`P05-02`、`P05-03`、`P13-02`、`P16-01`、`P16-02`、`P16-03`、`P16-04`、`P23-02`、`P31-01`、`P37-02`、`G05`、`G16`、`G23` | REQUIREMENTS_TRACEABILITY、Gate |
| 8 | `docs/algorithms/OPTIMIZATION_CONTRACT.md` | 运输/仓储/联合/局部重排的变量、约束、目标、配置、状态映射、独立校验硬规则代码与提交并发规则 | `P06-01`、`P06-02`、`P07-01`…`P07-06`、`P08-01`、`P08-02`、`P09-01`…`P09-05`、`P10-01`、`P10-02`、`P10-03`、`P15-02`、`P16-02`、`G07`、`G09`、`G10`、`G15`、`G16` | REQUIREMENTS_TRACEABILITY、Gate |
| 9 | `docs/algorithms/SIMULATION_CONTRACT.md` | 纯投影与仿真分支隔离、事件总排序键与优先级、RNG 与快照内容、恢复不 pickle generator、分支对比与进度控制、仿真验收 | `P11-01`、`P11-02`、`P12-01`、`P12-02`、`P12-03`、`P12-04`、`P13-01`、`G11`、`G12`、`G13` | REQUIREMENTS_TRACEABILITY、Gate |
| 10 | `docs/algorithms/METRICS_CONTRACT.md` | 14 项指标的精确定义、零值与边界、扰动公式、`ScheduleDiff` 六项差异、实验口径与失败样本保留 | `P15-04`、`P32-01`、`P32-02`、`P33-01`、`P33-02`、`G32`、`G33` | REQUIREMENTS_TRACEABILITY、Gate |
| 11 | `docs/plan/TEST_FIXTURES.md` | T1/W1/J1/I1/S1/M1 手算数据与 A/B/C1/C2/C3 生成参数、变体规则、不允许静默改共有期望 | `P04-01`、`P07-01`…`P07-07`、`P09-01`…`P09-05`、`P12-01`…`P12-04`、`P15-01`…`P15-04`、`P32-01`、`P35-01`…`P35-05`、`G04`、`G07`、`G09`、`G12`、`G15`、`G32`、`G35` | REQUIREMENTS_TRACEABILITY、Gate |
| 12 | `docs/plan/PHASE_GATES.md` | 40 个 Gate 的 `G00`–`G39` 协议、Gate Evidence 最小字段、freshness/失效规则、特定环境与发布门槛 | `P01-02`、`P01-03`、`P38-01`、`P38-02`、`P39-01`、`P39-02`、全部 `G00`–`G39` 的签收规则 | REQUIREMENTS_TRACEABILITY、Gate、P00-02 Prompt |

## 3. 冻结决定

每条决定给出结论、语义边界与来源。所有引用均来自第 2 节列出的冻结制品。

| # | 冻结决定 | 语义边界 | 来源 |
| --- | --- | --- | --- |
| D1 | 契约版本为 `1.0.0`；破坏字段/单位/enum/路径/必需语义升 major，新增可选字段升 minor，兼容修复升 patch；**先写 `contracts/changes/` 说明**，再在同一集成内按 domain → DTO → ports → 调用方 → 测试 → 导出物 顺序修改 | 旧 demo 的 `0.1.0` 只迁移输入，不得覆盖版本文件 | `DATA_CONTRACTS.md` 兼容变更；`IMPLEMENTATION_CONVENTIONS.md` 文件变更与证据 |
| D2 | 32 个实体是必需集合，每个实体具有 `id: UUID`、单一 `status` Enum、UTC `created_at`/`updated_at`、`row_version: int >= 0`、`schema_version: str`、`created_by: ActorId`；不复制业务模型，不维护第二套 domain/DTO/前端枚举 | 首次创建两时间相等；业务变更由应用服务递增 `row_version` 与 `updated_at`；不可变内容 `created_at=updated_at`，后续状态以追加生命周期事件投影；所有 ID 用 UUID4，合成数据用带 namespace 的 UUID5 | `DOMAIN_CATALOG.md` 共同继承字段、32 实体表；`ARCHITECTURE_OVERVIEW.md` Module Map |
| D3 | 共享单位与时间语义：整数秒、米、克、cm³、分（金额，整数最小单位）、decic（十分之一摄氏度）；时间统一 UTC epoch；服务开始允许窗 `[earliest_s, latest_s]` 两端可取；任务占用 `[start_s, end_s)`，故 `[0,10)` 与 `[10,20)` 不冲突 | 时间统一 `timestamptz` 且领域时间带时区；浮点经外层显示转换，不进入求解整数约束；订单数量按整数最小包装单位；不得默默把千克当克或分钟当秒；`hard_latest_start_s` 与 `soft_due_at_s` 是不同字段 | `DOMAIN_CATALOG.md` 单位与时间段落；`P00-02` Data Contract 段与其 Edge Cases |
| D4 | 边界 Schema 一律 `extra=forbid`，跨模块输入输出均具名、有版本，禁止任意 `dict`/`Any` 穿越边界；列表字段为 tuple 或显式 `list[T]`，可选字段用 `T\|None` 且有缺失语义 | 纯 domain 不依赖 Pydantic；边界解析拒绝未知字段而不是忽略 | `DATA_CONTRACTS.md` 开篇；Architecture Constraints 第 1 条 |
| D5 | 错误码到 HTTP 的映射被冻结：`INVALID_INPUT`/`INVALID_TRANSITION`/`DEPENDENCY_CYCLE` → 422；`UNAUTHENTICATED` → 401；`FORBIDDEN`/`TOOL_FORBIDDEN` → 403；`NOT_FOUND` → 404；`STALE_SNAPSHOT`/`RESOURCE_CONFLICT`/`IDEMPOTENCY_CONFLICT`/`CONFIRMATION_EXPIRED` → 409；`REQUEST_TOO_LARGE` → 413；`RATE_LIMITED` → 429；`PROVIDER_UNAVAILABLE`/`DEPENDENCY_UNAVAILABLE` → 503；`INTERNAL_ERROR` → 500 | 求解 TIMEOUT/UNKNOWN/INFEASIBLE 是**已完成作业的 typed 结果状态**，绝不统一包装成 500；`MANUAL_REQUIRED`/`NO_FEASIBLE_CANDIDATE` 是业务结果原因；开发期未实现能力 HTTP 501 且禁止进入对应 Gate；`TOOL_FORBIDDEN` 由 API/Tool 边界使用 | `DATA_CONTRACTS.md` 错误表；`API_CONTRACT.md` 通用规则 |
| D6 | `SolveStatus = OPTIMAL \| FEASIBLE \| INFEASIBLE \| TIMEOUT \| UNKNOWN \| INVALID_INPUT \| ERROR \| CANCELLED`；`JobStatus = queued \| running \| completed \| failed \| cancelled` | `completed` 只表示工作已执行并产出 typed 结果；优化结果可能仍是 INFEASIBLE/TIMEOUT，不表示求解成功；只有 worker 自身崩溃或代码错误重试耗尽才 `failed`；`TIMEOUT` 可有经校验的 incumbent，无 incumbent 不得报告可行；`FEASIBLE` 不等于 `OPTIMAL`；`UNKNOWN` 不等于已证明 `INFEASIBLE`；可选（未服务）/未知/无解/超时四种语义必须可区分，禁止互相冒充或混用 | `DATA_CONTRACTS.md` 公共类型与状态、`OptimizationResult`；`OPTIMIZATION_CONTRACT.md` 配置段 |
| D7 | 依赖方向冻结：domain 不导入框架/ORM/模型 SDK；application 不导入 adapters；`bootstrap.py` 是唯一组合根与唯一装配点；React 不硬编码业务规则、不另行声明枚举（前端类型由 OpenAPI 派生） | 包间只通过显式 Protocol 或 DTO 交互，实现对象只由 bootstrap 注入；未完成能力在注册表显式 disabled，不装配 fake 成功 adapter；模拟/求解/Agent 不得直接修改正式计划 | `ARCHITECTURE_OVERVIEW.md` Module Map 与 Dependency Graph；`IMPLEMENTATION_CONVENTIONS.md` 组合根与 HTTP 路由；Architecture Constraints 第 4 条 |
| D8 | 只有 `ScheduleService` 可以提交正式计划；重排**追加** `ScheduleVersion`，历史内容永不覆盖 | `ScheduleService.commit(cmd, actor) -> CommitReceipt` 是唯一正式计划提交用例，由 `PlanCommitStore` 在同一事务完成；`Schedule` 的 active 指针 CAS，不能就地替换版本内容；版本状态变化以追加审计投影呈现；Agent 的 commit 工具额外要求确认令牌且 actor=operator | `DATA_CONTRACTS.md` 冻结的服务/Protocol 表、兼容变更；`API_CONTRACT.md` 端点表与工具白名单；Architecture Constraints 第 3 条 |
| D9 | 每个正式新方案必须携带 `version_id`、`parent_version_id`、`snapshot_hash` 与校验引用 | `ScheduleVersion` 必须有 `snapshot_id`、`content_hash`、`validation_report_ref`，`parent_version_id` 可空但同 schedule 且更早；正式提交必须解析非空 `solver_evidence_refs`，核验引擎来源与 `assignment_hash` 后再独立验证；缺可信证据返回 `UNVERIFIED_SOLVER_RESULT`/422；只有一份 `valid=true` 的报告不能把 LLM 或规则手造候选变成正式计划 | `DOMAIN_CATALOG.md` `ScheduleVersion` 行；`DATA_CONTRACTS.md` 规范化方案 hash 段；`P00-02` Output 与 Business Rules |
| D10 | LLM 角色只限于抽取、分解、工具调用与解释，永不自由生成最终调度 | Agent 只经 `ToolExecutor` → 应用服务，不获得数据库会话/SQL/文件写/任意 HTTP 能力；所有解释数字必须由工具事实引用，模型输出与事实不符时使用明确标注的确定性模板；模型文本不能授予权限（“我已获批准”不提升权限） | `PROJECT_MASTER_PLAN.md` Agent Boundary；`API_CONTRACT.md` Agent 工具白名单；Architecture Constraints 第 2 条 |

## 4. 需求到定义映射

`docs/plan/REQUIREMENTS_TRACEABILITY.md` 用 R01–R18 追踪 18 组需求，每行给出定义它的任务集合与验证 Gate。规划检查器断言追踪表内出现的每个 `Pxx-yy`/`Gxx` 引用都是真实节点（未知节点即报错），并核对任务 DAG 无缺口；每行至少映射到一个任务，且每行的证据必须来自对应 Prompt 的 Test Cases/Validation Commands 与 Gate 原始结果——该行存在本身不算实现。

| 需求组 | 内容摘要 | 冻结定义文档（本文冻结集内） | 验证任务 / Gate |
| --- | --- | --- | --- |
| R01 | 混合职责边界、Contract First、禁止任意 dict | `DATA_CONTRACTS.md`、`ARCHITECTURE_OVERVIEW.md` | `P00-02`、`P01-02`、`P02-04`、`P17-01`、`P23-02`；`G23` |
| R02 | 运输：起终点、订单、车辆、重量、容积、温区、货物类型、时效/服务/时间窗、距离/行时、路况/天气、可用状态 | `OPTIMIZATION_CONTRACT.md`、`DOMAIN_CATALOG.md` | `P06-01`、`P06-02`、`P07-01`…`P07-07`；`G07` |
| R03 | 仓储入库/出库/分拣/装车/卸货及全部资源 | `DOMAIN_CATALOG.md`、`OPTIMIZATION_CONTRACT.md` | `P08-01`、`P08-02`、`P09-01`、`P09-02`、`P09-03`；`G09` |
| R04 | 仓储时间窗/互斥/容量/依赖/准备/清洁/月台/温区/分拣切换 | `OPTIMIZATION_CONTRACT.md` | `P09-01`、`P09-02`、`P09-04`、`P09-05`；`G09` |
| R05 | 十类异常：故障、延误、交通、天气、货物、取消、需求增减、设备故障、仓资源不可用 | `DATA_CONTRACTS.md`（EventPayload 十类） | `P13-01`、`P13-02`、`P14-01`；`G14` |
| R06 | 异常九步流程、Local 优先、范围扩展及失败处置 | `OPTIMIZATION_CONTRACT.md`（局部重调度） | `P14-01`、`P14-02`、`P15-01`…`P15-04`、`P22-01`；`G22` |
| R07 | 32 实体逐一 ID/状态/生命周期/字段/关联/时间 | `DOMAIN_CATALOG.md` | `P02-01`…`P02-04`、`P03-01`、`P03-02`；`G03` |
| R08 | `ScheduleVersion` 不可覆盖及六项差异 | `DOMAIN_CATALOG.md`、`METRICS_CONTRACT.md` | `P02-03`、`P03-04`、`P15-04`、`P16-03`、`P29-02`；`G29`（见 `ARCH-0001`） |
| R09 | 确定性硬校验、仓运联合可行性 | `OPTIMIZATION_CONTRACT.md` | `P07-06`、`P09-05`、`P10-01`…`P10-03`、`P16-02`；`G16` |
| R10 | DigitalTwin/Simulation/Event/Scenario 引擎、快照回放和反事实 | `SIMULATION_CONTRACT.md` | `P11-01`、`P11-02`、`P12-01`…`P12-04`、`P13-01`；`G13` |
| R11 | 四角色 Agent 及工具接口 | `DATA_CONTRACTS.md`（Protocol 表）、`API_CONTRACT.md`（工具白名单） | `P17-01`…`P23-02`；`G23` |
| R12 | 11 个 React 页面及 WebSocket 实时 | `ARCHITECTURE_OVERVIEW.md`、`API_CONTRACT.md` | `P24-01`…`P31-02`、`P32-03`、`P33-02`；`G33` |
| R13 | 14 项指标、口径、差异和实验基线 | `METRICS_CONTRACT.md` | `P32-01`、`P32-02`、`P32-03`、`P33-01`、`P33-02`；`G33` |
| R14 | A 正常冷链 / B 仓运联合 / C 故障取消天气演示 | `TEST_FIXTURES.md`（A/B/C 生成参数） | `P35-01`…`P35-05`；`G35` |
| R15 | 可追踪性/错误/安全/并发/幂等/备份恢复 | `DATA_CONTRACTS.md`（错误表）、`PHASE_GATES.md`（特定环境门槛） | `P03-04`、`P05-01`、`P05-03`、`P17-01`、`P34-03`、`P37-01`…`P37-03`；`G37` |
| R16 | 性能、工程部署、文档及发布 | `PROJECT_MASTER_PLAN.md`（Definition of Done）、`PHASE_GATES.md`（G36/G39 门槛） | `P01-01`、`P36-01`、`P36-02`、`P38-01`、`P38-02`、`P39-01`、`P39-02`；`G39` |
| R17 | 完整 Master/TaskGraph/14 目录/每 Prompt 结构/40 Gate | `PROJECT_MASTER_PLAN.md`、`TASK_GRAPH.md` | `P00-01`、`P00-02`、`P00-03`；`G00` |
| R18 | 3D 及其他过早设计不得影响核心 MVP | `ARCHITECTURE_OVERVIEW.md`（推荐调整项 7） | `P00-02`、`P24-01`、`P28-01`、`P38-02`；`G38` |

需求组总数 18（R01–R18），未覆盖数为 0。覆盖结论的语义边界：追踪表证明“每组需求至少有一个定义文档与验证节点”，不证明任何验证已通过。

## 5. 被拒绝的输入与冻结语义

两个边界用例是本契约的系统性语义，不是可选的实现细节。它们描述实现后的必然后果，本轮未运行任何应用测试来证明其行为。

| 输入 | 冻结语义 | 理由与禁止事项 |
| --- | --- | --- |
| `duration=1.5` 秒 | 整数时间契约**拒绝**该输入，判定为 `INVALID_INPUT`（HTTP 422）；不静默四舍五入、不截断、无副作用（不产生任务、不占用资源、不落库半状态） | 时间统一为整数秒；浮点只在外层显示转换，不进入求解整数约束。静默取整会让计划与输入快照不一致，破坏可追溯性 |
| 旧分钟输入 `2` | **显式转换**为 `120` 秒，并记录其来自旧版本（v0.1 分钟语义），转换事实与旧版本标记一同保留 | 旧 demo 使用分钟与简化字典，不属于当前契约；必须显式转换并标注来源，绝不隐式按分钟解释任何新契约字段。禁止在与新契约混用时“顺手”沿用分钟单位 |

共同边界行为（拒绝未知字段、非法枚举/单位、负值与整数溢出、悬空关联、边界时间相等、过期 revision、取消/超时、依赖不可用）按各实现任务的范围分别验证；实现后由 `G02` 断言“非法状态/单位/额外字段拒绝”。本任务只冻结语义，不产出业务测试证据。

## 6. 变更管理

- **版本升级规则**：破坏字段/单位/enum/路径/必需语义的变更升 major；新增可选字段升 minor；兼容修复升 patch。契约版本从 `1.0.0` 起算。
- **迁移顺序**：先写 `contracts/changes/` 说明，再在同一集成内按 domain → DTO → ports → 调用方 → 测试 → 导出物 顺序修改；不得先改后解释，也不能只改一侧。
- **生成物**：生成的 JSON/TS 产物（JSON Schema、OpenAPI 导出的 TS 类型、契约 JSON）**永不手改**，只运行生成器更新；任何 API 变化都同步生成 TS，`contracts:generate/check` 负责一致性。
- **hash 规范**：方案 hash 排除创建时间、生命周期投影与耗时，并排除随机生成的 candidate/version/route 与 solver_evidence 记录 ID；包含稳定订单/任务/车辆/资源 ID、路线节点顺序、所有业务时刻/载荷/费用，以及 schema/rules/matrix 版本；采用 UTF-8、排序键、整数和明确 null。
- **失效规则**：公共契约变更使受影响 Gate 及其所有下游证据失效，必须回到相应任务修复并重跑相关检查；不能以改日期恢复。影响某 Gate 的变更使其及下游证据失效。
- **非阻断处理**：非阻断架构问题写 `docs/architecture/issues/` 并继续限定任务，不顺手重构；阻断问题按最小契约迁移处理并更新所有受影响调用方、测试与导出物，禁止大规模重构。

## 7. 未决 / 阻断

- `unresolved_blocking_issues`：`[]`。冻结时没有任何阻断项被登记。
- 非阻断观察（不影响 `G00` 文档冻结结论，需由后续任务处理）：

| 观察 | 说明 | 处置责任 |
| --- | --- | --- |
| 冻结文档是唯一权威来源 | 本文与 `CONTRACT_FREEZE.json` 只是记录，不产生第二套契约；若文档之间出现语义差异，以第 3 节列出的来源文档为准并登记 issue | 契约变更任务 |
| 尚无运行期证据 | 没有任何应用代码、没有执行过应用测试；冻结只能由静态规划检查器核验，不能替代业务验收 | 各阶段任务与对应 Gate |
| Gate 执行器尚不存在 | `P01-02` 才实现正式 `scripts/gates.py`；在它存在之前，任何阶段都不能用统一执行器产出 Gate Evidence；`G00` 签收也不能用本轮静态报告替代 | `P01-02`、`G00` |
| `ARCH-0001` 追踪表 Gate 列与阶段屏障不严格对齐 | `REQUIREMENTS_TRACEABILITY.md` 的 R08 行把验证 Gate 写为 `G29`，但该行的 `P15-04`/`P16-03` 分别属于 Phase 15/16，其出口 Gate 是 `G15`/`G16`。检查器只校验引用节点存在，不校验 Gate 与阶段对齐。**非阻断**：完整性仍由精确阶段 Gate 保证 | `P00-03`（任务 DAG 与 Gate 契约）、契约变更任务 |
| `ARCH-0002` 基线清单的覆盖口径 | `BASELINE_INVENTORY.json` 以穷举方式登记 `demo/` 下 173 个普通文件（`coverage.unregistered_file_count = 0`），两个大型派生目录（`demo/frontend/node_modules/`、`demo/.venv/`）只记录计数与树指纹，缓存目录不登记。**非阻断**：`G01` 的"旧 demo 未被覆盖"断言由 `demo/` 登记文件指纹与 `demo.zip` 哈希验证；冻结结论不依赖派生目录的逐文件哈希 | `P00-01`（已 `closed`） |
| `ARCH-0003` 错误码 `UNSUPPORTED` 未登记 | 全部 109 个任务 Prompt 要求"未知必需能力→`UNSUPPORTED`"，但 `DATA_CONTRACTS.md` 第 13 行的错误表没有该错误码（只有 `ErrorDetail` 判别联合中的 `UnsupportedDetail(capability)`，且未规定其状态码）。**非阻断**：不影响实体/单位/状态枚举/求解语义，且 `P05-01` 之前没有 HTTP 边界会因此漂移 | `P05-01`（错误协议） |

未发现其他真实矛盾：冻结集内其余文档之间没有互斥声明、没有重复定义同一实体的冲突字段、没有互相覆盖的单位口径。按任务要求，不对未发现的矛盾编造条目。

## 8. 限制 / 未验证

本冻结明确**不**证明以下内容：

1. **本冻结记录写作时尚无应用代码**：记录所描述的是待实现结构。P01-01 之后 `apps/` 与 `packages/` 只存在可导入的包骨架（模块常量 + 未交付名字显式抛 `NotImplementedError`），仍然没有任何业务实现；本冻结的语义不因骨架存在而变化。
2. **无已执行的应用测试**：没有任何 unit/integration/solver/simulation/e2e 测试运行过；本轮唯一实际执行的证据是规划静态检查器。第 5 节的边界语义是冻结约定，不是测试结果。
3. **不证明算法正确性**：`OPTIMIZATION_CONTRACT.md` 的模型、独立校验硬规则与状态映射尚未实现；`G07`/`G09`/`G10` 的手算与反例断言全部未执行。
4. **不证明性能**：`PROJECT_MASTER_PLAN.md` 的求解预算（单域 5s、联合与重排 15s）与 HTTP p95 目标（接收 <500ms、健康 <200ms）是待实测门槛，`G36` 在参考机记录实测值；不把目标写为既成事实。
5. **不证明业务可用性**：没有任何真实承运人、仓库或模型供应商参与；A/B/C 演示与真实 LLM 契约 smoke 均为未执行。
6. **不证明哈希一致**：`CONTRACT_FREEZE.json` 内的 `sha256` 只有在生成器实际读取 12 个冻结源后才有意义；本文不提供也不背书任何哈希值。
7. **不使 Gate 通过**：`P00-02` 完成不等于 `G00` 通过；`G00` 仍需 `P00-03` 与 `P00-01` 的证据，且签收不能用本轮静态报告替代。

## 9. 参考

- `PROJECT_MASTER_PLAN.md`
- `TASK_GRAPH.md`
- `docs/architecture/ARCHITECTURE_OVERVIEW.md`
- `docs/architecture/DOMAIN_CATALOG.md`
- `docs/architecture/DATA_CONTRACTS.md`
- `docs/architecture/IMPLEMENTATION_CONVENTIONS.md`
- `docs/api/API_CONTRACT.md`
- `docs/algorithms/OPTIMIZATION_CONTRACT.md`
- `docs/algorithms/SIMULATION_CONTRACT.md`
- `docs/algorithms/METRICS_CONTRACT.md`
- `docs/plan/TEST_FIXTURES.md`
- `docs/plan/PHASE_GATES.md`
- `docs/plan/REQUIREMENTS_TRACEABILITY.md`（需求追踪，非冻结制品但为本文第 4 节来源）
- `docs/plan/TASK_MANIFEST.json`（`plan_version` 与任务边机器事实）
- `docs/architecture/issues/README.md`（架构问题登记，见 `ARCH-0001`、`ARCH-0002`、`ARCH-0003`）
- `tools/ai_coding_plan/contract_freeze_generate.py`（本 JSON 的生成器，`--check` 校验新鲜度）
