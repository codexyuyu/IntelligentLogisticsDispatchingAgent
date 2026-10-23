# AI-CODING-PLAN · 使用入口

这是一套面向后续 Coding Agent 的开发 Prompt 系统。**2026-10-01 当前实现：P01-02 四项返工已 READY_FOR_ZCODE；Codex 补所有权规则后完整回归 226 passed，G01 仍未有效签收，业务阶段尚未实现。** 当前状态与后续派发见[完整清单](docs/agent-toolchain/12-project-completion-dispatch.md)；历史 demo 保留只读。

当前入口：[返工后 N01–N05 解阻与验收](docs/agent-toolchain/12-project-completion-dispatch.md)。先读根[执行规则](AGENTS.md)，处理交接治理、G00 漂移、Phase 01 交接及三任务重验。P01-02 旧返工已停写；G01 有效签收前不启动 Phase 02。manifest 的 planned/not_run 是规划初始值，真实执行证据以当前磁盘记录及复核结果为准。

建议按以下顺序使用：

1. 阅读[七项架构总览](docs/architecture/ARCHITECTURE_OVERVIEW.md)，了解模块、依赖、风险和对原阶段顺序的补充。
2. 阅读[PROJECT_MASTER_PLAN](PROJECT_MASTER_PLAN.md)和[TASK_GRAPH](TASK_GRAPH.md)，以阶段Gate作为屏障。
3. 从[Prompt索引](docs/prompts/README.md)选择最早前置已满足的单个任务；本项目当前使用上面的解阻与验收入口，不从 P00-01 重做，也不按最新编号启动。
4. Codex读取Prompt列出的本地契约，核实前置证据，按Files白名单实现并运行Validation Commands。
5. 完成报告写`docs/implementation/reports/Pxx-yy.md`；阶段所有任务完成后执行[Gate规则](docs/plan/PHASE_GATES.md)。Gate失败就修复当前阶段，禁止跳到下一阶段。

所有Prompt自带Context、Current State、唯一Objective、Scope/Out of Scope、Files、数据和接口、业务规则、算法、异常处理、日志指标、具体测试及预期、验收命令、文档和Completion Report。公共契约随本包提供，后续Codex不需要历史聊天记录。预期文件路径写在代码样式中；尚不存在是待实施交付物，不是缺失的规划文件。

| 文件 | 用途 |
| --- | --- |
| [领域目录](docs/architecture/DOMAIN_CATALOG.md) | 32实体、公共字段、关系与生命周期 |
| [数据与Protocol契约](docs/architecture/DATA_CONTRACTS.md) | 类型、单位、错误、状态、跨模块通信 |
| [HTTP与Tool契约](docs/api/API_CONTRACT.md) | 路径、Schema、权限、服务边界 |
| [优化设计](docs/algorithms/OPTIMIZATION_CONTRACT.md) | Routing/CP-SAT/联合/局部重排与验证 |
| [仿真设计](docs/algorithms/SIMULATION_CONTRACT.md) | 状态、事件排序、RNG、快照恢复 |
| [指标定义](docs/algorithms/METRICS_CONTRACT.md) | 14项指标、差异公式、实验公平性 |
| [测试数据](docs/plan/TEST_FIXTURES.md) | 手算正反例和A/B/C场景生成规范 |
| [需求追踪](docs/plan/REQUIREMENTS_TRACEABILITY.md) | 需求→Task→Gate→验收证据 |
| [机器任务清单](docs/plan/TASK_MANIFEST.json) | DAG、反向依赖、文件白名单、命令、初始状态 |
| [规划验证报告](docs/plan/VERIFICATION_REPORT.md) | 本次静态检查范围与限制 |

本轮不调整既有Linear、A/B实时任务状态或旧demo文件。新计划面向完整研究系统；P00/P01先登记从旧骨架到目标monorepo的迁移，明确新的契约来源与所有权。3D是可选增强，不影响核心Gate。

规划自检命令（现在可运行，不启动物流系统）：

```powershell
python tools/ai_coding_plan/validate_plan.py --self-test
```

后续实现任务中的`uv run pytest ...`、`npm ...`、`scripts/gates.py`属于该任务必须交付/调用的未来环境；不能因为本轮未创建应用而伪称这些已通过。初始G00用规划工具核验文档及证据，P01再实现正式Gate执行器。详见Gate文档中的引导说明。
