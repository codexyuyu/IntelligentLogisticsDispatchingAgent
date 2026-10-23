> 当前决定：2026-10-03 N01-R01 decided（完整设计待独立复核）；G00阻断尚未经N02解除。下文旧发现/旧N01结论保留为历史，本轮末尾决定优先。

# ARCH-0007 早期具名类型字段与前向依赖缺口

- id：ARCH-0007
- status：open
- discovered_by_task：N01治理，按P02–P05接口及冻结契约逐项核验。
- title：ImportReceipt、Settings、MasterDataUpdate、JobRequest等具名类型缺完整字段/联合分支及可满足的类型依赖。
- evidence：[逐项审计](../TYPE_DEFINITION_OWNERSHIP.md)给出逐项类型的来源、定义任务和完整承载路径。P04-02只列ImportReceipt和inserted=0；P05-01只用Settings签名；P05-02用MasterDataUpdate但API表给多种命令；JobRequest在P05-03引用后续P06/P11/P14/P32能力的payload。当前正式包尚无业务定义，不能从现有源码复原字段。
- impact：P02完整类型/Schema导出以及P03–P05消费依赖无法仅凭当前描述验证；任意dict、空类、未来导入或复制DTO均不构成解决。
- blocking：yes；P02-01/P02-02/P02-04及相关P04/P05任务派发前，字段/引用/union未决项必须决定。N02独立判断这些缺口对冻结/G00的影响，本issue不冒作Gate结论。
- decision：归属与合法文件按审计/catalog决定；字段和JobRequest前向依赖保持open。A契约治理负责提交具体字段、判别成员、无未来导入的类型依赖、完整白名单、正反例及必要版本迁移，再独立复核。禁止交P03/P04/P05自造公共类型。
- owner：A契约治理；实施仅在已指派任务及其白名单中执行。
- links：[DATA_CONTRACTS](../DATA_CONTRACTS.md)、[迁移说明](../../../contracts/changes/N01-governance-1.0.1.md)。

## N01重复请求内复核修正（规划1.0.2）

原1.0.1审计将JobKind/JobStatus误指派到P02-04 runtime；已更正为P02-01 states.py唯一定义，P02-04/P05复用，catalog及DATA_CONTRACTS同步。JobKind成员未决阻断点前移到P02-01派发前，未猜测成员。补单列Resource及P05-02主数据端点过滤器、命令、分页、实体DTO、ResourceCalendar/CalendarDTO审计；简称的正式类型名证据不足保持未决。未新增业务实现或修改路径权限。


## N01-R01 完整决定（替代字段未决/仅下游派发限制）

- status：decided（完整设计）；READY_FOR_INDEPENDENT_REVIEW，非closed/Gate通过。
- blocking：yes，N02已经裁定G00冻结阻断；本轮实施者不得自行解除。独立N02重审新候选后决定。
- decision：JobKind五类及optimization三mode唯一states；CalendarInterval/ResourceCalendar在P02-01 primitives，新增必需epoch；ScenarioSpec/Ref/Bundle及直接嵌套事件/资源/Actor、JobCommand/RequestRef完整引用闭包早期唯一定义，禁止未来DTO导入。期望旁文件与正式运行输入严格分离。相关CLI/配置/主数据边界具名投影也明确字段/失败/版本语义，不再下发“请自造类型”。
- evidence：每项完整字段、依赖图、例子在[DATA本轮决定](../DATA_CONTRACTS.md#n01-r01-本轮完整契约决定)及[机器规范附表](../../../contracts/changes/N01-R01-contract-decisions.json)；逐项定义任务/文件在[类型审计](../TYPE_DEFINITION_OWNERSHIP.md)。新增选择明确为本轮设计决定，不伪称原条款。
- owner：A契约治理实施N01-R01；类型/行为由原manifest任务实施；独立N02负责冻结裁定。
- migration：数据契约1.0.0→2.0.0、计划1.0.2→1.0.3；最小恢复条件是本轮具体决定与验证被N02独立认可，然后才按授权归档历史并恢复真实冻结/G00。没有更新冻结reviewer/hash或Gate。详见[迁移说明](../../../contracts/changes/N01-R01-contract-freeze-2.0.0.md)。
