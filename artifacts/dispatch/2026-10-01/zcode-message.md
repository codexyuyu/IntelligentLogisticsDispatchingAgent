项目：D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent。保留我已选择的模型。这一轮只做 G01 独立预验收准备，与 DSH 的 P01-02 返工并行；不得边改实现边签收。

先读根 AGENTS.md、docs/agent-toolchain/current-project-review-2026-10-01.md、docs/agent-toolchain/11-dsh-repair-g01.md、docs/agent-toolchain/05-zcode-precheck.md、原 P01-02/P01-03 提示词、PHASE_GATES 与 GATE_EXECUTION_CONTRACT。DSH 现正在修 scripts/gates.py 和 P01-02 测试，因此当前工作区仍是可变候选。

只读梳理 P01-02 四类已确认缺口和 P01-03 的原始验收要求，列出新候选到达后需独立执行的具体正反例、真实命令、必要输入文件集、日志/依赖哈希核验规则及旧证据失效范围。重点验证：审查记录缺失/合法存在两种状态；写日志不改变候选但改源码改变候选；空/遗漏/漂移输入拒绝；不完整/漂移前置 Gate 拒绝；临时探针不改官方 G01。

本轮唯一可写目录是 tmp/zcode-g01-precheck-preparation/，交付 PRECHECK_PLAN.md 与必要的只读检查索引。不要修改 scripts/、tests/、apps/、packages/、docs/、任何 DSH 证据或已有 zcode precheck。不要运行会签 Gate、修改源文件或覆盖官方证据的命令；不重复运行完整 Phase 01 测试，避免与 DSH 写入候选同时验收。

候选尚未固定，本轮不得产出 Z_PRECHECK_PASSED、正式 precheck.json 或 Codex review。完成准备后停止，明确“等待 DSH 新候选固定和再次下发正式预验收”，不要自主轮询或进入 P02。后续正式审查必须重新读取新候选并重新计算 hash，不能照抄本轮准备材料的输入 hash。
