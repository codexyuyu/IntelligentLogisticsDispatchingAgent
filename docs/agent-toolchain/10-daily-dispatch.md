# 给 Codex：每次开工生成一个真正可执行的任务

请根据当前磁盘事实继续推进项目。先读同目录 `00-common.md`、当前任务清单、Gate、所有权与最新交接。不要重新规划整个 40 阶段，也不要把“最新编号”当作“下一可执行任务”。

2026-10-01 默认入口为 [返工后至完成的派发清单](12-project-completion-dispatch.md)：P01-02 四项返工已交付，不再默认派发同一返工。先处理交接治理与 G00 漂移，刷新 Phase 01 自身交接，重做三项独立预验收及 G01 review。不要把旧 `BARRIER_REMEDIATION_G01_G02_G03.md` 的“只补四份 JSON”当作现行方案；G01 有效签收后才下发 P02-01。

1. 找到最早失败、缺失或失效的前置节点。核验阻塞根因是否已变化；如果没有，就围绕该根因创建一个修复任务，停止向下游分发同类必败工作。
   任务完成、独立预验收通过、阶段签收是不同条件；不得让 DSH 生成其他角色的签收文件来使调度继续。
2. 确定本次目标、实际 owner、允许修改文件、明确不在本次范围的内容、输入候选和验收命令。公共契约有治理问题时，把其最小修复作为本次目标，并列受影响调用方和生成物。
3. 根据任务类型选择一个主实现者：沿用本项目 DSH，或指定已通过环境验证的 OpenCode。复杂跨模块设计/难题由 Codex 先形成可实现契约；需要 Codex 自己实现时，后续独立审查由新会话/指定审查者承担。
4. pi 只在存在有边界的复现/脚本工作时辅助。WorkBuddy 只在有简单任务和可用免费额度时领取候选草稿；它失败或不可用就跳过，不影响主任务开始。
5. 不启动两个 agent 在同一目录同时写同一任务。具备 Git 且已建立基线时可按项目约定用 worktree；无 Git 时先给文件所有权和独立副本方案，不假装 worktree 已创建。需要调整项目版本管理时单列一项任务，避免把整个父目录或机密纳入仓库。
6. 只让实现者跑实现验证，ZCode 做独立预验收，Codex 做最终审查；各环节使用冻结候选。低风险小任务可按项目治理缩短流程，但本项目要求的 Gate 不得擅自删除。
7. 若已有待审候选，优先完成该候选的预验收与签收，不开启重复实现。若环境升级正在进行，先使用可用 stable 环境，candidate 不接管关键主任务。

输出一张任务卡：

```text
task_id / title:
owner / primary_implementer:
project_root / work_directory:
input_revision_or_snapshot:
prerequisites_and_evidence:
objective:
allowed_files:
contract_changes_if_any:
acceptance_commands_and_expected_behavior:
time_or_cost_budget:
handoff_paths:
reviewer / next_step:
blocking_root_cause_and_repair_path_if_any:
```

随后给出可直接发给所选实现者的简短启动提示词，引用该任务文件和本目录对应角色提示词。如果当前会话已被用户授权实际执行所选任务，可继续完成你负责的工作；不要未经授权通过外部消息服务代发任务。
