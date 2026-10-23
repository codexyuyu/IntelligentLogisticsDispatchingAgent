# P02-02-IMPLEMENT-01 · WorkBuddy A 实现贡献

工作根仅 D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent。用户已授权按吞吐改派实现贡献。DSH 当前窗口属另一 Android 项目，不访问该工程；本贡献真实作者为 WorkBuddy，不冒写 DSH 正式交接。正式整合仍由合法 DSH 主写者核验后交接，独立 ZCode 不参与实现。

前置已核验：G01 50bae8ac3b7970864ccc7aa95a83fee89c9ef52c567e768824a49873ab5fda39；P02-01 precheck 9245cb8a76b0f71b020fe9fad540aced72dc6d103d5cf772944ff873256032b5，独立52测试/60探针通过，42输入/7日志hash有效，原执行者已停写；范围越界两脚本原字节已移出根，事实及hash见 ../zcode/P02-01-F01-RECHECK-scope-resolution.json。未签G02不阻断同阶段P02-02。启动前复算上述真实记录及依赖，不重跑G01。

读取 AGENTS.md、AI-CODING-PLAN.md、manifest、OWNERSHIP、PHASE_GATES、docs/prompts/02-domain/P02-02-master-entities.md、冻结契约、P02-01最新交接。唯一目标完整实现原 P02-02 订单、货物、运仓资源纯领域实体及严格边界 DTO。仅写原manifest七文件：
- docs/implementation/P02-02.md
- docs/implementation/reports/P02-02.md
- packages/contracts/src/logistics_contracts/entities.py
- packages/domain/src/logistics_domain/orders.py
- packages/domain/src/logistics_domain/resources.py
- tests/unit/test_p02_02_master_entities.py
- tests/integration/test_p02_02_master_entities.py

不改包marker、P02-01、公共枚举、锁/契约/Gate/他人证据。确需导出修改先交精确影响卡，不自行扩范围。当前仅一个实现贡献写者；不启动P02-03或其他业务任务。

辅助脚本、缓存、pytest临时物、自动记忆及真实作者交付 report.md/evidence.json/seal.json 仅 C:/Users/30382/AppData/Local/Temp/IntelligentLogisticsDispatchingAgent-workbuddy-p02-02-impl-01/**；不得写根 tmp 或 .workbuddy 等记忆文件。固定正式 dsh/evidence.json 不在本贡献白名单，禁止冒署。收尾必须停止写入并交精确文件hash、原日志、实际 argv/cwd/exit/counts 与限制，待 DSH 实际整合及独立验收。

复用已有 WBAI DTO 预研 C:/Users/30382/AppData/Local/Temp/IntelligentLogisticsDispatchingAgent-wbai-reuse-r01/tmp/orchestration/workbuddy-ai/p02-dto-reuse/report.md（679ddf0d3ccb6cb5a6f8e89813f694dfd015acdf1815e526ee274d10ba69e177），sources.json（fe630345412fa5b2e19141b4df00fd9b765d64c41ed46a37ac854cf25fdc1b4b）；先核验实际文件。Pydantic 2.13.5 锁定能力可复用，示例未实跑，必须亲自验证。domain 无框架，DTO 复用 domain 唯一枚举；Resource 五类具名判别联合、Calendar 三字段往返；禁止新增依赖或复制框架。冻结业务负例必须保留，不加无需求防御/安全层。

原五类明确正反例全部实际验证；从正确工作根运行原必需两命令，输出日志只上列 TEMP：
uv run pytest tests/unit/test_p02_02_master_entities.py tests/integration/test_p02_02_master_entities.py -q
uv run python scripts/check_architecture.py
不跑全仓回归（会触发整仓快照停写要求），不使用零测试/skip/旧测试冒充本任务。容量1001g/1000g数据可表示且分配违规，温区反转拒绝，Resource worker/Worker接受而worker/Dock拒绝，Calendar完整往返同值。报告区分实现、自测与尚待正式整合/独立验收；完成停写。

模型现场选择用户指定 GLM-5.3 及最高支持推理档。未核验免费/夜间条件记未知，不购买/重置/改全局配置；额度本轮不阻断已授权执行，实际服务限制如实交接。
