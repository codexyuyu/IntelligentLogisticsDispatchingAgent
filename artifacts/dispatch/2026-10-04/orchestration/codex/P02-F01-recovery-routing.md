# P02-01-F01 后的证据恢复路由（草案，未派发）

结论：本次最短且不依赖检查器遗漏的保守链为：DSH 修复封存 → ZCode 仅重验 P01-01 受影响部分 → 独立 N05 更新 G01 审查并运行一次正式 G01 → DSH 追加 P02-01 前置依赖刷新附件 → ZCode 重验 P02-01 业务 → P02-02。P01-02/03 不因全局 revision 变化而重做各自预验收；不要求 DSH 重新生成未变化的 P01-01 交付。

本文件仅为调度草案；未签收、未改源码/测试/官方证据。所有输出仅在本系统临时目录。`scope-audit.json` 是实际只读审计，`audit_readonly.py` 可用 `python -B` 复算；执行时需重新核对修复已封存，不能采用修复过程中的候选。

## 已确认事实

1. 官方 `artifacts/gates/G01.json` SHA256 `a7eed6aee3f0e21b39e440aee6a7d4f2f5f74b5d1407eb4011eac7215a3b18c4`，绑定 **40** 项输入，无 P02 源码/测试/交接直接输入。**262 项**属于 `G01-codex-review.json`，其 SHA256 为 `c41888a77a22d146502dd5f91de85f12f036c4cbd70fbf3de00d45789630a275`。
2. P01-01 precheck SHA256 `7ae3e9d6f22c86c4b6a62679dcebdbab291317bfc2901147437ec331afa8180b`，57 项输入含 states/primitives/errors、P02 两测试、P02 DSH evidence 和报告。P01-02/03 precheck 分别为 36/33 项，不含上述 P02 输入。
3. 只读审计时当前候选为 `content-sha256:477a883d2a29deb5cb60f8269c8712693d9e7aedeb3a620ba4953a630289158c`，82 文件；P01-01 precheck 已有 4 项输入漂移，G01 review 已有 5 项漂移且 revision 不同。审计期间所读输入前后未变；后续修复仍可能继续，不把这次观测作为最终封存。
4. 同一次实跑，Phase02 的 `check_previous_gates()` 返回 G00/G01 通过；P01-01 DSH evidence 的 26 项 deliverable_files 无漂移，P01-02/03 precheck 仍新鲜。**前序 Gate 读取器通过不等于整套独立审查闭包仍有效。**
5. `packages/domain/src/logistics_domain/__init__.py:25` 实际导入 errors/primitives/states；states.py 改动会进入六包导入及纯度验证的读取闭包。不能以“文件属于 P02”把它从 Phase01 相关输入中整体排除。

## 法规式依据及实现边界

- `docs/plan/GATE_EXECUTION_CONTRACT.md` §2 定义 input_artifact_hashes 为“本次判定所依赖的输入产物”；§3/§4 规定相关源文件 hash、不同阶段允许不同 revision、按影响重验。`docs/plan/PHASE_GATES.md:13` 规定不要求最终 HEAD 等于旧阶段 HEAD。依据是相关性，不是任意减少 hash 数量。
- `scripts/gates.py:791` 的四类 precheck 必需输入只是检查器下限；`docs/workflow/HANDOFF_CONTRACT.md:25-38` 还要求真实实现、实际读取的源码/配置/契约、日志、precheck、前置 Gate 和阶段断言。不能只保留四个 hash 或一个无关 hash。
- `scripts/gates.py:813-838` 在正常 G01 审查中比较当前 revision，并逐项校验 review 输入；`1124-1162` 的 G01 check-only 同样比较当前全局 revision。
- `scripts/gates.py:402-449` 的当前候选白名单跨所有已存在的实现目录，**没有按 phase 裁剪**。仅缩减 review 输入不能使新增 P02 代码不改变全局候选；不能用 `--revision <旧值>` 隐藏新候选。
- `scripts/gates.py:882-937` 验证前序 Gate 时核验其记录、40 项已绑定输入、原日志及依赖，不要求其 revision 与新阶段全局候选一致；也没有递归重验当前 precheck/review。不能利用后一个实现遗漏忽略已知漂移。
- `scripts/gates.py:1184-1195` 自动生成 G01 的 40 项输入；`PHASE_ASSERTIONS:141-176` 包括导入、全层检查、锁、失败关闭与历史资产。正式恢复 G01 时 F3 要求现行执行器亲自运行本阶段全部命令；不能手改官方 G01 hash、状态或免跑命令。

## 影响清单

| 变更/记录 | 本次影响 | 处理 |
| --- | --- | --- |
| states.py、P02 两测试、P02 说明/交接 | P02 FAILED 必须新验；P01-01 precheck/G01 review 绑定漂移 | 封存后按下列角色重验；旧失败和旧通过都保留 |
| domain 包 marker | 本卡禁止修改；当前是 P01 直接交付与 G01 直接输入 | 前后逐字节确认；若变化另开具体影响任务，不扩大本修复 |
| P01-01 DSH 26 项交付、安装/锁日志 | 本次只读审计未漂移；原回归引用指向 dadad196 历史快照 | 保留原字节，按真实时间/候选引用为历史，不把 272 passed 当新修复验证 |
| P01-02/03 DSH/precheck | 已记录输入未受本次限定修复影响 | 复算现存输入/日志及依赖后复用；不重写日期或 hash |
| G00/冻结契约/锁/治理工具 | 本卡均禁止变化 | 检查原字节与依赖；不重签 G00，不修改冻结记录 |
| 当前 G01.json | 40 项直接输入当前仍新鲜，但当前独立审查链有漂移 | 不凭读取器通过跳过影响审查；确需恢复时由独立 N05 一次正式重验 |

## 可裁剪与不得裁剪

新一轮审查可在明确独立范围判断后，不再把以下 P02 资料作为 G01 的**当前判定依赖**：P02 业务测试、P02 当前完成报告/DSH evidence/seal、P02 业务全回归日志，以及仅为任务派发使用的非必要过程文档。前提是 G01 本轮结论不再依赖这些资料证明当前正确性，改用 Phase01 自己的实际验证证据。实际消费的规则和日志仍必须绑定；不能先依赖它们再从映射删除。

若 P02 报告仅用于证明此前 marker 修改得到授权，可在独立审查前逐字节归档到该审查的独占历史目录，并注明只证明当时授权事实。不得把当前源码复制到归档后以归档 hash 取代活跃源码的相关性验证。

必须保留：Phase01 实际交付/测试/配置、相关契约和规则、G00、P01 DSH 与全部必需 precheck、实际采用的日志、marker 及其实际导入依赖，和本轮层检查读取的相关源码。全层检查扫到的源码不能仅因位于后续阶段而豁免。逐项记录保留/移出及理由；旧 262 项记录原字节归档，新记录按新审查真实创建，不修改历史审查。

**可减少无关元数据触发；不能保证任意后续源码变化都免于 Phase01 影响验证。** 新领域文件、入口装配和导入/依赖变化可能真实影响 G01。以后先区分“仅全局 revision 改变”与“G01 判定输入/行为改变”，不要每个 P02 Task 都机械调用 `--phase 01 --check-only` 后宣布必须全量返工。不能仅靠本提示词彻底解决当前 runner 的全局候选与阶段输入粒度差异；任何执行器设计变更必须另立任务，当前不实施。

## 下一轮任务卡 A：ZCode / P01-01-IMPACT-F01（建议 ID，未派发）

工作根：`D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`。你是未参与 P01/P02 实现的独立 ZCode 审查者；只处理 P01-01 受 ZC-P02-01-F01 修复影响的预验收，不签 G01/G02，也不验收 Reservation 业务。

启动条件：DSH P02-01-F01 真正封存停写；限定源码差异仅 states.py 和本任务两测试；marker、P01 26 项交付、锁、契约、检查器、G00 均复算未变。若不符，退回精确差异；不得扩大修复。核对当前候选，不使用本文审计中的过程候选。

最新投送锚点（调度已核对，接收者仍独立复算）：DSH F01 已封存 14 项产物/日志，候选 `content-sha256:477a883d2a29deb5cb60f8269c8712693d9e7aedeb3a620ba4953a630289158c`，P02 DSH evidence SHA256 `eac21615a8511ea371f12dc593f54f7e9b8aa7869da1bc8fdb5c921f6eb4281c`，实跑 52 测试、架构检查 exit 0；须待调度确认执行会话停写后开始。DSH 正文仍列旧 evidence `1ff843…` 属人工摘要待更正；机器 evidence/seal、产物和日志闭包核验成立时，不因这一摘要旧值阻断受影响导入验收，在下述依赖附件明确更正即可。

读取 P01-01 原任务、当前 DSH P01 交接、修复的真实差异、冻结/交接规则及本次影响清单。运行 P01-01 两测试的 manifest 命令，另实跑隔离六包导入、domain 纯度/未实现入口失败及必要分层检查；只引用不变安装/锁/历史资产日志，明确哪些复用、哪些本轮实跑。不要重复全仓 unit+integration 或 P01-02/03 的独立验收。

只写自己的 `docs/handoffs/P01-01/zcode.md`、`artifacts/handoffs/P01-01/zcode/precheck.json`、`artifacts/handoffs/P01-01/zcode/logs/p02-f01-impact/**`、`artifacts/handoffs/P01-01/zcode/archive/p02-f01-impact/**`；临时脚本/活跃日志写调度明确分配的系统临时唯一子目录。先归档旧 precheck/报告/日志原字节。

新 precheck 绑定四类必需输入及实际 Phase01 读取闭包，保留 states 等真实导入依赖；P02 业务测试/当前交接不再作为本轮 bootstrap 通过的证明。P01-01 DSH 交付仍新鲜时复用其原记录并明确历史快照，不要求改写自身旧 revision；如其中本次必须依赖的真实产物/日志失效，提交一项 DSH 最小补充需求后停写。

复算前后 hash、真实命令/退出码/用例数；通过才写自己的 Z_PRECHECK_PASSED。P01-02/03 仅复算，不改字节。交独立 N05 后停写。

## 下一轮任务卡 B：独立 Codex / N05-R02-IMPACT（建议 ID，未派发）

仅在 A 交付停写、全部必需 precheck 和 G00 有效后执行。保持独立身份，不增加无必要子审查；保留当前源码、测试、marker、契约、所有权、锁及 15 号 policy 原字节。

逐项裁定 Phase01 实际读取闭包；按上节创建真实的新 review 输入清单，解释移出的 P02 业务/过程资料，保留相关源码和完整必要证据。候选用现行 runner 真实 auto 全局算法复算，不造阶段专用 hash 传给现有 runner，不用旧 revision 伪装未变。

只写 `docs/handoffs/N05-R02-IMPACT/codex.md`、`artifacts/handoffs/N05-R02-IMPACT/codex/**`、合法官方 G01 review/G01.json/本次日志；旧官方 JSON、review 和全部原日志先逐字节归档到该任务专属目录。活跃临时输出在系统临时唯一子目录。

对相关 bootstrap 影响完成必要关键复现后，写新独立 review，实跑一次 `uv run python scripts/gates.py --phase 01 --revision auto`；七条阶段命令和附加断言全部由原执行器实际执行。不得用 `--skip-commands`、旧成功字段或只更新 hash 替代恢复。G01 40 输入、原日志、依赖及完整当前审查闭包均成立后才签收。

正式回归前所有非验收者在工程根停写，包括调度 state、日志和自动记忆；输出准备/归档应在静止窗口之前完成或由唯一验收者按顺序写入。原 P01-03 快照测试不改。检查后将本轮覆盖边界与未来触发条件写清：相关源码/导入变化仍需影响复核；仅全局候选或未绑定无关文档变化不自动让已签历史阶段失效。

## 后继卡 C / D：避免新的依赖循环

C：G01 恢复后由 DSH 仅追加 P02-01 的前置刷新附件及 seal，记录新 G01/review hash、修复封存候选和原业务日志来源；不要重写 P01 报告/交接来更新对新 G01 的引用，也不要将这个后写附件加入刚完成的 G01 review 输入。若 DSH P02 实现交接仍可作为同候选历史事实，则保留原字节；本附件只更新前置引用。

D：独立 ZCode 按原 P02-01 业务任务与 ZC-P02-01-F01 缺陷卡重验，核对新 G01 和依赖附件，实跑两项必需命令及 Reservation 正反例；只写 P02 自己的 precheck/交接/日志。通过才交回调度派 P02-02；不在此签 G02。不能把观察项或额外业务边擅自加入冻结契约。

用户本轮余额不阻断授权工作；不使用重置卡、不购买额度、不改全局设置。此草案未取得新的源码写权限，也不改变独立身份及官方签收职责。
