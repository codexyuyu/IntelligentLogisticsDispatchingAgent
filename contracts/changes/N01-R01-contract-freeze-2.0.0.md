# N01-R01 契约冻结缺口迁移 · 待独立复核

这是 A 契约治理的本轮设计决定，不是原 1.0.0 契约已有事实，不是实现或 Gate 签收。治理返工标识 N01-R01 不加入业务 manifest。

输入：计划 1.0.2；候选 `content-sha256:3525ed5b78851ea5d4fc7b5305b6b2e9f45bfedf7ee8742e3478ce6174e585a4`。精确修改白名单、改前 sha256、生成器实际 114 个输出及受保护文件见 [scope-before](../../artifacts/handoffs/N01-R01/codex/scope-before.json)。改前原字节保存在 `tmp/N01-R01/before/`；N01/N02 原交接和原日志不可改。

版本决定：规划 1.0.2 → 1.0.3；数据/领域/HTTP/内部契约 1.0.0 → 2.0.0。新增必需字段、枚举序列化值、hash 和引用语义不能预设兼容；Gate 证据 schema 仍 1.0.0，执行器、冻结记录、OWNERSHIP 与依赖锁不变。旧业务 schema_version=1.0.0 不自动视作 2.0.0；未来迁移必须显式转换并保留原版本、原输入 hash 和转换记录；无转换规则拒绝，禁止补默认猜值。

范围：N02-F01–F04、其直接嵌套引用及 ActorContext、Resource/ResourceDTO、早期 HTTP/CLI 具名边界闭包。规范决定表保存于本目录 `N01-R01-contract-decisions.json`；它是本轮文档契约的可校验附表，尚不是生成的业务 JSON Schema 或业务实现。公共类型实施后仍由 domain 源码唯一定义，DTO 映射，导出工具生成 Schema/OpenAPI/TS。

具体破坏点：五类JobKind及优化二级mode精确序列化；ScenarioRef与完整场景hash/输入/独立期望旁文件；ResourceCalendar必需epoch以及可复算源日历/投影绑定；JobCommand与不可变版本化引用取代未闭合的未来payload导入；Actor scope、Resource五分支包装和主数据具名投影。原Zone没有calendar字段，通用calendar端点限location/dock/worker/equipment，zone请求明确422 UnsupportedDetail，不推断仓库日历。日历DTO只映射公共字段并加根HTTP schema_version；上述选择均为本轮设计决定。

受影响 Gate：G00 冻结输入和规划 DAG；G01 计划/候选输入；G02 类型/Schema；G03 持久化；G04 场景/导入；G05 HTTP/Job；相关后续消费者 G06/G08/G11/G12/G14/G16/G17/G23/G32/G33，及其所有后继 G00–G39 的有效性均须重审。新候选不复用旧通过结论；已有 P01 交接/precheck 输入失效，不在本轮重写。

迁移顺序：先契约决定与规划源 → 重生成全部实际规划输出 → 本轮规划/契约正反例与字节复现 → 停写交独立 N02。N02 判定成立后才按其授权恢复冻结/G00；G00 有效后 N03–N05 刷新与重验 Phase01；G01 有效后按原 P02 任务实施 domain → DTO → ports → 消费者 → 测试 → Schema/OpenAPI/TS。本轮禁止业务源码、依赖锁、执行器和业务导出物写入，没有补造尚未实现的 Schema，也没有执行数据库/模型 smoke。

详细决定、例子、验证结果在最终交接中绑定原始日志；实施者状态只为待独立复核。


## N01-R02 唯一阻断修复追加 · 待独立复核

依据独立N02-R01的N02-R01-F02-C01，本轮只修改授权的DATA_CONTRACTS、TYPE_DEFINITION_OWNERSHIP、本规范JSON、本迁移说明、validate_plan.py；原字节及保护清单在tmp/N01-R02与artifacts/handoffs/N01-R02/codex。旧N01/N02交接与日志不覆盖，不修改冻结JSON/MD、官方G00/G01、业务源码、锁、OWNERSHIP、manifest或生成Prompt。

新决定：EntityKind为45项封闭集合（目录32实体+11既有辅助实体+TravelMatrix/RegionRef纯值目标）；EntityRef完整kind/id/可空非负revision，保留P02-01唯一承载。zone/location沿用既有边界标签；其余成员/精确值及全部十类事件的合法目标/ID/revision绑定由DATA与本附表明确。交通多弧绑定一个旧矩阵ID/version；天气region绑定已有RegionRef节点分组；仓储ref完整一致、限仓库及五资源。没有新增实体、payload字段或未来DTO依赖。

版本仍计划1.0.3、业务2.0.0、证据格式1.0.0：当前2.0.0候选未获冻结/G00签收，这是完成先前未决定义，不是假定已发布2.0.0的兼容修补。旧11字符串仅示例实现，不能作为已有枚举规范迁移来源；旧1.0.0仍遵循原破坏迁移规则。不确定目标/枚举/ID/修订的旧事件不得猜值转换，必须有可信事实映射并保留原bytes/hash/版本与转换记录，无映射拒绝。尤其旧脚本没有driver、matrix、region等成员，不能直接复用作完整事件验收。

新候选使受影响旧审查/规划/契约证据失效：G00冻结输入以及G01相关候选，随后G02公共类型、G04场景引用、G11/G13/G14事件消费、G17/G19/G23/G31引用与审计，以及所有受依赖传播影响的后继。新增设计测试以新输入实跑；本轮不复用N02-R01/N01-R01通过日志为新验收。沿用既有“domain→DTO→ports→消费者→测试→生成物”实施顺序，未实现部分仍由原阶段验收。

本实施者只提交N01-R02待独立复核交接；不record-g00、不更新旧冻结身份/hash、不签官方Gate、不启动N03/P02。下一执行者为独立Codex N02-R02，先复算新候选/五项差异/保护文件/日志并复核这个唯一修复，成立后再执行原授权的真实G00恢复流程。
