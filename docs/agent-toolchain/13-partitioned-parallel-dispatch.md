# 分区并发开发与验收 · 派发提示词

用户于 2026-10-04 授权：DSH、ZCode、Codex 按明确文件分区并发开发，开发与独立验收交错推进。本提示词补充原派发规则；具体任务范围、A/B 路径所有权、任务依赖与阶段 Gate 继续适用。它是执行指令，不是已派发或已通过记录。

## 可附加到后续开发任务的并发规则

工作根：`D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`。保留现有模型和工具配置。

1. 开工时由调度者按当前任务的依赖和允许文件，列出分区表：`task_id / partition_id / 实际 agent 与会话 / 实现或验收角色 / 精确可写文件 / 只读输入及 hash / 必需命令 / 输出目录 / 整合者`。明确分区后直接执行已授权工作，不为常规分区再次请求确认。没有合法并行分区的依赖步骤按顺序完成。
2. DSH、Codex-development、ZCode-development 均可编写分配给自己的实现和测试。一个文件同时只有一个写者；分区写集合必须无交集且包含于任务白名单。验收 agent 可并发编写自己分区的验证脚本和证据。每个 agent 只写其指定分区；范围外缺陷交对应写者修复。
3. 公共类型、接口、依赖清单和锁、生成器输出、路由入口等共享文件指定唯一整合者；确需修改时集中处理。接口就绪后再启动依赖它的分区。生成器或验收命令若会改写其他分区，在本轮隔离副本运行后由整合者接收产物。
4. 分区实现完成即停写，提交精确文件及依赖 hash、自己的贡献说明和实跑日志，交给未参与该分区实现的审查会话。其他无依赖、无写冲突的分区可继续开发。ZCode 和 Codex 可以同时核查固定输入；输入变化只重验受影响范围和项目要求的检查。
5. 同一会话不验收自己参与实现的候选。正式 Task precheck 由未参与该 Task 实现的独立 ZCode 会话完成；阶段签收由未参与被审阶段候选实现的独立 Codex 会话完成。开发贡献者的交叉审读属于辅助证据。记录实际工具及会话身份，Codex 子 agent 仍记为 Codex。
6. 常规 G01–G39 保留每任务一个 DSH 整合主写者：核对并采纳分区贡献，实跑整合验证，在自身交接中列出实际作者、路径及证据，再写自己的 `dsh/evidence.json`。Codex/ZCode 贡献者只写自己的贡献记录。这与现行执行器读取通道兼容。
7. 开发、必要测试及辅助审查可交错进行；正式阶段签收前停止该候选所有写者，核验完整候选和全部必需 precheck。Codex 主审补核最终 ZCode 记录后，按现行流程生成 review 并运行 Gate。每个官方 Gate 及公共记录只有一个写者。
8. 各分区使用独立的临时目录、日志文件、测试数据库/schema 和端口。原始失败证据保留。完成必要验证后交付，不为凑数量增加检查。

## 当前可直接派发：N02-R02 并发独立复核与 G00 恢复

执行 N02-R02。工作根：`D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`；保留现有模型。

待审候选：
`content-sha256:d1c94436a020158a0573d290443c7c6799711da6564b1609a294fb332d8b7f63`

你是未参与 N01-R02 实施的 Codex 主审。读取根规则、当前计划/manifest/Gate/OWNERSHIP、原 N02 流程、N01-R02 交接及 evidence、N02-R01 的 blocker。立即按下表并行开展独立复核；各接收者先核对同一候选。真实 ZCode 会话使用对应分区指令；没有 ZCode 接入时由明确标记身份的独立 Codex 辅审承担该分区，G00 不要求生成 ZCode precheck。

| 分区 / 接收者 | 工作 | 唯一可写输出，均相对工作根 |
| --- | --- | --- |
| C 契约 / ZCode 独立会话 | 审查 45 项 EntityKind、EntityRef 闭包、十类事件 kind/id/revision 映射及消费一致性，编写并实跑必要正反例 | `artifacts/handoffs/N02-R02/review-contract/**`、`tmp/N02-R02/review-contract/**` |
| V 检查器 / Codex 独立辅审 | 审查检查器与规范一致性、枚举或映射缺失的拒绝能力，实跑规划自测试和受影响设计检查；需生成文件的重放在隔离副本运行 | `artifacts/handoffs/N02-R02/review-validator/**`、`tmp/N02-R02/review-validator/**` |
| E 字节证据 / Codex 主审 | 独立复算候选、5 项差异、3786 项登记保护文件、日志及旧冻结/G00 输入，核验 P00 与既有已解决项的必要依赖证据 | `artifacts/handoffs/N02-R02/review-evidence/**`、`tmp/N02-R02/review-evidence/**` |

所有分区对被审候选只读。各自在专属目录写审查结论、实际命令/退出码、输入及日志 hash、缺陷和覆盖边界。已解决的 F01/F03/F04 及 Scenario 既有设计按本轮输入影响复核，不重做设计。发现实质缺陷时提交精确复现及最小修复范围。

主审收到 C/V/E 结果后完成一次汇总裁定和必要关键复现。唯一阻断项 N02-R01-F02-C01 解决且 G00 全部前置成立时，本轮已授权直接完成恢复：

1. 把旧冻结 JSON/MD、G00.json 和原始日志逐字节归档到 `artifacts/handoffs/N02-R02/archive/`，保存 hash。
2. 由主审单独更新 `docs/architecture/CONTRACT_FREEZE.json`、`docs/architecture/CONTRACT_FREEZE.md` 的真实审查身份、时间、计划 1.0.3、业务契约 2.0.0、当前哈希及迁移事实，保留历史记录。不要运行会覆写旧身份/版本的历史冻结生成器。
3. 实跑 `python tools/ai_coding_plan/validate_plan.py --self-test --record-g00`，保存实际退出码和原始日志；由该命令生成官方 G00。
4. 用现行 `scripts/gates.py` 的前置校验核验新 G00 的输入、日志与依赖证据。实际通过才报告 G00 有效、N03 可启动。

主审独占最终输出：`docs/handoffs/N02-R02/codex.md`、`artifacts/handoffs/N02-R02/codex/**`、上述归档目录、冻结记录，以及正式命令产生的 G00 和原始日志。其他 agent 不写这些路径。

本轮完成复核与 G00 恢复；N03/P02 仍按各自任务的前置单独派发。条件不满足则输出唯一汇总的具体缺陷与责任方。本轮不实施契约返工，不签 G01。交付实际证据后各分区停写。
