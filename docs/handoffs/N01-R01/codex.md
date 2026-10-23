# N01-R01 A契约治理返工 → 独立N02

结论：**READY_FOR_INDEPENDENT_REVIEW（待独立复核）**。N02-F01–F04已形成具体本轮设计决定及正反例；本实施者不裁定G00恢复。所有新增选择明确为本轮决定，非原1.0.0已有事实。治理返工N01-R01未新增业务manifest节点。

实际根：`D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`；无`.git`，使用内容hash；保留当前模型，无模型/供应商/插件/全局配置变动。输入规划1.0.2，候选`content-sha256:3525ed5b78851ea5d4fc7b5305b6b2e9f45bfedf7ee8742e3478ce6174e585a4`；当前计划**1.0.3**，数据/领域/HTTP/内部契约**2.0.0**，Gate证据格式仍1.0.0。

当前待审候选：`content-sha256:adbd8a1ccfa59e8b803acfbb8beb6e23d8fbdad28a51ededbb5862ee0c79ee98`；dirty-tree：`content-sha256:9a48d7b5308b7dce70dee3cf978ad463b0c5ca57774dae2de1acd5eaf4539d68`。77项相关文件按现行runner规则及独立公式复算一致。报告/日志/审查/tmp不进入候选；依赖证据单独绑定。[候选清单](../../../artifacts/handoffs/N01-R01/codex/candidate-files.json)、[机器证据](../../../artifacts/handoffs/N01-R01/codex/evidence.json)。

## 四项缺陷逐项响应

| N02缺陷 | 本轮具体决定 | 唯一定义/消费与迁移 |
| --- | --- | --- |
| F01 | JobKind五成员及小写值optimization/simulation/reschedule/experiment/metric；优化二级mode transport/warehouse/joint；kind/payload.family/ref.family精确一致，非优化禁止mode；JobStatus既有语义保留 | P02-01 states唯一定义；P02-04/P05引用；unknown/错branch/错mode正反例 |
| F02 | ScenarioRef完整ID/dataset/schema/hash；Spec及Size/EventPayload等嵌套数据、Input/Bundle完整；events唯一Spec，期望独立typed旁文件，正式类型可达图不含预制方案/期望 | P02-04 execution→runtime单向、runtime及DTO唯一；P04/P12/P16复用；canonical hash、绑定/数量/版本/隔离正反例 |
| F03 | CalendarInterval/ResourceCalendar完整epoch/version/intervals；源Calendar/hash/窗口投影可复算，Resource/DTO五分支，CalendarDTO只映射并明确HTTP版本 | P02-01 primitives最早定义，P02-02 entities映射，P03 capture；接续/重叠/容量/跨epoch/源hash正反例 |
| F04 | 完整早期JobCommand及五类非空具名引用payload，immutable RequestRef/Metadata/ResultRef，不导入未来DTO；注册/strict解析/版本/hash/scope/真实能力可用性及失败顺序 | P02-04纯命令与JobRequest映射；P05行为，未来能力自己的parser/handler消费同一命令；缺引用404/旧版本409/hash422/未启用501、不入队；Job生命周期/旧lease反例 |

完整字段及失败语义见[DATA本轮决定](../../architecture/DATA_CONTRACTS.md#n01-r01-本轮完整契约决定)、[规范JSON附表](../../../contracts/changes/N01-R01-contract-decisions.json)、[合法承载审计](../../architecture/TYPE_DEFINITION_OWNERSHIP.md)。ActorContext认证actor/role/scope、Resource/ResourceDTO同构、JobFailure纯domain不导入Envelope、CLI ImportReceipt、Settings/health/ready与主数据具名投影同步闭合。MasterData不是新增实体。原Zone没有calendar，本轮calendar端点限location/dock/worker/equipment，zone明确422 UnsupportedDetail；区域事件RegionRef明确节点集合，禁止猜区域成员。

## 差异与保护

- 开工前保存127个精确路径（实际生成器114输出），改前hash/原字节/影响与迁移：[scope-before](../../../artifacts/handoffs/N01-R01/codex/scope-before.json)；原字节在`tmp/N01-R01/before/`。
- 实际治理变动123项：[前后hash清单](../../../artifacts/handoffs/N01-R01/codex/governance-files.json)、[原字节差异](../../../artifacts/handoffs/N01-R01/codex/governance-diff.patch)。catalog/render/validate修改后重生成109 prompts及manifest；114输出精确复现，所有Task仍planned，40 Gate仍not_run，节点ID不变。P16-01精确补contracts.runtime结果映射路径，不授权业务实施。
- 3418个登记受保护文件原字节未变，含业务源码、锁、OWNERSHIP、AGENTS、执行器、冻结、官方Gate、N01/N02及其他旧交接/日志、登记旧资产；[保护比较](../../../artifacts/handoffs/N01-R01/codex/protected-comparison.json)。遍历排除依赖/缓存/.mimosa和本轮自身输出；不以此宣称这些派生目录已完整审计。
- 执行器未改，规划checker仅新增设计类型/任务/模块/映射负例校验，原15自测试保留；record_g00函数AST与改前一致，未降低冻结/Gate判定。规划与契约版本及破坏迁移见[changes](../../../contracts/changes/N01-R01-contract-freeze-2.0.0.md)。

## 实跑验证与原始日志

| 实际命令 | 退出码 / 结果 | 原始日志 |
| --- | --- | --- |
| python tools/ai_coding_plan/render_plan.py | 0；109 prompts/40 Gate；最终源重生成 | [render-02](../../../artifacts/handoffs/N01-R01/codex/render-02.log) |
| python tools/ai_coding_plan/validate_plan.py --self-test | 0；43测试，109任务/40Gate，errors=[] | [plan-check-final](../../../artifacts/handoffs/N01-R01/codex/plan-check-final-03.log) |
| python tmp/N01-R01/verify_contracts.py final03 | 0；95/95设计/治理检查 | [contract-check-final](../../../artifacts/handoffs/N01-R01/codex/contract-check-final-03.log) |
| python tmp/N01-R01/probe_g00.py | 1；现行runner只读G00前置校验拒绝5个漂移输入；未运行G01 | [g00-prerequisite](../../../artifacts/handoffs/N01-R01/codex/g00-prerequisite.log) |

命令精确argv/cwd/UTC/exit/log哈希在同目录*-command.json。合法示例、单点违规、检查范围在[contract-examples-final](../../../artifacts/handoffs/N01-R01/codex/contract-examples-final03.json)、[逐项结果](../../../artifacts/handoffs/N01-R01/codex/contract-validation-final03.json)。校验覆盖类型唯一定义/具名引用闭包、合法任务/文件与祖先依赖、模块无环/domain层边界、五类/三mode、引用版本/hash及真实能力缺失拒绝的文档协议、场景hash/期望隔离、资源calendar源hash/投影/容量、Job终态与lease、精确HTTP投影、规划初态、字节复现、本地链接与保护hash。

保留失败过程：contract-check首次exit1（字段提取漏数字，同时发现投影拼写问题）；第二次exit1（Dock/Worker/Equipment Update的allowed_zone_ids被错误替换），均已修正而非降低断言，旧raw log/机器结果保持。第三/四/最终轮分别80/92/95检查exit0。交接一致性检查还检出RegionRef审计字段漏列node_ids，已同步修正并按最终文件重新实跑规划及契约检查；初始41、后续42、最终43规划自测均保留日志；新增检查/设计修改后按新输入重验，不把旧轮成功转移到新候选。子任务首次探针误假设102任务，仅作为工具输出历史，后以实际109核验；最终证据只采用上述捕获日志。一次候选查询使用了不存在的方法，未用于最终结论，最终按实际compute_revision及独立公式复算。

## Gate影响、未执行与交接

冻结12项有4项漂移：DOMAIN_CATALOG、DATA_CONTRACTS、IMPLEMENTATION_CONVENTIONS、API_CONTRACT；官方G00的25项输入有上述4项及issues/README共5项漂移。[精确影响](../../../artifacts/handoffs/N01-R01/codex/freeze-impact.json)。历史status=passed不等于当前有效；当前G00无效，G01及下游不能通行。没有更新reviewer/日期/hash，没有record-g00，没有签Gate或修改他人交接。

设计决定待N02独立认可，**不宣称业务类型已实现或完整业务Schema已导出**。existing记录继承具名原契约或本轮显式投影，设计引用图验证不能替代所有继承模型的真实Schema/状态机/FK/授权/解析器验收；G02及各能力Gate仍必须实跑。引用解析例子仅验证文档元数据与拒绝谓词，未运行真实handler/worker；空场景是严格边界正例，不代表物流业务成功。未运行数据库/OR-Tools/SimPy/模型/浏览器smoke，未核验外部凭据/服务，不造环境卡，不把226旧passed作为本轮回归。Schema/OpenAPI/TS须由原授权业务任务按domain→DTO→ports→消费者→测试→导出顺序生成，旧1.0.0不能只改版本号。

下一执行者：与实施上下文分离的独立Codex N02，先独立复算本候选、差异、保护文件及原始日志，再按G00冻结条款审查这四项决定与其闭包。只有N02认可并执行真实恢复流程，G00有效后才可N03；本轮没有启动N03/P02，没有重启P01-02旧返工。P01旧交接/precheck需未来按新计划/候选输入重验，不能只换hash保留旧结论。

本交接保存后N01-R01停写；状态仅待独立复核，不是Gate通过或完整系统交付。
