# 给 ZCode：N02-R02-C 契约独立复核

工作根：D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent；保留现有模型。

本轮立即执行 N02-R02 的 C 契约分区。读取根规则、docs/agent-toolchain/13-partitioned-parallel-dispatch.md、N01-R02 最新交接/evidence、N02-R01 blocker 和当前规范附表。

绑定候选：content-sha256:d1c94436a020158a0573d290443c7c6799711da6564b1609a294fb332d8b7f63。你必须未参与该候选实现。若本 C 分区已有同轮主写者或已完成记录，核对并复用实际交付，不并发覆盖其输出。

独立审查 45 项 EntityKind 的完整成员/精确序列化值、EntityRef 闭包、十类事件的 kind/id/revision 映射及消费一致性。编写并实跑本分区必要正反例，给出唯一阻断 N02-R01-F02-C01 是否解决的结论。其他已解决设计只按本轮影响核对。

唯一可写：
- artifacts/handoffs/N02-R02/review-contract/**
- tmp/N02-R02/review-contract/**

在自己的分区交付 review.md 和 evidence.json，记录实际 ZCode 身份、候选、被审输入 hash、命令/退出码、原始日志及缺陷/覆盖边界。被审候选只读；会生成文件的命令在分区临时副本运行。

完成后由用户/调度者将交付路径交给 Codex N02-R02 主审。你不更新冻结、官方 Gate 或其他分区。本结果是 G00 辅审，不生成常规 Task 的 ZCode precheck。交付后停写。
