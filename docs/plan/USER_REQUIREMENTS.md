你现在担任本项目的：

- 首席软件架构师
- AI Coding Workflow Architect
- Prompt Engineer
- 后端架构师
- 运筹优化工程师
- AI Agent 架构师
- 测试负责人

你的当前任务不是直接编写整个程序，而是首先为后续 Codex Vibe Coding 开发生成一套完整、严格、可逐阶段执行的「开发 Prompt 系统」。

我会使用 Codex 完成绝大部分编码工作，因此你的目标是把一个大型项目拆成大量边界清晰、可以独立执行、可以独立测试、可以独立验收的开发任务，使后续 Coding Agent 不需要自行猜测架构。

# 一、项目名称

基于大模型技术的物流调度智能体应用开发

核心研究场景优先选择冷链物流，但架构应尽可能具有通用物流调度能力。

# 二、核心技术路线

系统采用：

大语言模型智能体
+
OR-Tools 确定性优化求解
+
SimPy 离散事件仿真
+
FastAPI
+
React
+
PostgreSQL

形成混合智能调度系统。

严格遵循以下职责边界：

LLM：

负责：

1. 自然语言理解
2. 意图识别
3. 约束抽取
4. 任务分解
5. 工具选择
6. 工具调用
7. 多智能体协调
8. 求解结果解释
9. 异常处置解释

LLM 不允许直接自由生成最终调度方案。

OR-Tools：

负责：

1. 车辆调度
2. 路径规划
3. 运力分配
4. 时间窗约束
5. 仓储资源排程
6. 局部重调度
7. 硬约束检查
8. 调度方案可行性验证

所有正式调度方案必须经过确定性求解器验证。

SimPy：

负责：

1. 数字孪生时间推进
2. 订单状态演化
3. 车辆状态演化
4. 仓库状态演化
5. 事件注入
6. 异常模拟
7. 方案推演
8. 反事实模拟

# 三、系统必须实现的三大核心能力

## A. 智能路径规划

至少考虑：

- 起点
- 终点
- 订单
- 车辆
- 载重
- 容积
- 温区
- 货物类型
- 时效要求
- 服务时间
- 时间窗
- 道路距离
- 预计行驶时间
- 路况
- 天气
- 车辆可用状态

输出：

车辆—订单—路线—到达时间—服务时间—运输成本的完整执行方案。

## B. 仓储协同调度

至少支持：

- 入库
- 出库
- 分拣
- 装车
- 卸货

资源至少包括：

- 仓库
- 温区
- 库位
- 月台
- 作业人员
- 分拣设备
- 搬运设备

需要处理：

- 时间窗
- 资源互斥
- 能力限制
- 前后任务依赖
- 准备时间
- 清洁时间
- 月台切换
- 温区切换
- 分拣切换

## C. 异常事件处置

至少支持：

- 车辆故障
- 运输延误
- 交通异常
- 天气突变
- 货物异常
- 订单取消
- 需求增加
- 需求减少
- 仓储设备故障
- 仓库资源不可用

处理流程必须为：

事件识别
→
影响分析
→
确定受影响任务
→
生成候选调整
→
局部重新求解
→
硬约束验证
→
方案比较
→
输出调整建议
→
生成处置记录

原则上优先执行 Local Rescheduling，而不是每次重新执行全局优化。

# 四、目标架构

按照下列层次设计：

## Layer 1：Interaction

React Web UI

包括：

- Dashboard
- Orders
- Vehicles
- Warehouses
- Transport Scheduling
- Warehouse Scheduling
- Simulation
- Exceptions
- Agent Chat
- Metrics
- Experiments

## Layer 2：Agent

至少设计：

CoordinatorAgent
TransportAgent
WarehouseAgent
ExceptionAgent

允许后续增加：

SimulationAgent
EvaluationAgent

所有 Agent 必须通过标准 Tool Interface 调用业务系统。

禁止 Agent 绕过业务服务直接修改核心调度数据。

## Layer 3：Optimization & Simulation

包括：

TransportSolver

WarehouseScheduler

RescheduleSolver

ConstraintValidator

DigitalTwinEngine

SimulationEngine

EventEngine

ScenarioEngine

## Layer 4：Domain & Data

PostgreSQL。

至少建立：

Order

Cargo

Vehicle

Driver

Warehouse

WarehouseZone

StorageLocation

Dock

Worker

Equipment

TransportTask

WarehouseTask

Route

RouteStop

Schedule

ScheduleTask

ScheduleVersion

Constraint

OptimizationRequest

OptimizationResult

Simulation

SimulationSnapshot

Event

ExceptionEvent

RescheduleRequest

RescheduleResult

AgentRun

ToolCall

DecisionRecord

Experiment

Metric

ExperimentResult

对每个实体定义：

- ID
- 状态
- 生命周期
- 关键字段
- 关联关系
- 创建时间
- 更新时间

所有关键业务操作必须具有可追踪性。

# 五、工程结构

优先设计 Monorepo：

apps/backend
apps/frontend

packages/agents
packages/optimization
packages/simulation
packages/evaluation

data/scenarios
data/seed
data/experiments

tests/unit
tests/integration
tests/solver
tests/simulation
tests/e2e

docs/architecture
docs/api
docs/algorithms
docs/prompts

# 六、当前任务

不要立即编写全部代码。

首先为整个项目制定「AI Coding Master Plan」。

必须先完成架构设计和任务分解，然后为后续 Codex 生成独立开发 Prompt。

整个开发计划必须按照依赖顺序组织。

推荐基础顺序：

Phase 00
需求冻结与 Architecture Contract

Phase 01
Monorepo 与工程基础

Phase 02
Domain Model

Phase 03
PostgreSQL Schema + Migration

Phase 04
Seed / Synthetic Dataset

Phase 05
FastAPI 基础服务

Phase 06
Transport Optimization Domain

Phase 07
Transport Solver

Phase 08
Warehouse Optimization Domain

Phase 09
Warehouse Scheduler

Phase 10
Constraint Validator

Phase 11
Simulation Domain

Phase 12
SimPy Digital Twin

Phase 13
Event Engine

Phase 14
Exception Impact Analyzer

Phase 15
Local Rescheduling Engine

Phase 16
Optimization API

Phase 17
Agent Tool Protocol

Phase 18
LLM Provider Abstraction

Phase 19
Coordinator Agent

Phase 20
Transport Agent

Phase 21
Warehouse Agent

Phase 22
Exception Agent

Phase 23
Agent Orchestration

Phase 24
React Application Shell

Phase 25
Orders / Vehicles / Warehouses UI

Phase 26
Transport Scheduling UI

Phase 27
Warehouse Scheduling UI

Phase 28
Digital Twin UI

Phase 29
Exception Center UI

Phase 30
Agent Chat UI

Phase 31
WebSocket Real-time System

Phase 32
Metrics / Evaluation

Phase 33
Experiment Framework

Phase 34
End-to-End Integration

Phase 35
Demo Scenario

Phase 36
Performance Optimization

Phase 37
Security / Audit / Observability

Phase 38
Documentation

Phase 39
Release

3D 仓库数字孪生属于可选 Enhancement，不允许在核心调度能力完成之前成为关键依赖。

# 七、你的输出要求

首先输出：

PROJECT_MASTER_PLAN.md

其中必须包含：

1. 项目目标
2. 非目标
3. 架构原则
4. 系统上下文
5. 技术架构
6. 模块划分
7. 模块依赖图
8. Domain Model
9. API Boundary
10. Agent Boundary
11. Solver Boundary
12. Simulation Boundary
13. 数据库边界
14. 前端边界
15. 测试策略
16. Observability
17. Security
18. Demo Strategy
19. Milestones
20. Definition of Done

然后输出：

TASK_GRAPH.md

使用 DAG 思维描述：

Task
Dependencies
Blocks
Can Run In Parallel

禁止存在模糊的：

“完善系统”

“完成相关功能”

“优化代码”

等任务。

每一个 Task 都必须对应一个明确、可验证的软件交付物。

# 八、随后生成 Codex Prompt

在：

docs/prompts/

生成：

00-master/
01-foundation/
02-domain/
03-database/
04-api/
05-transport-solver/
06-warehouse-solver/
07-simulation/
08-exception/
09-agents/
10-frontend/
11-evaluation/
12-integration/
13-release/

每个开发任务独立保存为 Prompt。

例如：

P07-01-transport-domain-model.md

P07-02-distance-matrix.md

P07-03-vrp-basic-solver.md

P07-04-capacity-constraint.md

P07-05-time-window.md

P07-06-temperature-constraint.md

P07-07-objective-function.md

P07-08-result-validator.md

不要为一个大型模块只创建一个巨大 Prompt。

应继续拆分到单个 Agent 一次可以可靠完成的粒度。

# 九、每一个 Coding Prompt 必须包含以下结构

## Context

解释项目背景以及当前模块位于整个系统中的位置。

## Current State

告诉 Coding Agent 当前代码库理论上已经完成什么。

## Objective

本任务唯一明确目标。

## Scope

本任务允许修改的内容。

## Out of Scope

明确禁止顺手实现的内容。

## Architecture Constraints

不得违反哪些架构规则。

## Files

预计：

创建哪些文件

修改哪些文件

禁止修改哪些文件。

## Domain Model

涉及哪些实体。

## Input

输入格式。

## Output

输出格式。

## Interfaces

函数签名/API/Protocol。

## Data Contract

必须使用什么 Schema。

## Business Rules

业务规则。

## Algorithm

算法逻辑。

如果涉及 OR-Tools，必须明确：

Decision Variables

Constraints

Objective Function

Solver Configuration

Result Extraction

Validation

## Edge Cases

列举必须考虑的异常情况。

## Error Handling

错误分类与处理策略。

## Logging

需要记录哪些日志。

## Observability

需要暴露哪些 Metric。

## Testing

必须创建：

Unit Test

Integration Test

必要时 Solver Test / Simulation Test。

## Test Cases

必须明确给出测试数据和预期结果。

## Acceptance Criteria

使用明确可验证条件。

例如：

pytest tests/solver/test_transport_solver.py

必须全部通过。

## Validation Commands

给出 Codex 完成任务以后必须执行的命令。

## Documentation

需要同步修改的文档。

## Completion Report

Codex 最终必须汇报：

Files created

Files modified

Tests added

Commands executed

Test results

Known limitations

Remaining risks

# 十、Coding Agent 行为限制

所有后续 Prompt 都必须明确告诉 Coding Agent：

不要擅自重新设计整个架构。

不要因为当前任务方便而修改公共接口。

如果发现架构问题：

先记录在：

docs/architecture/issues/

除非属于阻断性错误，否则不得顺手大规模重构。

禁止：

TODO 占位核心逻辑

fake implementation

hard-coded demo answer

绕过 Solver

让 LLM 自由生成最终调度结果

只写代码不写测试

捕获 Exception 后什么都不做

重复定义 Domain Model

前后端分别维护不同业务枚举

把业务规则写死在 React 页面

# 十一、强制开发原则

整个项目采用 Contract First。

顺序：

Domain Contract
→
Schema
→
Service Interface
→
Implementation
→
Test
→
Integration

所有跨模块通信应使用明确的数据结构。

Agent、API、Solver、Simulation 不允许相互传递未经定义的任意 dict。

优先使用：

Pydantic Schema

Typed Models

Enum

Protocol / Abstract Interface

# 十二、调度方案版本化

必须设计：

ScheduleVersion。

任何重调度不能直接覆盖历史方案。

例如：

V1 Original

V2 Vehicle Failure Reschedule

V3 Weather Reschedule

必须能够比较：

changed_tasks

added_cost

delay_difference

resource_changes

affected_orders

constraint_results

使整个调度过程可审计、可解释、可回放。

# 十三、测试场景

至少设计三类 Demo Scenario。

Scenario A：

正常冷链物流运输。

Scenario B：

仓储 + 运输联合调度。

Scenario C：

运行期间发生异常并执行局部重调度。

Scenario C 至少包含：

车辆故障

订单取消

天气变化

三个子场景。

必须能够展示：

原方案

异常

影响范围

候选方案

新方案

方案差异

关键指标变化

# 十四、评价指标

至少支持：

需求满足率

订单准时率

平均延误

运输总距离

运输总成本

车辆利用率

仓储利用率

月台利用率

设备利用率

求解时间

异常检测时间

重调度时间

被修改任务数量

方案扰动程度

# 十五、禁止过早设计

以下功能不得影响核心 MVP：

复杂权限系统

复杂微服务架构

Kubernetes

消息队列集群

大规模分布式数据库

复杂 GIS Server

真实企业 ERP/WMS/TMS 全量集成

高精度 Blender 模型

复杂 3D 游戏引擎

先确保：

调度正确

异常可以重调度

Agent 可以正确调用 Solver

数字孪生可以推演

Demo 可以复现。

# 十六、最终要求

最终不要只给我一个开发计划。

你必须生成一个完整的：

AI-CODING-PLAN

使我能够按照：

Master Plan
↓
Task Graph
↓
Module Prompt
↓
Coding
↓
Testing
↓
Gate
↓
Next Module

逐步完成整个仓库。

每个阶段都要存在 Gate。

如果 Gate 未通过：

禁止进入下一阶段。

在正式生成所有 Coding Prompt 前，先输出：

1. Architecture Overview
2. Module Map
3. Dependency Graph
4. Phase Plan
5. Prompt Tree
6. Major Technical Risks
7. 推荐调整项

然后再生成详细 Prompt。

整个规划应以「另一个 Codex 可以在不了解历史聊天记录的情况下，仅阅读对应 Prompt 就能够完成任务」作为 Prompt 完整性的判断标准。