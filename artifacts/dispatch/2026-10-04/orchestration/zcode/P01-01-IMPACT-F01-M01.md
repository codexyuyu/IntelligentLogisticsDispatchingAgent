# P01-01-IMPACT-F01-M01 · 仅纠正预验收元数据

沿用原独立 ZCode 会话，工作根 D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent。上轮已封存，本卡仅两项纠正；不改代码/测试/Gate/规则，不重跑56项或全仓回归。

当前 precheck 2be58c74702e222ee9b69204b6846e459debeb97dd880d5dd0bad6d3842ebfe9：54项输入和11项命令日志调度复算全部一致；56 passed、六包导入/纯度/loud failure/分层0违规均有原日志。本卡保留这些实际证据。

1. dirty_tree_hash 目前 content-sha256:eaea942624f00e5da16e89a3e744d3 被截断。用现行 GateRunner 实际相关清单复算完整值；预计 content-sha256:eaea942624f00e5da16e89a3e744d3a2c1c659fcf9eeda0a23787116681d636f，不沿用预计而不复算。
2. verified_input_hashes 绑定活跃 artifacts/gates/G01.json。P01-01 前置是 G00；本轮 G01 仅历史漂移背景，并非 bootstrap 通过的前置结论。后续 N05 会合法重签 G01，此活跃绑定会造成前置precheck/G01之间循环。先逐字节复制当前旧G01到自己 archive/p02-f01-impact/metadata-m01/G01-historical.json，复算其a7eed6ae…字节hash；将该历史判断的绑定改为该不可变归档路径，明确只证明本轮开始时历史40输入新鲜，不作为新G01有效性签收。保留所有真实当前源码/规则/导入依赖及G00，不任意删依赖、不弱化断言。不得覆盖或修改原G01。

仅写 docs/handoffs/P01-01/zcode.md、artifacts/handoffs/P01-01/zcode/precheck.json、artifacts/handoffs/P01-01/zcode/logs/p02-f01-impact/**、artifacts/handoffs/P01-01/zcode/archive/p02-f01-impact/**；临时输出仍本任务唯一系统TEMP路径。先归档本轮precheck和报告原字节到metadata-m01/before/，旧归档/日志不覆盖；本卡实跑只需候选及dirty完整复算、归档字节复算、全部输入/日志前后核验及必要precheck机械只读校验。用新round和真实来源解释仅元数据更新，保留实际测试时间与结果，不冒称重新运行测试。新记录中列本卡实际日志hash，报告更新precheck真实hash后停写交独立N05。不得启动业务下一Task或重签Gate。
