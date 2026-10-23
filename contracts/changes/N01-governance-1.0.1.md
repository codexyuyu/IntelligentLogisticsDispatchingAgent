# N01最小治理修正：规划1.0.0→1.0.2

2026-10-03，实施者Codex N01；下一独立复核者Codex N02。本文件是迁移说明，不是冻结审查或Gate通过记录。

变更前精确白名单与现场hash已保存为`tmp/N01/scope-before.json`，共134条精确路径（含109个prompt及N01产物）。治理交接中的`governance-files.json`保存实际差异。执行器、OWNERSHIP、依赖锁、业务源码、历史交接及官方Gate记录不在修改范围；已解决的AGENTS.md归属不再返工。

| 缺口 | 最小修正 | 版本与迁移 |
| --- | --- | --- |
| ARCH-0004 | 三份workflow文档严格对应实际读取字段/路径与冻结F1–F9，显式列未自动检查的规范要求 | 新流程文档1.0.0；不放宽执行器，不改旧审查记录 |
| ARCH-0003 | renderer改为请求未知必需能力INVALID_INPUT/422+UnsupportedDetail；校验unsupported_codes保持拒绝有效候选；开发未实现仍501/不得进Gate | 不新增ErrorCode，不改变业务Schema1.0.0；109项prompt从源重生成 |
| ARCH-0005 | catalog补齐P01-02缺review、check-only不签收两个案例；checker增加用例表与manifest精确比对及正反例 | 计划1.0.2，planned/not_run保留初始值，不迁移实时状态 |
| ARCH-0006/0007 | 早期纯值定义归属明确；Settings/CLI/HTTP/Job分别合法承载；补P05边界映射白名单；具体字段证据不足保留派发前阻断 | DATA_CONTRACTS归属段修正，业务Schema版本不变；定义/DTO/ports/调用方/测试/生成物尚未实施，不生成空Schema冒充迁移 |
| ARCH-0008 | P36-02 A基准/回归/整合，B矩阵源码与solver缓存验证，贡献清单覆盖全白名单 | OWNERSHIP路径不变；任务owner不覆盖路径，A整合不授权编辑B源码 |

受影响证据：

- G00当前已因issue登记漂移无效；本次又修改冻结的DATA_CONTRACTS。N02必须独立核验12项冻结制品、173项旧资产以及本次决定；先归档原冻结记录/G00/原始日志，再记录本次真实reviewer/时间与核验hash。未决类型缺口作为后续任务派发阻断，不把全系统类型契约声称已完备。
- manifest变化及109个prompt的规则/版本变化使P01-01/02/03的旧输入绑定失效；候选也变化。N03 DSH只刷新自身交接，N04 ZCode三任务重验，N05独立Codex审查G01。禁止只补旧hash恢复通过。
- G02及下游须先解除对应具名类型未决；G36涉及P36-02分工及真实缓存/回归验收。G02–G39还缺执行器附加断言覆盖；本轮未修执行器、未签后续Gate。

业务迁移顺序保留domain→DTO→ports→调用方→测试→生成物；本轮只有规划/归属修正，未来字段决定如改变Schema语义须另行版本裁定及真实生成/验收。旧CONTRACT_FREEZE的hash/reviewer/日期保留原字节，故本轮结束其DATA_CONTRACTS条目预期不再新鲜，这不是新签收。

环境：本轮不需要数据库、求解器或模型；未核实这些服务的运行条件，未创建环境任务卡、未运行其smoke、未改现有模型或全局配置。

## 1.0.1→1.0.2复核修正

修改前精确130项白名单、前后版本与Gate/迁移影响保存在`tmp/N01/recheck-20261003/scope-correction-before.json`，全部落于原134项白名单；上次N01文档/证据/日志字节副本在该目录的before树。修正JobKind/JobStatus与P02-01 states的唯一枚举定义冲突，JobKind未决必须在P02-01派发前裁定；补Resource及主数据各具名类型/简称未决审计；G00独立引导流程与G01–G39常规流程区分。catalog改动后重生成1.0.2，执行器、OWNERSHIP、官方记录、业务Schema均不改。
