# N05-R03-ENV · 独立 G01 下载环境恢复

责任者：原独立 `/root/n05_independent`，gpt-6.1-sol xhigh；未参与候选实现。工作根仅 D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent。本任务属于 N05-R02-ENV-NPM-01 的限定环境恢复，不修改总提示、源码或验收条件。

先读 AGENTS.md、原计划/manifest/PHASE_GATES/OWNERSHIP、N05-R02-IMPACT 卡和最新失败交接、seal/evidence/final-audit。本轮候选仍为 content-sha256:477a883d2a29deb5cb60f8269c8712693d9e7aedeb3a620ba4953a630289158c（82文件），dirty eaea942624f00e5da16e89a3e744d3a2c1c659fcf9eeda0a23787116681d636f。

恢复依据已由 root 实际核验：旧任务已明确停写；44份封存文件无漂移，seal abac462cd99f1979ae4a10b32b0b7e13306d8aa7b70e51682880ab809c546ac8；失败官方 G01 9f30bb45307721ecdb6d85259bac18230002d91d6dc5eabc61f55fd41337e35c；40 Gate 输入/184 review 输入/12日志哈希均有效。失败唯一为首轮空 npm 缓存下载超时，25/26；其后同次正式 P01-01-cmd3 npm ci 实际 exit0。root 只读逐项复算本卡前序缓存内三份 tarball 的冻结 package-lock SHA512 均匹配（8749/899597/3123044字节，0网络/0缓存修改）。必要条件已变化，准许本新任务一次真实正式 Gate。

精确可写：docs/handoffs/N05-R03-ENV/codex.md、artifacts/handoffs/N05-R03-ENV/codex/**、合法官方 artifacts/gates/G01.json 与 G01-logs/**；仅有实际需要且范围不变时可刷新 G01-codex-review.json，优先复算复用已有效的 e64827a62caa4c497304c66d85df154ac6047e571b3c5947b97a2d7c93925efc。新正式运行覆盖前，把本次失败 G01/review/全部12原日志逐字节归档到本任务专属 archive，并登记原路径/bytes/hash。N05-R02-IMPACT 全部封存文件保持原字节，不重写旧失败事实。

活跃脚本/缓存/pytest/日志只能落 C:/Users/30382/AppData/Local/Temp/IntelligentLogisticsDispatchingAgent-n05-r03-env/**。已停写的前序独占 TEMP/IntelligentLogisticsDispatchingAgent-n05-r02-impact/** 只读；可复制已核验 npm/uv 缓存到新任务唯一 TEMP，复制后再次核验冻结锁 tarball 完整性，确保三个包实际存在再正式运行，避免再用空缓存。环境变量只作用本次子进程，不改全局、不设离线模式替代真实 npm ci。测试、断言、命令、超时、锁、ACL均不变；缓存仅下载源，真正安装/导入/锁一致性仍由原测试验证。

root 已暂停所有非验收者工程根写入。归档/核验准备后，亲自执行一次 uv run python scripts/gates.py --phase 01 --revision auto；七命令、五断言、十四记录检查照原要求，不跳过、不以 check-only 或改字段签收。现有效影响 review、6进程导入探针及前序未变审查证据复算后按范围明确复用，避免重复无效审查；当前正式测试仍全部实跑。不要写 root state/他人交接/precheck/G00/所有权/15号规则或实现、不要启动 P02/P02-02、不要签 G02。失败提交实际最小缺口并停写，不在本卡第二次正式重跑。

成功需核验官方签收、40输入/184 review闭包、原日志/依赖及真实auto候选一致，保存argv/cwd/UTC/exit/数量/hash、报告/evidence/seal，明确已停写后交 root。G01 passed 才允许后续 DSH 新依赖附件，不覆盖被前序 precheck/review绑定的 P02 evidence/seal。当前余额授权覆盖旧停止线，继续观察真实限制；不用重置卡、不购买、不改全局配置。
