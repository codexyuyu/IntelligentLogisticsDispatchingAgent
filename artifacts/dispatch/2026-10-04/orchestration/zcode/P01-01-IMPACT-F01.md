# P01-01-IMPACT-F01 · 独立受影响导入预验收

工作根：D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent。沿用未参与实现的原 N04 独立 ZCode 会话；仅做本任务，完成停写。

依据：Astra xhigh 的 `artifacts/dispatch/2026-10-04/orchestration/codex/P02-F01-recovery-routing.md`，仅执行卡 A。读取 AGENTS.md、AI-CODING-PLAN.md、OWNERSHIP.json、docs/plan/TASK_MANIFEST.json、docs/plan/PHASE_GATES.md、docs/workflow/HANDOFF_CONTRACT.md、原任务 `docs/prompts/01-foundation/P01-01-workspace-bootstrap.md`、原 P01-01 DSH 交接与本轮修复封存。不要展开后继卡 B/C/D。

启动锚点：DSH P02-01-F01 已交付停写；当前候选 `content-sha256:477a883d2a29deb5cb60f8269c8712693d9e7aedeb3a620ba4953a630289158c`，82 文件。机器 evidence SHA256 `eac21615a8511ea371f12dc593f54f7e9b8aa7869da1bc8fdb5c921f6eb4281c`，seal SHA256 `32d2a882b442bb25761f11f23f56e146013a7a91083c70aa0c73a9c4e7c0f4c5`；本轮 52 项测试及架构检查 exit 0，14 项产物/日志调度复算一致。接收者须独立复算，不能把旧 272 回归当本候选结果。

仅写：
- docs/handoffs/P01-01/zcode.md
- artifacts/handoffs/P01-01/zcode/precheck.json
- artifacts/handoffs/P01-01/zcode/logs/p02-f01-impact/**
- artifacts/handoffs/P01-01/zcode/archive/p02-f01-impact/**
临时脚本、活跃日志及 UV 缓存仅 `C:/Users/30382/AppData/Local/Temp/IntelligentLogisticsDispatchingAgent-zcode-p01-f01-impact/**`。先逐字节归档旧报告/precheck/采用的旧日志，保留历史。禁止源码、测试、契约、锁、所有权、检查器、其他交接、官方 Gate、policy 和工程根自动记忆写入。

先复算 P01 DSH 26 项原交付、P01-02/03 现有 precheck 的输入/日志和 G00；未受影响者保留原字节复用。当前 P01-01 旧 precheck 5 项漂移，G01 review 8 项漂移；G01 40 项直接输入仍新鲜，不能只因 revision 不同断言历史 Gate 无效，也不能利用前序检查器未递归 review 而跳过已知实际导入影响。

实跑 `uv run pytest tests/unit/test_p01_01_workspace_bootstrap.py tests/integration/test_p01_01_workspace_bootstrap.py -q`；另做隔离六包导入、domain 纯度、未实现入口明确失败及必要分层检查。安装/锁/历史资产输入未变时核验并复用其原日志，逐项区分复用与本轮实跑；如不能证明有效，交一项最小必要补充，不伪称通过。不要跑整个 unit+integration、重做 P01-02/03 或验收 Reservation 业务。

新 precheck 采用真实 Phase01 读取闭包及必需四类输入；保留 states/primitives/errors 与 marker 的实际导入依赖。P02 业务测试、当前 DSH 业务交接及其报告不作为本轮 bootstrap 正确性证明；逐项说明旧集合中移出/保留理由，不能只保留检查器最低四项或用归档源码代替活跃源码。使用现行 auto 全局候选，不伪造阶段 hash 或沿用旧 revision。该裁剪不意味着后续相关源码/导入变化免于复核。

元数据更正由后续 DSH 依赖附件处理，本轮绑定机器事实：dsh-f01.md 首表 evidence 1ff843… 是旧摘要，actual 为 eac216…；seal previous_candidate 有拼写误差，真实旧值见旧失败 precheck；seal review 漂移清单正文只有 5 项而计数为 8，以实算清单为准。不要为这些已识别摘要误差改写他人交接或重复业务返工。

全部必要检查和哈希成立才写自己的 Z_PRECHECK_PASSED，提供实跑原日志、退出码/数量、真实前后输入与输出哈希、复用依据及限制，交独立 N05 后停写。不签 G01/G02、不启动 P02-02、不修改正确性断言、不加入防御层或安全框架。
