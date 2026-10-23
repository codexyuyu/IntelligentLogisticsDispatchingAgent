# P28-01 · 实现数字孪生场景、暂停、步进和事件注入

计划版本1.0.3 · 状态planned · 阶段Gate G28

## Context

你是本项目的Coding Agent。本项目以LLM工具调用 + OR-Tools确定性优化 + SimPy推演 + FastAPI/React/PostgreSQL实现冷链优先调度。当前任务位于Phase 28「Digital Twin UI」，任务ID `P28-01`，负责方 `A`。只执行本任务，不实现整个模块或后续阶段。

本Prompt连同仓库内契约足以工作，不依赖历史聊天。开始时读取以下本地规范；字段以契约实施后的唯一Python类型为准，文档若冲突先记录issue：

- [总体设计](../../../PROJECT_MASTER_PLAN.md)
- [领域模型](../../../docs/architecture/DOMAIN_CATALOG.md)
- [类型与Protocol](../../../docs/architecture/DATA_CONTRACTS.md)
- [HTTP与Tool](../../../docs/api/API_CONTRACT.md)
- [优化与硬约束](../../../docs/algorithms/OPTIMIZATION_CONTRACT.md)
- [仿真与回放](../../../docs/algorithms/SIMULATION_CONTRACT.md)
- [指标公式](../../../docs/algorithms/METRICS_CONTRACT.md)
- [测试数据](../../../docs/plan/TEST_FIXTURES.md)
- [内部接口与接线](../../../docs/architecture/IMPLEMENTATION_CONVENTIONS.md)
- [N01-R01规范决定附表](../../../contracts/changes/N01-R01-contract-decisions.json)
- [2.0.0迁移范围](../../../contracts/changes/N01-R01-contract-freeze-2.0.0.md)
- [Gate](../../../docs/plan/PHASE_GATES.md)

## Current State

理论上以下依赖已经交付且证据有效：`G27`。用TASK_GRAPH和Gate证据逐项核验，不能仅根据文件名存在认定完成。

本计划初始所有任务为planned，Gate为not_run；当前旧`demo/`是0.1骨架/展示资产，不代表本任务已实现。目标工作根为含PROJECT_MASTER_PLAN.md的目录，新包在apps/和packages/；旧demo只读，不从教学探针导入。若前置缺失/失败，报告具体阻断并修复前置任务，禁止跳Gate。

## Objective

实现数字孪生场景、暂停、步进和事件注入。唯一可验收交付物为下述Files对应实现/文档，以及本任务明确测试证据。

## Scope

仅实现 `simulation-controls-ui` 所属能力，遵循下面Business Rules和Algorithm。允许的实现、测试、文档文件完整列于Files。跨模块依赖通过既有Protocol注入。当前任务并行候选：无，按阶段内依赖顺序执行；即使列出候选，运行前仍检查实际写集合与依赖。

## Out of Scope

禁止顺手实现后续阶段、重新设计架构、改另一所有者实现掩盖集成错误、引入微服务/Kubernetes/队列集群/复杂GIS/复杂权限/3D关键依赖。测试替身不得进正式bootstrap。除Files及经明确记录的阻断契约迁移外，其他文件均不在范围。

## Architecture Constraints

1. Domain Contract → Schema → Service Interface → Implementation → Test → Integration，跨边界不传未经定义dict/Any。
2. LLM只抽取/分解/调用/解释，不自由生成最终调度；Agent只经工具到应用服务，不能直写数据库。
3. Solver候选必须经确定性独立硬校验；正式提交只能由ScheduleService完成，重排追加ScheduleVersion不覆盖历史。
4. Domain不导入框架/ORM/模型SDK；application不导入adapters，bootstrap唯一装配点；React不硬编码业务规则或另写枚举。
5. 不擅自改公共接口。发现架构问题先记录`docs/architecture/issues/`；非阻断继续限定任务，阻断只做最小契约迁移并更新所有受影响调用方/测试/导出物，禁止大规模重构。
6. 禁止TODO占位核心逻辑、fake implementation、hard-coded demo answer、绕过Solver、只写代码不写测试、吞掉Exception、重复定义Domain Model。开发时未实现部分必须显式失败，不能返回固定成功。

## Files

预计创建（若前置已创建则仅核对并增量修改）：

- `apps/frontend/src/features/simulation/Controls.tsx`
- `apps/frontend/src/features/simulation/Page.tsx`
- `apps/frontend/src/test/p28_01_simulation_controls_ui.integration.test.tsx`
- `apps/frontend/src/test/p28_01_simulation_controls_ui.unit.test.tsx`
- `docs/implementation/P28-01.md`
- `docs/implementation/reports/P28-01.md`

预计修改已有前置产物：

- 无；如运行时已存在同名文件，核对前置产物后只做本任务范围增量。

禁止修改：`demo/`、`demos/`教学代码、非本任务文件、已提交历史版本或审计内容。`contracts/*.json`和`generated.ts`若列入范围只能运行生成器更新，不得手改。包marker只有确需导出本任务类型时可修改，须先在完成报告列出精确路径；不能借此越过接口边界。

## Domain Model

SimulationView、SimulationControl、EventEnvelope。实体字段/状态/生命周期以DOMAIN_CATALOG为准；本任务新增的非实体view只组合既有字段。每实体继承UUID、唯一status Enum、UTC created_at/updated_at、row_version、schema_version，不复制业务模型。

## Input

正式输入由Interfaces的签名左侧和DATA_CONTRACTS相应具名Schema定义：

UI Props从生成OpenAPI类型组合。QueryState为loading/ready/empty/error/stale/cancelled判别联合；业务ID和enum从generated.ts引用。JobRef与版本状态分开；显示秒/米/克/分到用户单位时仅格式转换，不重算调度。

必须覆盖Test Cases给出的具体输入变体；使用TEST_FIXTURES的完整T1/W1/I1/S1/M1定义，未指出的字段保持原值。HTTP边界额外携带actor、trace_id、Idempotency-Key或If-Match（按API_CONTRACT）。

## Output

返回Interfaces右侧的具名结果/明确文件产物，包含本任务Test Cases所列可观察值；不能只返回任意dict或成功布尔。业务失败保留类型化原因；候选/已验证/已确认分别表达；任何正式新方案必须带version_id、parent_version_id、snapshot_hash和校验引用。本文档/测试任务只返回证据，不生成调度数据。

## Interfaces

本任务采用以下精确公开入口；多个入口用分号分隔，HTTP路径均带API_CONTRACT前缀：

```text
SimulationPage() -> ReactElement
```

新实现放在本任务Files并导出到既有组合根/注册入口时仅做必要装配；第三方引擎对象留在adapter内部。若签名需扩展，不得先改后解释：先写`contracts/changes/`说明输入输出影响。

## Data Contract

UI Props从生成OpenAPI类型组合。QueryState为loading/ready/empty/error/stale/cancelled判别联合；业务ID和enum从generated.ts引用。JobRef与版本状态分开；显示秒/米/克/分到用户单位时仅格式转换，不重算调度。

共享单位：整数秒/米/克/cm³/分/decic，UTC epoch；服务开始窗闭区间，占用[start,end)。业务契约版本2.0.0，Gate证据schema仍1.0.0；边界extra=forbid。N01-R01新增必需字段/enum/引用规则是本轮破坏设计决定，旧1.0.0不能只改版本号沿用；按迁移说明显式转换与重验。Optional、未知、无解、超时的语义不得混淆；参考DATA_CONTRACTS的SolveStatus/JobStatus/错误表。

## Business Rules

明确simulation时间与现实时间；control_seq幂等；3D非依赖；仿真注入不修改正式订单。

所有业务结果绑定输入快照和规则版本。空输入仅在契约允许零需求时可返回有效空结果；有必需需求却无解不能返回空路线成功。已执行事实与已确认历史不可改写。

## Algorithm

选场景/版本→启动→轮询→暂停/步进/恢复；事件表单使用typed payload和simulation_id。

按已冻结的接口完成上述步骤；纯领域规则不引入框架，副作用经所属应用服务；不得为本任务新建第二套算法或规则。

## Edge Cases

必须处理：暂停t150 => 时钟保持150；注入天气事件 => 请求含当前simulation_id。

共同边界按本任务适用范围测试：空集合、重复ID、非法枚举/单位、负值/整数溢出、缺失关联、边界时间相等、过期revision、取消/超时、依赖不可用。对不适用项在Completion Report说明，不为制造覆盖率添加无意义断言。

## Error Handling

输入契约错误→INVALID_INPUT/422；非法状态→INVALID_TRANSITION；请求未知必需能力→INVALID_INPUT/422并用UnsupportedDetail说明，拒绝有效结果；独立硬校验发现未支持规则时保留unsupported_codes且不得报告有效候选；开发期间未实现能力仍按DATA_CONTRACTS返回501且不得进入对应Gate，不自造UNSUPPORTED错误码；版本/资源/幂等冲突→409；权限→401/403；依赖不可用→503。求解TIMEOUT/UNKNOWN/INFEASIBLE为typed结果，不统一包装成500。

仅捕获明确可处理的第三方异常并保留cause/trace；边界可最后捕获未预期错误记录脱敏stack并返回INTERNAL_ERROR，禁止except Exception: pass。重试仅幂等暂态操作，有最大次数与deadline；不重试业务硬约束失败。

## Logging

事件名使用 `p28_01.started/completed/rejected`（纯函数由调用边界记录）。记录operation、trace_id、输入/输出hash、schema_version、结果状态、duration_ms、明确错误码；涉及求解追加引擎版本/配置/seed，涉及版本追加base/candidate/version引用。禁止输出secret、完整个人数据或模型内部思维。文档任务保存检查日志与文件hash。

## Observability

页面加载/错误/交互耗时及接口失败次数（测试证据中可观测）；不新增订单级用户跟踪。

不得用order_id/vehicle_id/trace_id作metric标签；这些只在日志或trace。此阶段还没有完整监控backend时，先输出结构化测量/诊断，P37接统一出口；不能因此跳过可观察结果。

## Testing

- Unit Test：`apps/frontend/src/test/p28_01_simulation_controls_ui.unit.test.tsx`；测试本任务规则/转换/状态或文档检查负例。
- Integration Test：`apps/frontend/src/test/p28_01_simulation_controls_ui.integration.test.tsx`；验证真实相邻模块的数据/服务边界；涉及数据库使用隔离真实PostgreSQL。
- Integration Test是组件+生成客户端+MSW网络边界测试；Phase34另用真实API浏览器验收。不要把MSW测试称生产后端已接通。
- 所有测试均有确定数据和预期，不用固定假成功掩盖缺失实现；命令零用例或关键skip视为未验收。

## Test Cases

| 编号 | 明确输入 → 预期结果 | 断言要求 |
| --- | --- | --- |
| 1 | 暂停t150 => 时钟保持150 | 必须按箭头右侧断言；禁止只断言status非空。 |
| 2 | 注入天气事件 => 请求含当前simulation_id | 必须按箭头右侧断言；禁止只断言status非空。 |

正例数值来自TEST_FIXTURES手算；负例一次仅改指定字段，明确断言错误码/违规位置及无副作用。多可行解场景检查不变量/目标容许范围，不随意固定solver搜索顺序。

## Acceptance Criteria

1. Objective与Files交付完全对应，本任务所有具体Test Cases通过。
2. 下列命令实际执行且exit code=0，记录真实测试数量，不含关键skip/占位返回；编译成功不等于业务通过。
3. 无共享类型/生成客户端漂移，依赖边界检查通过；失败路径不产生半计划或伪成功。
4. 完成报告和任务文档齐备，并将证据交 `G28`：仿真暂停/步进/注入/快照/分支比较可操作；正式状态不污染，3D不是必要依赖。
5. 单任务成功不自动使Gate成功；当前Gate未通过，禁止开始下一Phase。

## Validation Commands

从仓库根目录执行。Phase01之后使用已锁定环境；数据库任务先按环境手册启动隔离PostgreSQL。以下为完成本任务后的强制命令，**本轮规划没有执行未来应用测试**：

```powershell
npm run test --workspace apps/frontend -- --run p28_01_simulation_controls_ui.unit.test.tsx p28_01_simulation_controls_ui.integration.test.tsx
npm run contracts:check --workspace apps/frontend
npm run build --workspace apps/frontend
```

如工具/依赖/凭据不可用，保留实际错误并记录未执行项，不能写全部通过。修改失败后只重跑受影响测试和必需Gate；不得在未通过时跳阶段。

## Documentation

更新 `docs/implementation/P28-01.md`：已实现能力、接口/单位、输入输出样例、状态与失败语义、实际限制、关联测试。完成报告写 `docs/implementation/reports/P28-01.md`。公共契约变化另追加contracts/changes说明及架构issue，重新导出Schema/OpenAPI/TS并重验受影响Gate，不通过聊天补交接。

## Completion Report

最终答复和报告必须逐项包含：

- Files created（精确路径）
- Files modified（精确路径及原因）
- Tests added（文件、用例和覆盖的业务边界）
- Commands executed（实际命令、工作目录、环境）
- Test results（exit code、passed/failed/skipped数量、原始日志与产物位置）
- Known limitations（支持/不支持及用户可见行为）
- Remaining risks（有证据的风险、影响、下一责任任务）

另记录Task ID、契约版本前后、输入/输出hash、当前代码revision/相关文件hash、Gate证据引用。不得声称尚未运行的测试通过，不把本任务完成说成整个系统完成。
