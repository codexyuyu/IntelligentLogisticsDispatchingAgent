# Architecture Contract 冻结记录 · 2.0.0

结论：N02-R02 独立复核接受 N01-R02 治理候选，唯一残余 N02-R01-F02-C01 已解决；本记录冻结文档契约。官方 G00 由真实规划命令生成并经现行前置验证后才有效；本记录自身不签收 G01 或业务能力。

| 字段 | 当前事实 |
| --- | --- |
| 记录 schema_version | 1.0.0 |
| plan_version | 1.0.3，取自当前 TASK_MANIFEST |
| frozen_contract_version | 2.0.0 |
| legacy_contract_version | 0.1.0，只读迁移输入 |
| reviewer | Codex N02-R02 /root/n02_r02_independent (independent reviewer; not N01 implementer) |
| reviewed_at | 2026-10-04T14:48:49.292386+00:00，实际 UTC |
| reviewed_candidate | `content-sha256:d1c94436a020158a0573d290443c7c6799711da6564b1609a294fb332d8b7f63` |
| reviewed_dirty_tree_hash | `content-sha256:1f46a24cc017ed209fc3c049239de9be1cea7053992e4d49469af98c6addeed0` |
| unresolved_blocking_issues | [] |

实际根为 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，无 Git。主审是本轮全新独立代理，未参与 N01-R02 实施，沿用继承模型且未覆盖模型；只读辅助审查与本轮追加探针不代替主审裁定。[本轮裁定及输入绑定](../../artifacts/handoffs/N02-R02/codex/review-decision.json)记录证据。

## 冻结范围与哈希

[机器冻结记录](CONTRACT_FREEZE.json)记录逐项实际 SHA-256；核心12项为 Master、TaskGraph、架构总览、Domain、Data、内部规范、API、三算法契约、测试Fixture和PhaseGate。另冻结3项直接规范附表：`contracts/changes/N01-R01-contract-decisions.json`、其2.0.0迁移说明及 `TYPE_DEFINITION_OWNERSHIP.md`。共15项，均从当前字节计算，不冻结日志、报告或冻结文件自身。

`code_revision`与`reviewed_candidate`绑定恢复前已独立复算的77项审查候选。现行runner的候选集合包含本JSON/MD；恢复修改会生成新的当前候选，完成后在本轮交接重新复算。当前候选不得写入自身冻结内容再声称哈希不变。规划器G00另以排序输入hash-map JSON计算revision；它与runner的path/NUL/hash组合值使用不同公式，不能混称。

## 已接受的决定

| 决定 | 冻结内容与实施责任 |
| --- | --- |
| 单位与实体 | 保留整数秒/米/克/cm³/分/decic、UTC、闭窗与半开占用；32实体及11既有辅助实体、共同字段/状态/生命周期由 DOMAIN_CATALOG 唯一定义 |
| EntityKind / EntityRef | 45个精确成员/值：32实体+11辅助实体+TravelMatrix/RegionRef。kind/id/可空非负revision显式闭合；唯一P02-01 states/primitives，primitives单向依赖states，不导入未来业务目标类型 |
| 十事件引用 | vehicle、transport_task、cargo、order、equipment按真实事实对象ID/给定row_version绑定；交通单矩阵多有向弧并必填旧version；天气显式节点区域、相同region ID保持集合、revision必须null；仓储限定warehouse/zone/location/dock/worker/equipment且两个引用全值相等 |
| JobKind | 五kind与family绑定，optimization另含transport/warehouse/joint；非优化禁止mode，保留N02-F01决定 |
| Scenario | Ref/Spec/Input/Bundle具名字段、版本/hash、事件payload闭包、独立期望旁文件隔离；唯一P02-04，保留N02-F02已解决部分 |
| Calendar | CalendarInterval/ResourceCalendar唯一P02-01，P02-02/DTO复用，源日历/hash与窗口投影可复算；不向zone添加calendar，保留N02-F03决定 |
| JobRequest | 早期JobCommand/引用闭包，无未来DTO；scope/hash/version和404/409/422/501顺序、未实现能力不入队、typed终态/lease保持N02-F04决定 |
| 分层、错误与提交 | domain不依赖框架，bootstrap唯一组合根；错误/Protocol以当前DATA/API为准，未知能力INVALID_INPUT/422+UnsupportedDetail、开发未实现501；只有ScheduleService提交，历史版本追加、不覆盖 |

45成员、十事件完整表与ID/revision细则以 [DATA_CONTRACTS](DATA_CONTRACTS.md)、[规范附表](../../contracts/changes/N01-R01-contract-decisions.json)与[唯一归属](TYPE_DEFINITION_OWNERSHIP.md)为准。本记录不建立第二套类型。

## 原字节与迁移事实

旧1.0.0冻结JSON/MD、旧官方G00和全部将被替换的原日志已在任何修改前逐字节归档；[归档清单及原hash](../../artifacts/handoffs/N02-R02/codex/archive-manifest.json)覆盖4项。旧身份、旧UTC、旧版本、旧观察保存在原字节及新JSON的history，不把历史“无执行器/无应用测试”当当前事实。

N01-R01为规划1.0.3/业务2.0.0的破坏契约决定，N01-R02补齐未接受候选的枚举与直接嵌套引用闭包；不声称已发布2.0.0兼容。旧输入必须有可信显式转换、保留原bytes/hash/版本与转换记录；无法确认kind/目标/ID/revision则拒绝。未来实施顺序为domain→DTO→ports→消费者→测试→生成Schema/OpenAPI/TS；真实模型与生成物仍由原任务交付，本轮不补造。

已解决的F01/F03/F04与Scenario既有字段未重做；本轮核验必要输入影响、类型内容与任务依赖。issues/README的“待N02”属于实施历史，本次接受事实由本记录和独立裁定保存，不修改他人登记或交接。

## 验证边界与后续

本轮独立重算77候选、5差异、3786保护、旧demo173项与必要原日志/输入；规划73自测试和隔离268设计检查实际通过，并运行独立追加引用探针。具体argv/cwd/UTC/退出码和原始日志由本轮机器证据保存。

本轮只恢复G00。新冻结及新G00使相关旧Phase01交接/precheck/审查输入失效；G00有效后才可由DSH执行N03刷新自身交接，随后N04/N05重验/签G01。未签G01、未启动N03/P02。

设计示例的CalendarDTO重叠、完整Scenario FK/日历绑定、OnArc时序、CargoType覆盖限制仍保留；静态检查器并非全部payload行为检查。DB、真实domain/handler/worker、OR-Tools、SimPy、模型及浏览器验收均未运行，不以设计检查或历史226测试代替业务验收。ARCH-0001仍为原非阻断观察，精确阶段屏障继续执行。
