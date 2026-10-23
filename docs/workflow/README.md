# 任务交接与阶段签收

契约版本1.0.0；2026-10-03 N01补齐ARCH-0004。本文描述流程，不是预验收或Gate通过记录。当前根为`D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，无Git；保留既有模型。

依据：[实际执行器](../../scripts/gates.py)、[冻结Gate规则](../plan/GATE_EXECUTION_CONTRACT.md)、[阶段断言](../plan/PHASE_GATES.md)、[当前派发顺序](../agent-toolchain/12-project-completion-dispatch.md)。格式详见[交接契约](HANDOFF_CONTRACT.md)，ZCode执行步骤见[独立预验收](02-ZCODE-PRECHECK.md)。

| 角色 | 产物及责任 | 边界 |
| --- | --- | --- |
| DSH主实现者 | 自己的实现、任务文档、完成报告、`dsh/evidence.json` | 只在任务白名单及A/B路径权限内写；不写ZCode/Codex记录，不签官方Gate |
| B贡献者 | B文件及带候选/日志/hash的贡献清单交A整合 | 贡献清单不是执行器消费的DSH/ZCode记录；A不能因整合责任获得B源码写权限 |
| ZCode独立预验收 | 每Task的`zcode/precheck.json`及原始日志 | 冻结候选上核验与复跑；不改实现，不冒写DSH状态 |
| Codex治理/实现 | 治理差异及自己的交接 | 修改候选后交新的独立上下文，不自称完成独立审查 |
| Codex独立阶段审查 | `GNN-codex-review.json`，成立后按正式流程运行Gate | 覆盖当前候选、所有Task预验收、全部前序Gate及附加断言；无真实证据不签 |

G00使用独立引导流程：N02复核冻结记录、基线、问题登记及P00证据后，按派发规则调用规划检查器；签收身份来自CONTRACT_FREEZE。该检查器不读取P00 ZCode precheck或G00-codex-review，不应为适配常规流程制造这些记录。本N01不执行该引导签收。

G01–G39的固定顺序：

1. 治理决定、白名单、环境必要条件先成立；核验前序Gate及真实依赖。不从manifest的`planned/not_run`推断进度。
2. 完成实现及必要Schema生成、测试，停止候选文件写入；复算相关文件清单及revision。先冻结业务候选，再生成实现交接。
3. DSH先保存原始日志，再完成报告/任务说明，最后写自己的evidence哈希；若evidence索引handoff，先落handoff再哈希，不互相引用形成环。
4. ZCode读取冻结候选及DSH交付，独立复跑、核验输入和日志；先保存日志/报告，再写precheck。失败只写自己的失败记录、缺陷和恢复条件，退回对应责任方。
5. 本阶段全部precheck有效后，独立Codex审查当前候选，先保存审查日志再写review；review不绑定尚未生成的本Gate证据，避免循环。
6. 独立签收者先逐字节归档旧官方JSON和原始日志，再运行正式Gate，核验输出与日志、依赖哈希；任何失败保留原始证据，禁止启动下阶段。

候选、输入、日志三类哈希分别保存。workflow/prompts/报告/日志不进入执行器候选清单，但审查记录必须显式绑定所消费的文档与证据。流程文档改动不能因revision不变就沿用旧结论。

开发探针仅写`tmp/<task>/<round>/...`并使用`--out-dir`；其`official_gate_record=false`不是签收。`--check-only`不运行命令、不写记录；无记录时当前执行器也可能退出0，不能据此启动下阶段。官方记录必须实际存在且规则、输入、日志和依赖均有效。

候选或公共契约变化后，由原角色在新输入上重验受影响任务与全部下游Gate；禁止只换日期/hash恢复旧通过。执行器只注册G01附加断言，G02–G39必须在对应签收前完成断言/证据覆盖治理，不得把空注册视为通过。

本轮下一执行者是独立Codex N02。P01-02保持READY_FOR_ZCODE；先完成G00复核，再N03刷新DSH自身交接、N04三任务ZCode重验、N05独立G01审查。本轮不执行`--record-g00`、不重启旧返工、不启动P02。
