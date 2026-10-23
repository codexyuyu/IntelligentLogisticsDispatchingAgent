任务 ORCH-REUSE-01；角色下一业务阶段开源复用预研；整合者 Codex 总调度。
工作根 D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent。
只读 pyproject.toml、packages/*/pyproject.toml、apps/backend/pyproject.toml、P02/P03 原任务卡及数据契约；只写 tmp/orchestration/workbuddy-ai/reuse/ 内自己的产物。
对 P02 Domain Model 和 P03 PostgreSQL 迁移所需能力做一次轻量 GitHub 官方仓库核查，优先已装依赖，最多5项可直接节省实现/验收时间的候选。记录官方链接、实际版本/commit、许可证、功能对应、新增依赖/体积影响、采用或不用的具体理由。证据不足明确标注。不要引入框架或安装依赖，不启动 P02/P03 实现。报告≤1000字；不重复既有证据索引。
不得写源码、Gate、他人交接、项目/全局配置、.workbuddy-ai/memory。自动记忆只能落在专属 tmp 目录；无法限定就停止写记忆并报告，不改 OWNERSHIP/断言。遵守 docs/agent-toolchain/15-autonomous-orchestration.md，完成停写交产物和哈希。无需再次确认执行。
