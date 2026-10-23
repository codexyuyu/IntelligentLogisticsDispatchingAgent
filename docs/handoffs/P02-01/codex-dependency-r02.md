# P02-01-DEP-R02：当前依赖附件

结论：当前 G01 前置有效，依赖核验已完成并停写；P02-01 业务仍待原独立 ZCode 复核。本附件作者 Codex root；实现作者仍为 DSH-A，原实现交接通道和责任不变，不冒写 DSH 或 ZCode 签收。

当前候选 content-sha256:477a883d2a29deb5cb60f8269c8712693d9e7aedeb3a620ba4953a630289158c，82文件。G01 SHA256 50bae8ac3b7970864ccc7aa95a83fee89c9ef52c567e768824a49873ab5fda39；review e64827a62caa4c497304c66d85df154ac6047e571b3c5947b97a2d7c93925efc；N05-R03-ENV seal e3e3bab32623de6b68450ac8c672551b5ebbd93d031f77c9e0d292de52362368。正式7命令、5断言、14记录检查通过，26/26；56/96/74共226只证明Phase01。

本附件真实只读复算：36份新封存、44份旧失败封存、G00 25输入、G01 40输入/review184输入/12日志、三预验收123输入/29命令日志、DSH F01 14项产物/日志均一致。旧预验收保存的历史失败日志仍保留失败身份；现行前置由新正式G01证明，不把历史补充失败当成当前必要命令通过。

DSH F01 evidence eac21615a8511ea371f12dc593f54f7e9b8aa7869da1bc8fdb5c921f6eb4281c、seal32d2a882b442bb25761f11f23f56e146013a7a91083c70aa0c73a9c4e7c0f4c5及旧交接/附件/日志不改。原52业务测试和架构0违规仅核验原日志，未重跑；旧272属于修复前候选，不代表本候选全回归。原F01记录中的旧前置仅属历史，当前前置以本附件记录供ZCode独立核验。

改派依据为用户允许按吞吐改派任意合适agent。电脑自动审批拒绝读取当前DSH另一Android项目完整界面；root未进入或读取该工程，将本次纯依赖核验改由Codex署名新增。未改任何实现、测试、契约、锁、规则、官方Gate/review、DSH/ZCode旧记录，也不将新附件加入G01输入。

实跑命令/UTC/exit0/原日志/hash及逐项输入见 artifacts/handoffs/P02-01/codex-dependency-r02/evidence.json、verification.log。实际核验源码保存在同目录verify.py。当前不签G02、不启动P02-02；下一执行者原独立ZCode，仅复核P02-01 F01业务。
