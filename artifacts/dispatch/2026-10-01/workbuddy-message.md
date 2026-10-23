项目：D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent。保留我已选择的模型。只完成一项可丢弃的文档草稿，与 DSH 代码返工和 ZCode 审查准备并行。仅使用当前已有免费额度与工具；不足时输出已完成部分，不开通付费服务或修改配置。

先读根 AGENTS.md、docs/agent-toolchain/current-project-review-2026-10-01.md、00-common.md、07-workbuddy-small-tasks.md、05-zcode-precheck.md、08-codex-final-review.md，以及 docs/plan/GATE_EXECUTION_CONTRACT.md、PHASE_GATES.md、docs/handoffs/P01-01/zcode.md。现有 ARCH-0004 指出交接治理文档缺失。

基于这些实际来源起草交接文档三份：README.draft.md、02-ZCODE-PRECHECK.draft.md、HANDOFF_CONTRACT.draft.md，唯一可写目录为 tmp/workbuddy-g01-handoff-draft/。写清 DSH 实现交接、ZCode 独立预验收、Codex 最终审查、Gate 执行的职责，固定候选与独立证据哈希，完整状态字段、日志/退出码/测试数量与阻塞报告要求。字段须标注实际源码/契约来源；未知字段写“待 Codex 核验”，不编造兼容 schema。

DSH 正修改 Gate 实现，草稿不得依赖某次中间版本已经正确，不得将当前记录缺失、空输入哈希或候选自扰动当成正常规则。明确真实验收前不得填通过状态，生成顺序不能代替正确的候选隔离和 freshness 核验。

禁止写入 docs/workflow/ 正式目录、改任何源代码/测试/锁/契约/已有证据，禁止关闭 ARCH issue、签收 Gate 或生成通过记录。无需安装插件、执行测试或重复建架构问题单。完成三份草稿后停止，列出草稿路径与尚待核验的字段，由 Codex 后续审阅并决定是否纳入正式治理。
