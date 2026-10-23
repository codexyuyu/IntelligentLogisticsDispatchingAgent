# ZCode独立预验收

版本1.0.0；按[交接契约](HANDOFF_CONTRACT.md)、[冻结Gate规则](../plan/GATE_EXECUTION_CONTRACT.md)、[当前派发](../agent-toolchain/12-project-completion-dispatch.md)执行。单任务预验收不签阶段Gate，不使下一阶段自动可启动。

1. 核验实际工作根、任务ID、角色、候选清单、A/B白名单和最早前置。P01-02四项返工已READY_FOR_ZCODE，不重复分配已修复的AGENTS.md所有权缺口。
2. 读取manifest/prompt、冻结规则和实际实现；复算候选revision、每个DSH产物/hash、原始日志/hash、退出码与测试数；历史DSH结论不是独立验证。
3. 冻结必要输入，记录`verified_input_hashes`的四类必需输入及实际核验的源码/配置/契约/日志/前序Gate。读取之前记录hash，测试结束再次比较；输入变化则停止该轮并重开新候选审查。
4. 在当前锁定环境独立复跑任务命令、正反例和必要边界。保存真实argv/cwd/exit_code/counts与完整stdout/stderr；PostgreSQL、OR-Tools、SimPy、模型、浏览器按任务使用真实依赖。缺凭据/外部服务写BLOCKED或NOT_RUN与责任方/恢复条件，不写通过，不用fake或skip替代验收。
5. Gate负例在受控临时仓库；开发探针使用`--out-dir tmp/<task>/<round>/...`。对`--check-only`比较官方记录与日志的运行前后字节/hash，不把退出0当签收。不得删除真实review/precheck满足负例。
6. 全部要求成立后先写本角色原始日志，再写本角色precheck；只在`artifacts/handoffs/<task>/zcode/`写独立结果。失败写FAILED/BLOCKED、具体缺陷、范围、责任方及恢复条件；退回实现/治理角色，ZCode不代改实现。
7. 把precheck与日志交独立Codex；其review完成并真实Gate通过前禁止启动下一阶段。审查中修改源码必须产生新候选，不沿用原precheck。

| 必查正反例 | 验收说明 |
| --- | --- |
| 完整非空输入hash且正确task/gate/reviewer | 读取规则通过，独立测试证据完整才可写通过 |
| 空hash、漏prompt/DSH evidence、旧源码hash | 明确拒绝，不能手填通过 |
| 命令exit=1、零用例、关键skip | 验收失败；保留日志 |
| 仅status=passed的前序Gate、缺日志/命令退出码、依赖hash漂移 | 前置无效，停止下游 |
| 缺Codex review、review revision错误 | Gate失败；precheck不能替代review |
| check-only前后、写tmp/日志后候选不变 | 保持官方记录原字节，候选无自扰动；改相关源码后候选必变 |

当前P01-01旧precheck已失效，P01-02/P01-03缺precheck；N01规划1.0.2改变manifest和prompts，使三个任务都须按新输入重验。先由N02独立复核G00与冻结迁移，再N03由DSH刷新自身交接，N04 ZCode验三个任务，N05独立Codex审查G01。本文件不宣称这些工作已完成。
