# P02-01-R01 补充：保持已审原交接字节

当前G01独立review同时绑定P02-01原evidence/seal/dsh.md。覆盖它们会使刚签review失效，与刷新依赖形成循环。本补充收窄上一条刷新指令，完成相同前置核验目标。

不得改写原 docs/handoffs/P02-01/dsh.md、artifacts/handoffs/P02-01/dsh/evidence.json、seal.json 及原日志。旧记录保留启动时历史身份和限制。仅新增 docs/handoffs/P02-01/dsh-r01.md、artifacts/handoffs/P02-01/dsh/dependency-refresh-r01.json、artifacts/handoffs/P02-01/dsh/dependency-refresh-r01-seal.json；复算探针仅 tmp/P02-01/R01/**。

新增附件记录原交接sha、当前G01/review实际有效性、源代码及必需日志字节未变、复用依据、当前候选、当前实际UTC以及作者/停写状态。明确旧依赖是历史前置，不把旧Gate写成现行有效；最新前置由本附件供ZCode核验，原交接不冒充更新。不得将本附件加入G01review输入，不改review/Gate/任何业务源码/测试/契约。先验证真实原证据与当前Gate，再封存本次附件。

若已改写原交接，先依据此次写入前保存的原字节恢复，检查原evidence SHA256=36f08ff6a8b983c8ba749ef1bbf6fc4b0ae157059e4036f1e6f7917ec274c4c8，并以G01-codex-review.verified_input_hashes确认全部原绑定恢复。不要靠重算旧hash或改他人记录处理。实跑日志历史不删改。完成停写交ZCode，不启动P02-02。
