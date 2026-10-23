# DSH / ZCode / WorkBuddy 提示词派发顺序

2026-10-04 整理；规划 1.0.3。本清单是条件式派发索引，不是任务已执行或验收通过的记录。每项只在真实前置成立后发送。

核对时 N01-R02 已停写，N02-R02 已有部分日志但尚无最终交接，现行执行器仍拒绝 G00；当前候选为 `content-sha256:d1c94436a020158a0573d290443c7c6799711da6564b1609a294fb332d8b7f63`。状态变化后以新正式证据为准。

## 现在至 G01 的派发顺序

| 顺序 / 启动条件 | 接收者 | 交付目标 | 可直接发送的提示词 |
| --- | --- | --- | --- |
| 现在，主审协调 | 独立 Codex | N02-R02：分区复核并恢复 G00 | [打开提示词](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/agent-toolchain/13-partitioned-parallel-dispatch.md) |
| 现在，可与主审并行 | ZCode 独立会话 | N02-R02-C：EntityKind 和事件引用映射复核 | [打开提示词](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-04/parallel/messages/zcode/N02-R02-contract.md) |
| 现在，可与复核并行 | WorkBuddy | 当前证据索引草稿 | [打开提示词](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-04/parallel/messages/workbuddy/current-evidence-index.md) |
| G00 实际恢复并核验有效后 | DSH-A | N03：刷新 Phase 01 三任务自身交接 | [打开提示词](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-04/parallel/messages/dsh/N03.md) |
| N03 对应候选交审并停写后 | ZCode 独立会话 | N04：独立重验 Phase 01 三任务 | [打开提示词](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/now/N04.md) |
| 三项 precheck 有效、候选固定后 | 独立 Codex | N05：阶段审查并签收 G01 | [打开提示词](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/now/N05.md) |

本轮已有分区主写者或正式交付时先核对实际记录，不向同一输出目录重复派发第二写者。WorkBuddy 产物供核对采用，额度不足不阻断主链。

## 并发方式

- [分区并发开发与验收规则](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/agent-toolchain/13-partitioned-parallel-dispatch.md)：依赖成立、文件分区无交集后，可由 DSH/Codex/ZCode 开发；每文件一个写者，共享文件一个整合者。
- 分区完成停写后可交独立审查，其他独立分区继续开发。常规执行器仍读取 DSH 整合交接；正式 precheck 和 Gate 分别由未参与实现的独立 ZCode/Codex 会话完成。
- 下表 DSH 链接是正式实现/整合通道，ZCode 链接是独立预验收通道。ZCode/Codex 的开发贡献须另附精确分区卡；不把验收消息直接当成源码写授权。
- 同阶段下一任务按 manifest 的 deps 及真实交付/预验收启动；若分区共享文件、接口或依赖尚未就绪，先由整合者处理。正式阶段 Gate 须等待全部必需证据成立。

## WorkBuddy 的后续辅助顺序

| 启动条件 | 工作 | 提示词 |
| --- | --- | --- |
| 当前，可与 N02-R02 并行 | 证据索引草稿 | [给 WorkBuddy](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-04/parallel/messages/workbuddy/current-evidence-index.md) |
| G24 有效，页面接口固定后 | 页面状态、按钮和标签中文文案草稿 | [给 WorkBuddy](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/workbuddy/frontend-copy.md) |
| G35 有效，五场景证据归档后 | A/B/C1/C2/C3 演示证据索引 | [给 WorkBuddy](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/workbuddy/demo-evidence-index.md) |
| G37 有效，真实操作步骤可读取后 | 操作文档格式与步骤索引 | [给 WorkBuddy](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/workbuddy/operator-doc-copy.md) |
| P39-01 发布候选固定后 | 发布说明及限制的排版草稿 | [给 WorkBuddy](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/workbuddy/release-note-copy.md) |

## G01 通过后：Phase 02–39 完整开发顺序

下面共有 103 项后续任务，每项附实现、独立预验收和完整任务书链接。按真实依赖启动，不从 manifest 初始 planned/not_run 值推断完成状态。

### Phase 02 · Domain Model → G02

阶段入口：G01 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P02-01 | 实现领域 ID、单位与唯一状态枚举 | DSH-A | G01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P02-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P02-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/02-domain/P02-01-primitives-and-states.md) |
| P02-02 | 实现订单、货物与运仓资源领域模型 | DSH-A | G01, P02-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P02-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P02-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/02-domain/P02-02-master-entities.md) |
| P02-03 | 实现任务、版本与优化结果领域模型 | DSH-A | G01, P02-02 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P02-03.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P02-03.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/02-domain/P02-03-planning-entities.md) |
| P02-04 | 实现运行记录模型与 Schema 导出 | DSH-A | G01, P02-03 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P02-04.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P02-04.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/02-domain/P02-04-runtime-contract-export.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G02 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G02.md)。

### Phase 03 · PostgreSQL Schema + Migration → G03

阶段入口：G02 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P03-01 | 创建主数据与资源迁移 | DSH-A | G02 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P03-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P03-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/03-database/P03-01-resource-schema.md) |
| P03-02 | 创建不可变计划、运行与审计迁移 | DSH-A | G02, P03-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P03-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P03-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/03-database/P03-02-planning-schema.md) |
| P03-03 | 实现快照读取与事务工作单元 | DSH-A | G02, P03-02 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P03-03.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P03-03.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/03-database/P03-03-repositories-and-snapshot.md) |
| P03-04 | 实现版本 CAS、资源预留与幂等存储 | DSH-A | G02, P03-03 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P03-04.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P03-04.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/03-database/P03-04-atomic-version-store.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G03 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G03.md)。

### Phase 04 · Seed / Synthetic Dataset → G04

阶段入口：G03 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P04-01 | 生成可手算的合成场景与反例数据 | DSH-A | G03 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P04-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P04-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/01-foundation/P04-01-canonical-fixtures.md) |
| P04-02 | 实现可重复执行的数据库种子导入 | DSH-A | G03, P04-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P04-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P04-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/01-foundation/P04-02-database-seed.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G04 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G04.md)。

### Phase 05 · FastAPI 基础服务 → G05

阶段入口：G04 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P05-01 | 建立 FastAPI 组合根、错误协议与基础鉴权 | DSH-A | G04 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P05-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P05-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/04-api/P05-01-api-composition.md) |
| P05-02 | 实现主数据分页读写服务与资源日历 API | DSH-A | G04, P05-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P05-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P05-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/04-api/P05-02-master-data-services.md) |
| P05-03 | 实现作业租约、超时取消与受限 worker | DSH-A | G04, P05-02 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P05-03.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P05-03.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/04-api/P05-03-durable-jobs.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G05 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G05.md)。

### Phase 06 · Transport Optimization Domain → G06

阶段入口：G05 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P06-01 | 实现运输请求、结果和 Solver Protocol | DSH-B | G05 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P06-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P06-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/05-transport-solver/P06-01-transport-contract.md) |
| P06-02 | 实现版本化道路距离和时间矩阵提供器 | DSH-B | G05 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P06-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P06-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/05-transport-solver/P06-02-distance-matrix.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G06 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G06.md)。

### Phase 07 · Transport Solver → G07

阶段入口：G06 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P07-01 | 实现多起终点车辆路径基本求解 | DSH-B | G06 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P07-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P07-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/05-transport-solver/P07-01-vrp-base.md) |
| P07-02 | 实现重量、容积和提送货载荷约束 | DSH-B | G06, P07-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P07-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P07-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/05-transport-solver/P07-02-capacity-and-pickup.md) |
| P07-03 | 实现服务时间、等待、班次与硬时间窗 | DSH-B | G06, P07-02 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P07-03.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P07-03.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/05-transport-solver/P07-03-time-windows.md) |
| P07-04 | 实现温区、货物类型与车辆允许集合 | DSH-B | G06, P07-03 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P07-04.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P07-04.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/05-transport-solver/P07-04-temperature-and-cargo.md) |
| P07-05 | 实现可解释费用与可选订单目标函数 | DSH-B | G06, P07-04 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P07-05.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P07-05.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/05-transport-solver/P07-05-objective-function.md) |
| P07-06 | 实现运输结果提取、状态映射和独立重算 | DSH-B | G06, P07-05 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P07-06.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P07-06.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/05-transport-solver/P07-06-result-status-validation.md) |
| P07-07 | 装配运输 Solver 并验证数值与预算边界 | DSH-B | G06, P07-06 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P07-07.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P07-07.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/05-transport-solver/P07-07-transport-adapter.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G07 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G07.md)。

### Phase 08 · Warehouse Optimization Domain → G08

阶段入口：G07 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P08-01 | 实现仓储任务与资源日历协议 | DSH-A | G07 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P08-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P08-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/06-warehouse-solver/P08-01-warehouse-contract.md) |
| P08-02 | 实现库存占用和仓运交接约束模型 | DSH-A | G07, P08-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P08-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P08-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/06-warehouse-solver/P08-02-inventory-and-handoffs.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G08 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G08.md)。

### Phase 09 · Warehouse Scheduler → G09

阶段入口：G08 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P09-01 | 实现仓储区间、互斥资源与任务依赖 | DSH-A | G08 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P09-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P09-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/06-warehouse-solver/P09-01-intervals-precedence.md) |
| P09-02 | 实现人员、设备和温区容量限制 | DSH-A | G08, P09-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P09-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P09-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/06-warehouse-solver/P09-02-cumulative-resources.md) |
| P09-03 | 实现库位库存区间和冷链容量约束 | DSH-A | G08, P09-02 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P09-03.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P09-03.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/06-warehouse-solver/P09-03-storage-capacity.md) |
| P09-04 | 实现清洁及月台、温区、分拣切换时间 | DSH-A | G08, P09-03 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P09-04.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P09-04.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/06-warehouse-solver/P09-04-sequence-setup.md) |
| P09-05 | 装配仓储目标、结果提取与独立校验 | DSH-A | G08, P09-04 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P09-05.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P09-05.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/06-warehouse-solver/P09-05-warehouse-result.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G09 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G09.md)。

### Phase 10 · Constraint Validator → G10

阶段入口：G09 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P10-01 | 实现统一校验报告与约束覆盖注册表 | DSH-A | G09 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P10-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P10-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/06-warehouse-solver/P10-01-validator-protocol.md) |
| P10-02 | 实现跨仓运链、库存和资源完整校验 | DSH-A | G09, P10-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P10-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P10-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/06-warehouse-solver/P10-02-joint-validator.md) |
| P10-03 | 建立独立硬约束反例与小规模 oracle 套件 | DSH-A | G09, P10-02 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P10-03.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P10-03.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/06-warehouse-solver/P10-03-validator-adversarial-suite.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G10 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G10.md)。

### Phase 11 · Simulation Domain → G11

阶段入口：G10 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P11-01 | 实现仿真场景、状态、快照与随机源契约 | DSH-B | G10 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P11-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P11-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/07-simulation/P11-01-simulation-contract.md) |
| P11-02 | 实现订单、车辆和仓库执行状态转换 | DSH-B | G10, P11-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P11-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P11-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/07-simulation/P11-02-execution-state-machine.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G11 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G11.md)。

### Phase 12 · SimPy Digital Twin → G12

阶段入口：G11 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P12-01 | 实现 SimPy 时间推进与稳定事件调度内核 | DSH-B | G11 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P12-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P12-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/07-simulation/P12-01-simpy-kernel.md) |
| P12-02 | 实现车辆移动、服务与订单交付过程 | DSH-B | G11, P12-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P12-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P12-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/07-simulation/P12-02-transport-execution.md) |
| P12-03 | 实现仓储资源争用、作业与库存演化 | DSH-B | G11, P12-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P12-03.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P12-03.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/07-simulation/P12-03-warehouse-execution.md) |
| P12-04 | 实现快照恢复和反事实分支隔离 | DSH-B | G11, P12-02, P12-03 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P12-04.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P12-04.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/07-simulation/P12-04-snapshot-replay.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G12 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G12.md)。

### Phase 13 · Event Engine → G13

阶段入口：G12 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P13-01 | 实现十类异常事件的校验、去重与排序 | DSH-A 整合 / B 分区贡献 | G12 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P13-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P13-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/07-simulation/P13-01-event-ingestion.md) |
| P13-02 | 实现事件注入服务及持久化分发 | DSH-A | G12, P13-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P13-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P13-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/07-simulation/P13-02-event-api-and-outbox.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G13 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G13.md)。

### Phase 14 · Exception Impact Analyzer → G14

阶段入口：G13 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P14-01 | 实现异常影响依赖图与最小闭包 | DSH-A | G13 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P14-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P14-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/08-exception/P14-01-impact-graph.md) |
| P14-02 | 实现不可逆事实、在途起点与重排边界提取 | DSH-A | G13, P14-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P14-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P14-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/08-exception/P14-02-execution-freeze.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G14 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G14.md)。

### Phase 15 · Local Rescheduling Engine → G15

阶段入口：G14 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P15-01 | 实现局部候选策略与救援交接任务生成 | DSH-A | G14 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P15-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P15-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/08-exception/P15-01-candidate-policies.md) |
| P15-02 | 实现冻结边界下的局部重新求解 | DSH-A | G14, P15-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P15-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P15-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/08-exception/P15-02-local-solve.md) |
| P15-03 | 实现局部扩展与全局剩余任务降级策略 | DSH-A | G14, P15-02 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P15-03.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P15-03.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/08-exception/P15-03-bounded-escalation.md) |
| P15-04 | 实现版本差异与候选排序 | DSH-A | G14, P15-03 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P15-04.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P15-04.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/08-exception/P15-04-version-diff.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G15 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G15.md)。

### Phase 16 · Optimization API → G16

阶段入口：G15 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P16-01 | 实现运输、仓储和重排作业 API | DSH-A | G15 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P16-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P16-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/04-api/P16-01-optimization-job-api.md) |
| P16-02 | 实现有界仓运窗口反馈协调服务 | DSH-A | G15, P16-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P16-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P16-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/04-api/P16-02-joint-planning-service.md) |
| P16-03 | 实现重新校验后的版本确认服务 | DSH-A | G15, P16-02 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P16-03.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P16-03.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/04-api/P16-03-validated-commit-api.md) |
| P16-04 | 实现仿真控制、版本对比与结果查询 API | DSH-A | G15, P16-03 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P16-04.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P16-04.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/04-api/P16-04-simulation-query-api.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G16 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G16.md)。

### Phase 17 · Agent Tool Protocol → G17

阶段入口：G16 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P17-01 | 实现 Agent 标准工具注册、权限与参数协议 | DSH-A | G16 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P17-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P17-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/09-agents/P17-01-tool-schemas.md) |
| P17-02 | 实现工具到业务服务的唯一适配层 | DSH-A | G16, P17-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P17-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P17-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/09-agents/P17-02-business-tools.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G17 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G17.md)。

### Phase 18 · LLM Provider Abstraction → G18

阶段入口：G17 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P18-01 | 实现模型供应商抽象与结构化响应边界 | DSH-A | G17 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P18-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P18-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/09-agents/P18-01-llm-provider.md) |
| P18-02 | 实现模型预算、重试、脱敏与故障降级 | DSH-A | G17, P18-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P18-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P18-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/09-agents/P18-02-llm-resilience.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G18 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G18.md)。

### Phase 19 · Coordinator Agent → G19

阶段入口：G18 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P19-01 | 实现 Coordinator 意图及约束抽取 | DSH-A | G18 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P19-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P19-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/09-agents/P19-01-intent-extraction.md) |
| P19-02 | 实现 Coordinator 任务分解与有界运行状态机 | DSH-A | G18, P19-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P19-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P19-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/09-agents/P19-02-coordinator-state-machine.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G19 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G19.md)。

### Phase 20 · Transport Agent → G20

阶段入口：G19 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P20-01 | 实现 TransportAgent 求解工具工作流 | DSH-A | G19 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P20-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P20-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/09-agents/P20-01-transport-agent-tools.md) |
| P20-02 | 实现有证据的运输结果解释 | DSH-A | G19, P20-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P20-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P20-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/09-agents/P20-02-transport-explanation.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G20 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G20.md)。

### Phase 21 · Warehouse Agent → G21

阶段入口：G20 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P21-01 | 实现 WarehouseAgent 排程与窗口报价工作流 | DSH-A | G20 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P21-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P21-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/09-agents/P21-01-warehouse-agent-tools.md) |
| P21-02 | 实现仓储甘特与资源瓶颈解释数据 | DSH-A | G20, P21-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P21-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P21-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/09-agents/P21-02-warehouse-explanation.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G21 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G21.md)。

### Phase 22 · Exception Agent → G22

阶段入口：G21 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P22-01 | 实现 ExceptionAgent 九步处置工作流 | DSH-A | G21 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P22-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P22-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/09-agents/P22-01-exception-agent-tools.md) |
| P22-02 | 实现异常处置链和版本差异解释 | DSH-A | G21, P22-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P22-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P22-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/09-agents/P22-02-exception-explanation.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G22 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G22.md)。

### Phase 23 · Agent Orchestration → G23

阶段入口：G22 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P23-01 | 实现四角色路由、取消与有界协调 | DSH-A | G22 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P23-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P23-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/09-agents/P23-01-agent-orchestration.md) |
| P23-02 | 实现 Agent 会话 API 与攻击性输入验收 | DSH-A | G22, P23-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P23-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P23-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/09-agents/P23-02-agent-api-safety.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G23 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G23.md)。

### Phase 24 · React Application Shell → G24

阶段入口：G23 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P24-01 | 建立 React 应用壳、路由与统一状态展示 | DSH-A | G23 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P24-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P24-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/10-frontend/P24-01-react-shell.md) |
| P24-02 | 建立 OpenAPI 生成客户端和数据请求层 | DSH-A | G23, P24-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P24-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P24-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/10-frontend/P24-02-generated-api-client.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G24 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G24.md)。

可选并行 WorkBuddy：G24 有效，页面接口固定后，[页面状态、按钮和标签中文文案草稿](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/workbuddy/frontend-copy.md)。

### Phase 25 · Orders / Vehicles / Warehouses UI → G25

阶段入口：G24 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P25-01 | 实现订单查询、编辑和取消事件入口 | DSH-A | G24 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P25-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P25-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/10-frontend/P25-01-orders-ui.md) |
| P25-02 | 实现车辆、司机和可用日历页面 | DSH-A | G24 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P25-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P25-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/10-frontend/P25-02-vehicles-ui.md) |
| P25-03 | 实现仓库、温区、库位及作业资源页面 | DSH-A | G24 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P25-03.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P25-03.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/10-frontend/P25-03-warehouses-ui.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G25 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G25.md)。

### Phase 26 · Transport Scheduling UI → G26

阶段入口：G25 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P26-01 | 实现运输请求、作业进度与不可行诊断页面 | DSH-A | G25 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P26-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P26-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/10-frontend/P26-01-transport-request-ui.md) |
| P26-02 | 实现路线、逐站执行表和候选确认视图 | DSH-A | G25, P26-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P26-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P26-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/10-frontend/P26-02-transport-plan-ui.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G26 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G26.md)。

### Phase 27 · Warehouse Scheduling UI → G27

阶段入口：G26 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P27-01 | 实现仓储请求和资源甘特图 | DSH-A | G26 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P27-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P27-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/10-frontend/P27-01-warehouse-gantt-ui.md) |
| P27-02 | 实现仓运交接与联合方案对照视图 | DSH-A | G26, P27-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P27-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P27-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/10-frontend/P27-02-joint-handoff-ui.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G27 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G27.md)。

### Phase 28 · Digital Twin UI → G28

阶段入口：G27 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P28-01 | 实现数字孪生场景、暂停、步进和事件注入 | DSH-A | G27 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P28-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P28-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/10-frontend/P28-01-simulation-controls-ui.md) |
| P28-02 | 实现快照回放和反事实分支对比 | DSH-A | G27, P28-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P28-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P28-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/10-frontend/P28-02-replay-comparison-ui.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G28 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G28.md)。

### Phase 29 · Exception Center UI → G29

阶段入口：G28 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P29-01 | 实现异常列表、影响图和处置流水 | DSH-A | G28 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P29-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P29-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/10-frontend/P29-01-exception-center-ui.md) |
| P29-02 | 实现候选比较、版本差异和重排确认 | DSH-A | G28, P29-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P29-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P29-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/10-frontend/P29-02-reschedule-diff-ui.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G29 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G29.md)。

### Phase 30 · Agent Chat UI → G30

阶段入口：G29 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P30-01 | 实现聊天、澄清和工具执行状态页面 | DSH-A | G29 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P30-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P30-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/10-frontend/P30-01-agent-chat-ui.md) |
| P30-02 | 实现有证据的建议确认与风险提示 | DSH-A | G29, P30-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P30-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P30-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/10-frontend/P30-02-agent-confirmation-ui.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G30 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G30.md)。

### Phase 31 · WebSocket Real-time System → G31

阶段入口：G30 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P31-01 | 实现带游标的实时事件与断线补偿服务 | DSH-A | G30 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P31-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P31-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/10-frontend/P31-01-websocket-events.md) |
| P31-02 | 实现前端实时订阅与轮询回退 | DSH-A | G30, P31-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P31-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P31-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/10-frontend/P31-02-frontend-realtime.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G31 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G31.md)。

### Phase 32 · Metrics / Evaluation → G32

阶段入口：G31 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P32-01 | 实现14项调度指标与统一统计口径 | DSH-A | G31 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P32-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P32-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/11-evaluation/P32-01-metric-calculators.md) |
| P32-02 | 实现指标持久化、版本比较与 Dashboard 聚合 | DSH-A | G31, P32-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P32-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P32-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/11-evaluation/P32-02-metrics-api.md) |
| P32-03 | 实现 Dashboard 与 Metrics 图表页面 | DSH-A | G31, P32-02 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P32-03.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P32-03.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/11-evaluation/P32-03-metrics-dashboard-ui.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G32 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G32.md)。

### Phase 33 · Experiment Framework → G33

阶段入口：G32 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P33-01 | 实现对照实验、配对随机种子与结果留档 | DSH-A | G32 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P33-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P33-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/11-evaluation/P33-01-experiment-runner.md) |
| P33-02 | 实现实验创建、进度、结果与导出工作台 | DSH-A | G32, P33-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P33-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P33-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/11-evaluation/P33-02-experiments-api-ui.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G33 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G33.md)。

### Phase 34 · End-to-End Integration → G34

阶段入口：G33 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P34-01 | 建立真实数据库运输请求到确认的端到端验收 | DSH-A | G33 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P34-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P34-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/12-integration/P34-01-transport-e2e.md) |
| P34-02 | 建立仓运联合与异常重排的完整端到端验收 | DSH-A | G33, P34-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P34-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P34-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/12-integration/P34-02-joint-exception-e2e.md) |
| P34-03 | 建立崩溃、并发、模型断线与陈旧提交验收 | DSH-A | G33, P34-02 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P34-03.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P34-03.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/12-integration/P34-03-failure-recovery-e2e.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G34 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G34.md)。

### Phase 35 · Demo Scenario → G35

阶段入口：G34 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P35-01 | 交付 Scenario A 正常冷链运输演示 | DSH-A | G34 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P35-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P35-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/12-integration/P35-01-demo-normal.md) |
| P35-02 | 交付 Scenario B 仓储和运输联合演示 | DSH-A | G34, P35-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P35-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P35-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/12-integration/P35-02-demo-joint.md) |
| P35-03 | 交付 Scenario C1 车辆故障局部重排演示 | DSH-A | G34, P35-02 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P35-03.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P35-03.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/12-integration/P35-03-demo-vehicle-failure.md) |
| P35-04 | 交付 Scenario C2 订单取消局部重排演示 | DSH-A | G34, P35-03 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P35-04.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P35-04.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/12-integration/P35-04-demo-order-cancel.md) |
| P35-05 | 交付 Scenario C3 天气变化与一键复现演示包 | DSH-A | G34, P35-04 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P35-05.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P35-05.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/12-integration/P35-05-demo-weather.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G35 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G35.md)。

可选并行 WorkBuddy：G35 有效，五场景证据归档后，[A/B/C1/C2/C3 演示证据索引](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/workbuddy/demo-evidence-index.md)。

### Phase 36 · Performance Optimization → G36

阶段入口：G35 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P36-01 | 建立可重复的容量、耗时和内存基准 | DSH-A | G35 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P36-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P36-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/12-integration/P36-01-benchmark-harness.md) |
| P36-02 | 实现有内存上限的版本化矩阵缓存并复验 | 按已裁定 A/B 分区，DSH 整合 | G35, P36-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P36-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P36-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/12-integration/P36-02-bounded-performance-fix.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G36 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G36.md)。

### Phase 37 · Security / Audit / Observability → G37

阶段入口：G36 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P37-01 | 验证并修复访问控制、输入边界和依赖安全 | DSH-A | G36 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P37-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P37-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/12-integration/P37-01-security-boundary.md) |
| P37-02 | 实现全链追踪、指标端点和审计可检索性 | DSH-A | G36, P37-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P37-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P37-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/12-integration/P37-02-observability-audit.md) |
| P37-03 | 验证数据库备份恢复、迁移回滚与作业恢复 | DSH-A | G36, P37-02 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P37-03.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P37-03.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/12-integration/P37-03-backup-and-recovery.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G37 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G37.md)。

### Phase 38 · Documentation → G38

阶段入口：G37 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P38-01 | 交付与实际实现一致的架构、API和算法文档 | DSH-A | G37 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P38-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P38-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/13-release/P38-01-developer-docs.md) |
| P38-02 | 交付演示、异常处置、运维和模型配置手册 | DSH-A | G37, P38-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P38-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P38-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/13-release/P38-02-operator-docs.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G38 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G38.md)。

可选并行 WorkBuddy：G37 有效，真实操作步骤可读取后，[操作文档格式与步骤索引](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/workbuddy/operator-doc-copy.md)。

### Phase 39 · Release → G39

阶段入口：G38 有效。阶段结束后由独立 Codex 完成签收。

| 顺序 / 任务 | 目标 | 实现/整合 | 必需前置 | DSH 提示词 | ZCode 提示词 | 完整任务书 |
| --- | --- | --- | --- | --- | --- | --- |
| P39-01 | 生成可安装发布候选及完整性清单 | DSH-A | G38 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P39-01.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P39-01.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/13-release/P39-01-release-candidate.md) |
| P39-02 | 签收发布 Gate 与复现证据索引 | DSH-A | G38, P39-01 | [给 DSH](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/dsh/P39-02.md) | [给 ZCode](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/zcode/P39-02.md) | [原任务](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/prompts/13-release/P39-02-release-gate.md) |

全部必需任务完成且当前证据有效后：[给独立 Codex：G39 审查及签收](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/codex/G39.md)。

可选并行 WorkBuddy：P39-01 发布候选固定后，[发布说明及限制的排版草稿](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/artifacts/dispatch/2026-10-01/completion/messages/workbuddy/release-note-copy.md)。

## 交付判定

正式版本以当前有效的阶段证据、实际业务实现与必需真实依赖验收为准；完成发布链 G39 才是完整交付。每阶段附加断言按当前 PHASE_GATES 落实，缺执行器覆盖时由有明确范围的治理任务补齐。

原完整派发依据：[12-project-completion-dispatch.md](/D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent/docs/agent-toolchain/12-project-completion-dispatch.md)。
