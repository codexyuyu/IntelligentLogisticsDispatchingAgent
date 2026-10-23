# N02 独立 Codex 审查：G00 阻断

结论：**BLOCKED；当前 G00 无效，禁止进入 DSH-A N03。** ARCH-0006/0007 的四项关键未决阻断本次契约冻结，不能仅作为后续派发限制。未执行 `--record-g00`，未修改冻结审查身份/日期/hash、官方 Gate 或他人交接；未签 G01，未启动 P02。

审查身份：`Codex N02 /root/n02_independent`；隔离方式为 `fork_turns=none`，未继承 N01 实施历史；继承当前模型，无模型覆盖。实际工作根为 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`；`.git` 不存在，`git rev-parse --show-toplevel` 实际退出 128。审查时间和完整绑定输入见[机器证据](../../../artifacts/handoffs/N02/codex/evidence.json)。独立只读子审计 `/root/n02_independent/freeze_semantics` 提供条款证据，本 N02 主审作最终决定；父 N01 实施上下文未代为裁定。

本次候选：`content-sha256:3525ed5b78851ea5d4fc7b5305b6b2e9f45bfedf7ee8742e3478ce6174e585a4`；规划 `1.0.2`，业务 Schema `1.0.0`。任务卡与派发文件中的 `1.0.0`、仅 issues 漂移为历史状态，`1.0.1` 为 N01 历史候选。

## 独立核验事实

| 核验项 | 本次实测 |
| --- | --- |
| 候选 | 75/75 文件 hash 一致；独立遍历集合一致；revision 与 dirty-tree 两种公式复算一致 |
| 治理差异 | 129 项差异与 `tmp/N01/before/` 原字节及当前字节一致；均在原 134 项白名单内；两轮 scope hash 一致 |
| 受保护证据 | 287/287 与 N01 修改前清单相符；N02 前后再次比较，冻结 JSON/MD、G00/G01、原始日志、执行器、OWNERSHIP、旧交接未变 |
| 冻结制品 | 12 项中 11 项相符；DATA_CONTRACTS 原 `1c77514c…`，现 `8091763a…`，冻结 hash 失效 |
| 旧资产 | BASELINE_INVENTORY 登记的 173/173 文件 hash 一致；普通资产未登记项为空 |
| 官方 G00 | JSON 的 `status=passed` 是历史字段；25 项输入中 23 项一致，DATA_CONTRACTS 与 issues/README 漂移；原始 G00 日志 hash 一致；依赖 hash 为合法空集合 |
| 原始日志 | N01 交接/候选清单/治理清单及声明的两条命令日志 hash 一致；已读取原始 render、15 项自测试及 36 项治理日志。它们是实施者历史自检，**不是本次独立验收** |

逐项结果见[审计汇总](../../../artifacts/handoffs/N02/codex/audit-summary.json)、[原字节治理差异](../../../artifacts/handoffs/N02/codex/governance-diff.txt)、[冻结核验](../../../artifacts/handoffs/N02/codex/freeze-audit.json)、[旧资产核验](../../../artifacts/handoffs/N02/codex/baseline-audit.json)。

## G00 冻结判定依据

以下属于基于现行条款的独立审查判断；输入 hash 漂移和命令退出码属于实测事实。

- [P00-02:67](../../prompts/00-master/P00-02-freeze-contracts.md) 范围是“全部领域实体、Schema、Protocol”；第 99 行要求冻结 DATA_CONTRACTS 等源，第 105 行明确“存在阻断矛盾先记录 issue 并阻止 Gate”。
- [PHASE_GATES:21](../../plan/PHASE_GATES.md) 要求 G00 的单位/32 实体/错误/Protocol 冻结及 DAG/追踪无缺口；[Gate 契约:19](../../plan/GATE_EXECUTION_CONTRACT.md) F7 要求附加断言逐条成立。
- [IMPLEMENTATION_CONVENTIONS:13](../../architecture/IMPLEMENTATION_CONVENTIONS.md) 要求 P02 先定义实体直接引用的纯值类型，使 Schema 能立即导出；[DATA_CONTRACTS:79](../../architecture/DATA_CONTRACTS.md) 禁止用 Any、空类、TODO 替代完整类型。
- ARCH-0006/0007、N01 迁移说明把未决项定位于相关任务派发前；但 ARCH-0007 和 issue 索引明确保留 N02 对冻结/G00 的判断。没有现行 P00/G00 范围豁免。冻结记录第 138 行对旧 ARCH-0003 的非阻断理由是“不影响实体/单位/状态枚举/求解语义”，不能扩用于以下四项。

## 具体缺陷与最小恢复条件

责任方均为 **A 契约治理**；N02 不实施修复。

| 缺陷 | 当前事实与来源 | 最小恢复条件 |
| --- | --- | --- |
| N02-F01：JobKind 成员/判别映射未冻结 | [类型审计:47](../../architecture/TYPE_DEFINITION_OWNERSHIP.md) 明确成员及请求 kind 映射未决。JobKind/JobStatus 的唯一定义任务已修正为 P02-01 `packages/domain/src/logistics_domain/states.py`，P02-04/P05 只引用；归属正确不等于成员已冻结 | 决定完整成员、命名、请求 kind 映射及正反例；保留 states 唯一定义，更新相关契约/源生成规划后独立复核 |
| N02-F02：ScenarioRef/Bundle 的形状未冻结 | [ARCH-0006:31](../../architecture/issues/ARCH-0006-scenario-bundle-ownership.md) 明确成员、ID/version/hash、期望与正式输入隔离结构未决；[DATA_CONTRACTS:96](../../architecture/DATA_CONTRACTS.md) 的冻结 ScenarioEngine Protocol 已使用它们。唯一承载 P02-04 runtime 已裁定 | 决定完整字段、嵌套类型、引用/版本/hash 语义和隔离不变量，给出可验证正反例；消费者只复用唯一类型 |
| N02-F03：ResourceCalendar 唯一定义任务/模块未闭合 | [DATA_CONTRACTS:7](../../architecture/DATA_CONTRACTS.md) **已给** intervals/version；[类型审计:104](../../architecture/TYPE_DEFINITION_OWNERSHIP.md) 未明示定义任务/承载；DOMAIN_CATALOG 的 Vehicle、Warehouse、StorageLocation、Dock、Worker、Equipment 已直接引用它 | 裁定最早唯一定义任务、合法纯值模块及 CalendarInterval 依赖，确保 P02-02 引用前成立；同步 catalog/白名单/依赖及 CalendarDTO 映射，不在 HTTP 自造公共类型 |
| N02-F04：JobRequest 完整 union 的前向依赖未解决 | [DATA_CONTRACTS:57](../../architecture/DATA_CONTRACTS.md) 给五类 payload 且要求 P05-03 定义；[类型审计:49](../../architecture/TYPE_DEFINITION_OWNERSHIP.md) 保留 P06/P11/P14/P32 请求未定义问题。P05-03 当前只依赖 G04/P05-02，无法确认该 union 在该阶段可满足 | 决定完整早期纯类型或具名引用策略，明确判别分支、版本/解析语义、可满足的定义与消费依赖及正反例；禁止未来导入、Any、空类占位 |

ARCH-0007 还登记 ActorContext、Resource/ResourceDTO 关系及若干 HTTP/内部命令字段未决；本次没有替 A 选择字段。新治理任务应按冻结范围一并裁定相关公共契约缺口，不能只修一项或只更新 hash 后沿用“无阻断”。

已成立的有限治理结果：workflow 的 G00 引导例外与 G01–G39 常规流程、实际读取字段/缺口披露一致；JobKind/JobStatus 唯一定义位置已修正；P36-02 的 9 项贡献路径与实际 A/B 所有权一致、集合无交集且并集覆盖完整白名单，B solver 测试纳入必需命令。P36 实际贡献和性能验收未运行，未授权 A 编辑 B 源码。

## 实际命令与停止状态

| 实际命令 | 退出码 | 原始日志/范围 |
| --- | --- | --- |
| `python tmp/N02/audit.py`（由 capture_audit 捕获） | 0 | [audit.log](../../../artifacts/handoffs/N02/codex/audit.log)；独立字节/输入/证据审计完成，退出 0 不代表 Gate 通过 |
| `python tmp/N02/probe_g00.py`（由 capture_probe 捕获） | 1 | [g00-prerequisite.log](../../../artifacts/handoffs/N02/codex/g00-prerequisite.log)；实际调用现行 runner 的 `check_previous_gates()`，仅检查 G00，两个输入漂移被拒绝 |

命令的精确 argv/cwd/UTC 时间/hash 分别见 [audit-command](../../../artifacts/handoffs/N02/codex/audit-command.json) 与 [probe-command](../../../artifacts/handoffs/N02/codex/probe-command.json)。未执行 G01 验收。

限制：首次字节审计的额外派生目录遍历已中止（exit 1）；修正为只审计必需登记资产后实际完成。node_modules/.venv 的全部派生文件计数/树指纹为 NOT_RUN；冻结记录第 137 行明确冻结结论不依赖其逐文件 hash。未运行本次规划自测试或 `--record-g00`，因为冻结独立复核已阻断；未运行数据库/求解器/仿真/模型/浏览器业务测试。未修改任何模型、插件或全局配置。

下一责任方：调度者生成 A 契约治理的限定修复卡；形成具体契约决定与新候选后重新交独立 N02。只有独立复核成立，才可按原 N02 授权先逐字节归档旧冻结/G00/原始日志，更新真实审查身份/时间和核验 hash，实际执行规划检查器并复核新官方记录。当前不作这一步，**N03 仍阻断**；P01 旧证据需未来按新输入重新验收，G01–G39 均无通行授权。
