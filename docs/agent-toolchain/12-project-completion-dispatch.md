# P01-02 返工后至项目完成的派发顺序

适用日期：2026-10-01。工作根仅为 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，当前机器规划版本为 1.0.0。另一目录 `D:\Agent\Codex\IntelligentLogisticsDispatchingAgent` 的 1.2.0 计划、状态和证据不能混用。各 agent 保持用户已经选择的模型；以下是派发计划，不是任务完成记录，也不是已发送消息。

## 当前事实与更正

- P01-02 限定返工已经交付 `READY_FOR_ZCODE`；不是已预验收或已签收。Codex 已复算 DSH 交付中 20 项文件/日志哈希，全部一致。四项修复仍须独立审查，不能因实现者报告通过就视为最终通过。
- 原 DSH 日志为本任务 96 passed、全套 224 passed / 2 failed。两处失败来自上一轮 Codex 新增 `AGENTS.md` 时遗漏显式所有权。此轮 Codex 已在 `OWNERSHIP.json` 增加 `AGENTS.md: A`，实际重跑 unit + integration 为 **226 passed，exit 0**。这项修正改变了候选；不得照抄 DSH 旧 `afbc7e4c…` 作为当前候选。
- G00 的 25 项输入中 `docs/architecture/issues/README.md` 漂移；冻结的 12 项契约及 173 项旧基线哈希均相符。因此当前不必仅为该漂移重建全部契约，但必须审查新增 issue、处理签收阻断，再按当前内容重录 G00。若治理修复实际修改冻结契约，先重新独立复核冻结记录；不能只补哈希并沿用旧审查身份。
- `ARCH-0004` 已登记交接契约缺失，`docs/workflow/` 尚不存在。应先依据实际执行器明确 DSH / ZCode / Codex 的字段和职责，然后出正式预验收记录。
- P01-01 旧预验收包含过期的 `scripts/gates.py` 输入；P01-02、P01-03 缺预验收，G01 缺 Codex review。三个任务按新候选处理，不沿用旧通过结论。
- `scripts/gates.py` 的 `PHASE_ASSERTIONS` 当前只登记 G01；G02–G39 的额外业务断言尚未注册。后续签收前必须建立与阶段要求对应的可执行检查/证据覆盖，缺覆盖即阻断，不能把空断言列表当成业务通过。
- manifest 共 109 个任务 / 40 个 Gate，其中 P02–P39 共 **103 个业务任务**。`planned` / `not_run` 是初始规划值，不是实时状态。本轮不改这些状态，不签署 Gate，不修改任何 DSH/ZCode 历史记录。

证据：[返工哈希审计](../../artifacts/reviews/2026-10-01/codex/post-rework-state.json)、[所有权修正后的完整测试日志](../../artifacts/reviews/2026-10-01/codex/ownership-fix-full-suites.log)、[DSH 返工交付](../../artifacts/handoffs/P01-02/dsh/evidence.json)、[任务机器清单](../plan/TASK_MANIFEST.json)、[阶段验收规范](../plan/PHASE_GATES.md)。

## 固定角色

| 接收 agent | 本轮及后续职责 | 边界 |
| --- | --- | --- |
| Codex 治理/实现会话 | 解阻、契约裁定、文件落点、环境准备、Gate 检查覆盖 | 修改过的候选交独立上下文审查；不自行声称完成独立验收 |
| DSH-A | A 范围任务的唯一主实现者 | 不签 ZCode precheck、Codex review、官方 Gate |
| DSH-B | B 范围任务的唯一主实现者 | 这是 B 的委派执行会话；不是 A 会话自动获得 B 文件权限 |
| ZCode | 每任务独立预验收，实际复跑与证据核验 | 验收时不修改实现；失败只写本角色缺陷/失败记录 |
| Codex 独立审查会话 | 阶段最终审查、必要复现、合法 Gate 签收、最终 G39 | 没有通过前置与真实测试不签；与实现/治理职责区分 |
| WorkBuddy | 可选文档/界面文案/证据索引草稿 | 只写分区草稿；不设计接口，不改核心代码、锁和签收记录；不可用时主流程继续 |

当前执行器读取 `artifacts/handoffs/<task>/dsh/evidence.json`。因此本清单沿用 DSH 主实现通道；Codex 可先形成设计或补丁，由指定主写者核验并整合。如以后把某正式任务的主实现者改为 Codex/OpenCode，先迁移实现者交接契约和执行器，不能让别的工具冒写 DSH 身份。A/B 的代码所有权仍以 `OWNERSHIP.json` 为准。

## 立即派发：按 N01 → N05 串行完成

这些编号只是本说明的解阻顺序，不新增或伪造 manifest 业务节点。

### N01 → Codex 治理：补交接契约并裁定已知规划缺口

```text
工作根：D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent；保留现有模型。
先读 AGENTS.md、docs/agent-toolchain/00-common.md、12-project-completion-dispatch.md、TASK_MANIFEST、PHASE_GATES、GATE_EXECUTION_CONTRACT、OWNERSHIP、最新 P01-02 dsh 交接。
P01-02 的四项限定返工已经 READY_FOR_ZCODE；不要重启同一返工，不启动 P02。
AGENTS.md 所有权遗漏已由 Codex 修正，现为 A；完整测试 226 passed。不得把这个已解决问题再分配给 DSH。
本次目标是补齐 ARCH-0004 的 docs/workflow/README.md、02-ZCODE-PRECHECK.md、HANDOFF_CONTRACT.md：字段和路径以 scripts/gates.py 的实际读取规则及冻结 Gate 规则为准，说明角色、候选冻结、非空输入哈希、原始日志、失败退回、旧证据失效及生成顺序。不要降低执行器判定来适配旧记录。
核对已登记 ARCH-0003（UNSUPPORTED）、ARCH-0005（prompt/manifest 用例口径）、ARCH-0006（ScenarioBundle 归属）；对 ImportReceipt、Settings、MasterData、Job 等被引用具名类型逐项检查定义任务和合法承载文件，证据不足明确列未决。与下一阶段有关的缺口须在下发对应任务前有决定；不要猜测 DTO 或交给 P03/P04/P05 自造类型。
核对 P36-02：manifest owner 为 A，但 matrix.py/matrix_cache.py 位于 B 的 optimization 路径。按 A/B 拆分贡献及整合责任，或完成有依据的所有权治理决定，不能用任务标题覆盖路径所有权。
冻结输入变动前先列出精确文件白名单、影响的 Gate 和必要迁移；本次授权仅限上述治理缺口的最小修正。修改规划需改 catalog/render 等生成源并重生成、记录版本变化，不手改生成清单的任务状态。禁止整套重设计和业务功能实现。
只在核实环境缺口时准备相应环境任务卡；凭据/外部服务缺失明确记录，不把未运行的数据库或模型 smoke 写成通过。
运行规划检查器 --self-test，检查新文档本地链接和正反例说明；若改执行器，只做单列、有精确范围及测试的治理修复，交新的独立审查。
交付治理差异、当前候选、未决项、所影响的预验收；不执行 --record-g00，不写任何他人的交接/通过记录。下一执行者是独立 Codex 的 N02。
```

### N02 → Codex 独立审查：复核并恢复 G00

```text
工作根：D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent；保留现有模型。
你是与 N01 治理实施分开的独立审查会话。读取 N01 实际差异、Phase 00 三项任务、冻结契约、基线清单、最新 issue 和 Gate 执行规范。
独立重算 CONTRACT_FREEZE 的每项文件哈希和 BASELINE_INVENTORY 的旧资产哈希，核验 P00-01/02/03 文档与报告、DAG/追踪、阻断 issue、日志和命令。
当前仅确认旧 G00 的 issues/README.md 输入漂移；不要把重新记录等同于重新审查。N01 若改变冻结契约，先检查契约迁移、更新冻结审查事实，禁止复制旧 reviewer/日期制造新通过。
复核成立后先归档原冻结记录、G00.json 与原始日志的逐字节副本，再将 CONTRACT_FREEZE 的复核时间/身份记录为本次真实独立审查者（record_g00 会从此处读取 reviewer）；未变的契约哈希保留已核验值，禁止复制旧 reviewer 冒充当前审查。然后在实际根执行 python tools/ai_coding_plan/validate_plan.py --self-test --record-g00，保留实际退出码和日志。
用现行 scripts/gates.py 的前置 Gate 校验逐项复核新 G00，包括规划检查器 log_hash schema；不得只看 status。失败则交回 N01 的具体缺陷，不改 failed 为 passed。
仅处理 G00，不签 G01、不补写 ZCode 记录、不启动 P02。完成后通知调度者当前 G00 是否有效及被其变更失效的证据。下一执行者为 DSH 的 N03。
```

### N03 → DSH-A：刷新 Phase 01 自身交接，交审后停止

```text
工作根：D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent；先核对实际工作目录，保留现有模型。
读取 AGENTS.md、04-dsh-development.md、12-project-completion-dispatch.md、Phase 01 三项原任务和 N01/N02 的正式产物。G00 必须已按当前输入独立复核通过。
P01-02 四项限定返工已完成，本次不是再次实施同一返工；AGENTS.md 显式所有权已由 Codex 增补，记录实际作者，不把它写成 DSH 实施成果。
本次只核对 P01-01/02/03 的实现候选和更新你自己的交接证据。旧轮 evidence.json 与日志先逐字节归档；复算当前相关文件和新 G00 依赖哈希，保留首轮与返工历史。
按这三项任务卡实际重验必要命令，记录真实计数/退出码/原始日志。P01-02 重点是临时仓库隔离、自扰动、空输入拒绝、完整前置 Gate 校验；不要删除真实审查记录。若发现新实现缺陷，只提交具体缺陷和建议白名单，等待限定返工卡，不自行扩大范围。
可写范围仅为三项任务各自 docs/handoffs/<task>/dsh.md、artifacts/handoffs/<task>/dsh/ 新轮日志与证据、确需追加的本任务报告，以及 tmp/<本轮>/；不改源码、测试、锁、所有权、公共契约或规划。
DSH 实现交接只写真实 READY_FOR_ZCODE；不生成 precheck、review 或官方 Gate，不运行覆盖 artifacts/gates 的探针，不进入 P02。交给 ZCode 的 N04 后停止写候选。
```

### N04 → ZCode：独立重验 Phase 01 三项候选

```text
工作根：D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent；保留现有模型，不重复做无关插件安装。
先读 00-common.md、05-zcode-precheck.md、12-project-completion-dispatch.md、docs/workflow 的已审交接规则、Phase 01 三项任务及最新 DSH evidence。
你只做独立预验收，不修改实现。确认 N02 的 G00 有效，且 N03 已停写。重新计算当前候选，不沿用 DSH 旧 afbc7e4c…；P01-01 旧 scripts/gates.py hash 已过期。
先复核 P01-02 四项返工正反例及实际 96 例的收集/运行，再按原任务要求重验 P01-01 与 P01-03。核对 AGENTS.md 显式所有权、源码分层、锁与旧 demo 不变。完整回归的当前基线为 226 passed；数字须来自你实际执行结果，不照抄。
按已审 schema 分别写 P01-01、P01-02、P01-03 的 docs/handoffs/<task>/zcode.md 与 artifacts/handoffs/<task>/zcode/precheck.json。verified_input_hashes 必须非空、64 位 SHA-256、逐项与磁盘相符；至少包括 manifest、PHASE_GATES、任务 prompt、本任务 DSH evidence，并覆盖你实际检查的源码/测试/配置/契约/原始日志。
task_id、phase_gate=G01、reviewer 和 status 必须真实匹配；只有实际通过才写 Z_PRECHECK_PASSED。失败记录具体缺陷、复现、责任方，不填空哈希，不改 DSH evidence，不改官方 Gate，不启动下游。
三项通过并固定候选后交给独立 Codex 的 N05；如源文件再变动，按影响重新预验收。
```

### N05 → Codex 独立审查：最终审查并签收 G01

```text
工作根：D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent；保留现有模型。
你是独立最终审查者。先读 08-codex-final-review.md、12-project-completion-dispatch.md、Phase 01 三项 prompt、Gate 规范、N01/N02/N03/N04 的实际记录。参与当前被审实现/治理的会话不得声称独立；使用指定独立上下文。
独立复核 P01-02 四项修复和 P01-01/P01-03 当前产物，重算全部必需输入、前置 G00、三个 ZCode precheck 与原始日志的哈希。已确认的所有权修正应体现在新候选，禁止沿用旧 revision 或过期 precheck。
确认 G01 的任务命令、额外业务断言、真实依赖和退出码均满足要求；不能把 --check-only 退出 0 当成签收，不能把 226 个测试全绿替代 review 或 G00。
审查满足时按实际 schema 写 artifacts/gates/G01-codex-review.json：gate_id、当前 code_revision、真实 reviewer、approved/passed、非空且足够的 verified_input_hashes、实际复现日志和限制。输入集合不包含 review 自己或待生成 G01.json，避免自引用。
先逐字节归档旧 G01.json 及原始日志，再执行 uv run python scripts/gates.py --phase 01 --revision auto，保存实际日志/退出码。最终重核官方 G01.json 的 passed、输入/日志/依赖哈希和审查覆盖；失败立即停止并退回具体责任方，不手改状态。
确认有效 G01 后，只下发 P02-01；后续按本清单严格走任务依赖和阶段 Gate。G02–G39 的未注册业务断言覆盖由单独治理任务解决，不能扩大 DSH 的既定四项返工。
```

### 可同时交给 WorkBuddy：只准备草稿

```text
工作根：D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent；保留现有模型，使用现有免费额度。
读取 07-workbuddy-small-tasks.md 和最新交付；只在 tmp/workbuddy-dispatch/ 中整理 Phase 01 证据索引草稿，列 task、文件路径、原日志结果、当前/历史标识和缺失项。
核对每条事实的原始来源，不把旧日志当新候选实跑结果，不编写通过记录。禁止修改源码、规划、公共契约、DSH/ZCode/Codex 正式记录和 Gate。
交付可核对的草稿给 Codex/DSH 后停止。额度或能力不足就交已完成部分，不阻塞 N01–N05。
```

## 后续固定循环与失败退回

1. Codex 调度者选择最早依赖已满足的任务；读取任务 prompt 与 manifest 的实际 `deps` / `allowed_files` / `commands`，对照路径所有权。需要新增依赖、补接口或环境时先建立有范围的修复卡。
2. 对应 DSH-A 或 DSH-B 实现**一个**任务，跑必需验证，写自己的新轮交接，停写后交 ZCode。下面每项均有独立启动消息，不是一句“继续整个项目”。
3. ZCode 按本任务验证并写真实 precheck；失败回该任务主实现者的限定缺陷卡。Task 通过只允许同阶段满足依赖的下一个 Task，不自动放行下一 Phase。
4. 同阶段任务全部完成后停止所有该候选主写者，统一复算相关输入；检查早先 precheck 是否仍新鲜，对被影响记录重验。Codex 独立审查本阶段全部任务、前置 Gate 和业务断言覆盖，按实际 schema 生成 review，再实际运行并核验官方 Gate。
5. 当前 Gate 有效签收后才启动下一阶段。需要修正旧公共输入时按 F6 计算受影响 Gate 和下游失效集合，逐一重验；不把全局新 revision 当作所有旧 Gate 自动无效，也不以旧 passed 免除真实输入漂移。

限定返工消息：给原主实现者附 `task_id + 新轮次 + 当前候选 + 缺陷文件/位置 + 复现 + 预期行为 + 精确可写文件 + 必需验证 + 停止条件`，并引用原任务、`04-dsh-development.md`。返工不能写他人记录、吞错误、删用例或扩展到后续任务。

### 可并行范围

- **P06-01 / P06-02**：都依赖 G05；由两个获 B 委派的主写会话分区，接口冻结且真实写集合不交叉时并行。
- **P12-02 / P12-03**：先完成 P12-01 且 G11 有效，再分区实现运输与仓储仿真；两者完成并验收后执行 P12-04。
- **P25-01 / P25-02 / P25-03**：G24 有效后分区实现三类资源页；共享组件、路由、客户端、全局样式和锁由一个整合者持有，需要变更时串行。
- 无 Git 时使用明确独立写集合或受控副本/补丁，不虚构 worktree。候选未冻结时可做阅读与缺陷草稿；正式通过记录应绑定停写后的实际输入。
- WorkBuddy 的可丢弃草稿可与主任务并行；这不授权越过阶段 Gate，也不授权未列出的业务任务并行。

### 跨所有权与环境的特别派发

- P13-01：DSH-A 主写公共事件 DTO/后端及共同证据；DSH-B 只写 `packages/simulation/src/logistics_simulation/events.py`。先冻结事件接口，再由 A 主写者整合证据；不是两个会话同时重写公共 DTO。
- P36-02：原 manifest 的任务 owner=A，与 optimization 文件的 B 所有权存在冲突。开始前必须完成治理决定；推荐 B 写矩阵缓存实现，A 写基准/回归与整合报告。不能在未裁定时给 DSH-A 整包源码权限。
- G03/G05/G16/G34/G37 使用真实隔离 PostgreSQL；提前确认测试库、迁移及清理边界。G07/G09/G10/G15 使用真实 OR-Tools 与独立校验；G12 使用真实 SimPy。G18/G23 的真实供应商 smoke 与离线替身结果分别记录；无凭据不签通过。前端按任务使用真实 API、组件网络测试及阶段要求的浏览器验证。
- Python/前端依赖清单和锁的增补由明确任务承担，公共锁只有一个写者；新增依赖对旧 Gate 输入造成漂移时必须重验受影响证据。不能借环境准备擅自修改用户全局配置、升级 harness 或购买服务。

## 完成条件

P39-01 提供真实可安装候选、完整性清单/SBOM/锁/迁移及干净安装证据。P39-02 的 DSH 交付是 ReleaseAcceptance 待审候选和复现索引；官方 G39 仍由 ZCode 预验收后，Codex 独立最终审查签收。不得把最终 Gate 尚未生成作为任务自测试的循环前提。

项目完成以有效 G00–G39 链、五场景 A/B/C1/C2/C3 的真实端到端证据、固定发布候选、10 次性能基准、备份恢复/安全/审计、开发与运维文档为准。`PHASE_GATES.md` 的数值要求逐项落实；任务数量、截图、聊天报告和一次全绿单测不能代替。外部发布按实际用户授权另执行，不与本地候选签收混为同一事实。

## 完整任务与消息索引

下方由当前 manifest 生成：每个业务任务都有 DSH 启动消息和 ZCode 预验收消息，每阶段都有 Codex review/Gate 消息。接收者须实际读取原始完整 prompt，而不是仅依据表中标题实现。消息是未来条件式派发文本，只有前置有效才发送；未设置模型或伪造完成状态。

<!-- GENERATED DISPATCH INDEX -->

| 立即顺序 | 接收者与目标 | 可直接粘贴的消息 |
| --- | --- | --- |
| N01 | odex 治理：补交接契约并裁定已知规划缺口 | [完整消息](../../artifacts/dispatch/2026-10-01/completion/messages/now/N01.md) |
| N02 | odex 独立审查：复核并恢复 G00 | [完整消息](../../artifacts/dispatch/2026-10-01/completion/messages/now/N02.md) |
| N03 | SH-A：刷新 Phase 01 自身交接，交审后停止 | [完整消息](../../artifacts/dispatch/2026-10-01/completion/messages/now/N03.md) |
| N04 | Code：独立重验 Phase 01 三项候选 | [完整消息](../../artifacts/dispatch/2026-10-01/completion/messages/now/N04.md) |
| N05 | odex 独立审查：最终审查并签收 G01 | [完整消息](../../artifacts/dispatch/2026-10-01/completion/messages/now/N05.md) |
| 可选并行 | WorkBuddy：证据索引草稿 | [完整消息](../../artifacts/dispatch/2026-10-01/completion/messages/workbuddy/phase01-index.md) |

后续可选 WorkBuddy 草稿（均不成为主链依赖）：

| 启动条件 | 草稿范围 | 消息 |
| --- | --- | --- |
| G24 有效且客户端/页面状态接口已固定 | 整理 loading/empty/error/conflict/cancelled/TIMEOUT 的中文页面文案与标签草稿 | [给 WorkBuddy](../../artifacts/dispatch/2026-10-01/completion/messages/workbuddy/frontend-copy.md) |
| G35 有效且五场景原始证据已归档 | 整理 A/B/C1/C2/C3 的输入、求解、校验、事件、版本差异、指标、回放文件索引草稿 | [给 WorkBuddy](../../artifacts/dispatch/2026-10-01/completion/messages/workbuddy/demo-evidence-index.md) |
| G37 有效且实际运行/恢复/模型配置步骤可读取 | 整理文档格式、术语与操作步骤索引草稿，供 P38 主实现者核对采用 | [给 WorkBuddy](../../artifacts/dispatch/2026-10-01/completion/messages/workbuddy/operator-doc-copy.md) |
| P39-01 候选已经固定 | 整理发布说明和已知限制排版草稿，保持来源与实际能力边界 | [给 WorkBuddy](../../artifacts/dispatch/2026-10-01/completion/messages/workbuddy/release-note-copy.md) |

### Phase 02 · Domain Model → G02

前置阶段 Gate：G01；阶段额外验收：32实体及辅助记录可表达，非法状态/单位/额外字段拒绝；Schema确定导出；domain无框架依赖。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P02-01 实现领域 ID、单位与唯一状态枚举](../../docs/prompts/02-domain/P02-01-primitives-and-states.md) | DSH-A | G01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P02-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P02-01.md) |
| [P02-02 实现订单、货物与运仓资源领域模型](../../docs/prompts/02-domain/P02-02-master-entities.md) | DSH-A | G01, P02-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P02-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P02-02.md) |
| [P02-03 实现任务、版本与优化结果领域模型](../../docs/prompts/02-domain/P02-03-planning-entities.md) | DSH-A | G01, P02-02 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P02-03.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P02-03.md) |
| [P02-04 实现运行记录模型与 Schema 导出](../../docs/prompts/02-domain/P02-04-runtime-contract-export.md) | DSH-A | G01, P02-03 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P02-04.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P02-04.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G02 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G02.md)；有效签收后才能继续。

### Phase 03 · PostgreSQL Schema + Migration → G03

前置阶段 Gate：G02；阶段额外验收：真实PostgreSQL迁移、回滚与FK通过；一致快照；最后一份资源并发提交恰一成功；事务失败无半版本。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P03-01 创建主数据与资源迁移](../../docs/prompts/03-database/P03-01-resource-schema.md) | DSH-A | G02 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P03-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P03-01.md) |
| [P03-02 创建不可变计划、运行与审计迁移](../../docs/prompts/03-database/P03-02-planning-schema.md) | DSH-A | G02, P03-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P03-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P03-02.md) |
| [P03-03 实现快照读取与事务工作单元](../../docs/prompts/03-database/P03-03-repositories-and-snapshot.md) | DSH-A | G02, P03-02 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P03-03.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P03-03.md) |
| [P03-04 实现版本 CAS、资源预留与幂等存储](../../docs/prompts/03-database/P03-04-atomic-version-store.md) | DSH-A | G02, P03-03 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P03-04.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P03-04.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G03 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G03.md)；有效签收后才能继续。

### Phase 04 · Seed / Synthetic Dataset → G04

前置阶段 Gate：G03；阶段额外验收：T1/W1/I1/M1数据hash可复现；反例各有原因；同种子二次导入不重复，不清空既有库。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P04-01 生成可手算的合成场景与反例数据](../../docs/prompts/01-foundation/P04-01-canonical-fixtures.md) | DSH-A | G03 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P04-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P04-01.md) |
| [P04-02 实现可重复执行的数据库种子导入](../../docs/prompts/01-foundation/P04-02-database-seed.md) | DSH-A | G03, P04-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P04-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P04-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G04 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G04.md)；有效签收后才能继续。

### Phase 05 · FastAPI 基础服务 → G05

前置阶段 Gate：G04；阶段额外验收：API认证、错误、分页、revision与持久Job可验收；杀worker后租约可重领；无长求解阻塞请求。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P05-01 建立 FastAPI 组合根、错误协议与基础鉴权](../../docs/prompts/04-api/P05-01-api-composition.md) | DSH-A | G04 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P05-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P05-01.md) |
| [P05-02 实现主数据分页读写服务与资源日历 API](../../docs/prompts/04-api/P05-02-master-data-services.md) | DSH-A | G04, P05-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P05-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P05-02.md) |
| [P05-03 实现作业租约、超时取消与受限 worker](../../docs/prompts/04-api/P05-03-durable-jobs.md) | DSH-A | G04, P05-02 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P05-03.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P05-03.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G05 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G05.md)；有效签收后才能继续。

### Phase 06 · Transport Optimization Domain → G06

前置阶段 Gate：G05；阶段额外验收：运输typed输入/矩阵节点顺序/版本明确；不可达与0区分；天气倍率100→150秒可手算。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P06-01 实现运输请求、结果和 Solver Protocol](../../docs/prompts/05-transport-solver/P06-01-transport-contract.md) | DSH-B | G05 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P06-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P06-01.md) |
| [P06-02 实现版本化道路距离和时间矩阵提供器](../../docs/prompts/05-transport-solver/P06-02-distance-matrix.md) | DSH-B | G05 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P06-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P06-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G06 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G06.md)；有效签收后才能继续。

### Phase 07 · Transport Solver → G07

前置阶段 Gate：G06；阶段额外验收：真实OR-Tools T1=9000m/1400分；容量/提送/硬窗/温区/状态各有反例；独立校验通过，无假成功。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P07-01 实现多起终点车辆路径基本求解](../../docs/prompts/05-transport-solver/P07-01-vrp-base.md) | DSH-B | G06 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P07-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P07-01.md) |
| [P07-02 实现重量、容积和提送货载荷约束](../../docs/prompts/05-transport-solver/P07-02-capacity-and-pickup.md) | DSH-B | G06, P07-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P07-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P07-02.md) |
| [P07-03 实现服务时间、等待、班次与硬时间窗](../../docs/prompts/05-transport-solver/P07-03-time-windows.md) | DSH-B | G06, P07-02 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P07-03.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P07-03.md) |
| [P07-04 实现温区、货物类型与车辆允许集合](../../docs/prompts/05-transport-solver/P07-04-temperature-and-cargo.md) | DSH-B | G06, P07-03 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P07-04.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P07-04.md) |
| [P07-05 实现可解释费用与可选订单目标函数](../../docs/prompts/05-transport-solver/P07-05-objective-function.md) | DSH-B | G06, P07-04 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P07-05.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P07-05.md) |
| [P07-06 实现运输结果提取、状态映射和独立重算](../../docs/prompts/05-transport-solver/P07-06-result-status-validation.md) | DSH-B | G06, P07-05 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P07-06.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P07-06.md) |
| [P07-07 装配运输 Solver 并验证数值与预算边界](../../docs/prompts/05-transport-solver/P07-07-transport-adapter.md) | DSH-B | G06, P07-06 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P07-07.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P07-07.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G07 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G07.md)；有效签收后才能继续。

### Phase 08 · Warehouse Optimization Domain → G08

前置阶段 Gate：G07；阶段额外验收：五类仓储作业、所有资源与库存/交接具名；DAG环拒绝；初始库存与存储区间契约可验证。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P08-01 实现仓储任务与资源日历协议](../../docs/prompts/06-warehouse-solver/P08-01-warehouse-contract.md) | DSH-A | G07 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P08-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P08-01.md) |
| [P08-02 实现库存占用和仓运交接约束模型](../../docs/prompts/06-warehouse-solver/P08-02-inventory-and-handoffs.md) | DSH-A | G07, P08-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P08-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P08-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G08 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G08.md)；有效签收后才能继续。

### Phase 09 · Warehouse Scheduler → G09

前置阶段 Gate：G08；阶段额外验收：真实CP-SAT W1=25秒；工序/资源/库存/setup反例通过；UNKNOWN不当INFEASIBLE；返回资源时间轴。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P09-01 实现仓储区间、互斥资源与任务依赖](../../docs/prompts/06-warehouse-solver/P09-01-intervals-precedence.md) | DSH-A | G08 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P09-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P09-01.md) |
| [P09-02 实现人员、设备和温区容量限制](../../docs/prompts/06-warehouse-solver/P09-02-cumulative-resources.md) | DSH-A | G08, P09-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P09-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P09-02.md) |
| [P09-03 实现库位库存区间和冷链容量约束](../../docs/prompts/06-warehouse-solver/P09-03-storage-capacity.md) | DSH-A | G08, P09-02 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P09-03.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P09-03.md) |
| [P09-04 实现清洁及月台、温区、分拣切换时间](../../docs/prompts/06-warehouse-solver/P09-04-sequence-setup.md) | DSH-A | G08, P09-03 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P09-04.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P09-04.md) |
| [P09-05 装配仓储目标、结果提取与独立校验](../../docs/prompts/06-warehouse-solver/P09-05-warehouse-result.md) | DSH-A | G08, P09-04 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P09-05.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P09-05.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G09 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G09.md)；有效签收后才能继续。

### Phase 10 · Constraint Validator → G10

前置阶段 Gate：G09；阶段额外验收：所有required硬约束有checked或unsupported记录；J1联合冲突检出；每条硬约束单点破坏反例检出。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P10-01 实现统一校验报告与约束覆盖注册表](../../docs/prompts/06-warehouse-solver/P10-01-validator-protocol.md) | DSH-A | G09 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P10-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P10-01.md) |
| [P10-02 实现跨仓运链、库存和资源完整校验](../../docs/prompts/06-warehouse-solver/P10-02-joint-validator.md) | DSH-A | G09, P10-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P10-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P10-02.md) |
| [P10-03 建立独立硬约束反例与小规模 oracle 套件](../../docs/prompts/06-warehouse-solver/P10-03-validator-adversarial-suite.md) | DSH-A | G09, P10-02 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P10-03.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P10-03.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G10 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G10.md)；有效签收后才能继续。

### Phase 11 · Simulation Domain → G11

前置阶段 Gate：G10；阶段额外验收：仿真状态/事件/RNG/快照类型冻结；非法执行状态拒绝；计划和真实执行事实分离。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P11-01 实现仿真场景、状态、快照与随机源契约](../../docs/prompts/07-simulation/P11-01-simulation-contract.md) | DSH-B | G10 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P11-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P11-01.md) |
| [P11-02 实现订单、车辆和仓库执行状态转换](../../docs/prompts/07-simulation/P11-02-execution-state-machine.md) | DSH-B | G10, P11-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P11-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P11-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G11 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G11.md)；有效签收后才能继续。

### Phase 12 · SimPy Digital Twin → G12

前置阶段 Gate：G11；阶段额外验收：真实SimPy T1终态1020秒；t400恢复一致；同秒事件稳定排序；分支隔离、资源无死锁、取消无伪完成。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P12-01 实现 SimPy 时间推进与稳定事件调度内核](../../docs/prompts/07-simulation/P12-01-simpy-kernel.md) | DSH-B | G11 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P12-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P12-01.md) |
| [P12-02 实现车辆移动、服务与订单交付过程](../../docs/prompts/07-simulation/P12-02-transport-execution.md) | DSH-B | G11, P12-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P12-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P12-02.md) |
| [P12-03 实现仓储资源争用、作业与库存演化](../../docs/prompts/07-simulation/P12-03-warehouse-execution.md) | DSH-B | G11, P12-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P12-03.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P12-03.md) |
| [P12-04 实现快照恢复和反事实分支隔离](../../docs/prompts/07-simulation/P12-04-snapshot-replay.md) | DSH-B | G11, P12-02, P12-03 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P12-04.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P12-04.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G12 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G12.md)；有效签收后才能继续。

### Phase 13 · Event Engine → G13

前置阶段 Gate：G12；阶段额外验收：十类异常payload全覆盖；重复去重、乱序/迟到有明确处理；事件与outbox原子保存。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P13-01 实现十类异常事件的校验、去重与排序](../../docs/prompts/07-simulation/P13-01-event-ingestion.md) | DSH-A 主写 / DSH-B 按文件贡献 | G12 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P13-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P13-01.md) |
| [P13-02 实现事件注入服务及持久化分发](../../docs/prompts/07-simulation/P13-02-event-api-and-outbox.md) | DSH-A | G12, P13-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P13-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P13-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G13 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G13.md)；有效签收后才能继续。

### Phase 14 · Exception Impact Analyzer → G14

前置阶段 Gate：G13；阶段额外验收：I1闭包只有T1/T2；T3冻结；在途起点和剩余载荷真实；已执行事实不可改写。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P14-01 实现异常影响依赖图与最小闭包](../../docs/prompts/08-exception/P14-01-impact-graph.md) | DSH-A | G13 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P14-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P14-01.md) |
| [P14-02 实现不可逆事实、在途起点与重排边界提取](../../docs/prompts/08-exception/P14-02-execution-freeze.md) | DSH-A | G13, P14-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P14-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P14-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G14 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G14.md)；有效签收后才能继续。

### Phase 15 · Local Rescheduling Engine → G15

前置阶段 Gate：G14；阶段额外验收：局部→扩大→全局剩余共享预算；救援无瞬移；完整合并方案重验；六项diff正确；失败给诊断/暂停建议。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P15-01 实现局部候选策略与救援交接任务生成](../../docs/prompts/08-exception/P15-01-candidate-policies.md) | DSH-A | G14 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P15-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P15-01.md) |
| [P15-02 实现冻结边界下的局部重新求解](../../docs/prompts/08-exception/P15-02-local-solve.md) | DSH-A | G14, P15-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P15-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P15-02.md) |
| [P15-03 实现局部扩展与全局剩余任务降级策略](../../docs/prompts/08-exception/P15-03-bounded-escalation.md) | DSH-A | G14, P15-02 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P15-03.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P15-03.md) |
| [P15-04 实现版本差异与候选排序](../../docs/prompts/08-exception/P15-04-version-diff.md) | DSH-A | G14, P15-03 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P15-04.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P15-04.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G15 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G15.md)；有效签收后才能继续。

### Phase 16 · Optimization API → G16

前置阶段 Gate：G15；阶段额外验收：运输/仓储/联合/重排/仿真API真实连通；J1反馈消除交接冲突；并发/过期确认409；V1不覆盖。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P16-01 实现运输、仓储和重排作业 API](../../docs/prompts/04-api/P16-01-optimization-job-api.md) | DSH-A | G15 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P16-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P16-01.md) |
| [P16-02 实现有界仓运窗口反馈协调服务](../../docs/prompts/04-api/P16-02-joint-planning-service.md) | DSH-A | G15, P16-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P16-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P16-02.md) |
| [P16-03 实现重新校验后的版本确认服务](../../docs/prompts/04-api/P16-03-validated-commit-api.md) | DSH-A | G15, P16-02 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P16-03.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P16-03.md) |
| [P16-04 实现仿真控制、版本对比与结果查询 API](../../docs/prompts/04-api/P16-04-simulation-query-api.md) | DSH-A | G15, P16-03 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P16-04.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P16-04.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G16 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G16.md)；有效签收后才能继续。

### Phase 17 · Agent Tool Protocol → G17

前置阶段 Gate：G16；阶段额外验收：白名单Tool typed args/role/scope/deadline/幂等生效；不直写数据库；未确认commit被拒绝。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P17-01 实现 Agent 标准工具注册、权限与参数协议](../../docs/prompts/09-agents/P17-01-tool-schemas.md) | DSH-A | G16 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P17-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P17-01.md) |
| [P17-02 实现工具到业务服务的唯一适配层](../../docs/prompts/09-agents/P17-02-business-tools.md) | DSH-A | G16, P17-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P17-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P17-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G17 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G17.md)；有效签收后才能继续。

### Phase 18 · LLM Provider Abstraction → G18

前置阶段 Gate：G17；阶段额外验收：真实供应商适配契约smoke有脱敏证据；schema/429/超时/预算/无密钥降级通过；fake不能冒充真实smoke。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P18-01 实现模型供应商抽象与结构化响应边界](../../docs/prompts/09-agents/P18-01-llm-provider.md) | DSH-A | G17 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P18-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P18-01.md) |
| [P18-02 实现模型预算、重试、脱敏与故障降级](../../docs/prompts/09-agents/P18-02-llm-resilience.md) | DSH-A | G17, P18-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P18-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P18-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G18 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G18.md)；有效签收后才能继续。

### Phase 19 · Coordinator Agent → G19

前置阶段 Gate：G18；阶段额外验收：意图抽取保留原文/实体证据；缺字段先澄清；有界状态机在预算耗尽停止，不自造ID。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P19-01 实现 Coordinator 意图及约束抽取](../../docs/prompts/09-agents/P19-01-intent-extraction.md) | DSH-A | G18 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P19-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P19-01.md) |
| [P19-02 实现 Coordinator 任务分解与有界运行状态机](../../docs/prompts/09-agents/P19-02-coordinator-state-machine.md) | DSH-A | G18, P19-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P19-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P19-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G19 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G19.md)；有效签收后才能继续。

### Phase 20 · Transport Agent → G20

前置阶段 Gate：G19；阶段额外验收：TransportAgent仅通过工具取得候选；无解不造路线；T1数值解释与证据一致。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P20-01 实现 TransportAgent 求解工具工作流](../../docs/prompts/09-agents/P20-01-transport-agent-tools.md) | DSH-A | G19 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P20-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P20-01.md) |
| [P20-02 实现有证据的运输结果解释](../../docs/prompts/09-agents/P20-02-transport-explanation.md) | DSH-A | G19, P20-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P20-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P20-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G20 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G20.md)；有效签收后才能继续。

### Phase 21 · Warehouse Agent → G21

前置阶段 Gate：G20；阶段额外验收：WarehouseAgent报价非预留且会过期；资源瓶颈解释引用真实任务/诊断，不能杜撰利用率。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P21-01 实现 WarehouseAgent 排程与窗口报价工作流](../../docs/prompts/09-agents/P21-01-warehouse-agent-tools.md) | DSH-A | G20 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P21-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P21-01.md) |
| [P21-02 实现仓储甘特与资源瓶颈解释数据](../../docs/prompts/09-agents/P21-02-warehouse-explanation.md) | DSH-A | G20, P21-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P21-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P21-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G21 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G21.md)；有效签收后才能继续。

### Phase 22 · Exception Agent → G22

前置阶段 Gate：G21；阶段额外验收：ExceptionAgent九步有完整记录；缺救援数据manual_required；解释区分建议与已确认版本。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P22-01 实现 ExceptionAgent 九步处置工作流](../../docs/prompts/09-agents/P22-01-exception-agent-tools.md) | DSH-A | G21 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P22-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P22-01.md) |
| [P22-02 实现异常处置链和版本差异解释](../../docs/prompts/09-agents/P22-02-exception-explanation.md) | DSH-A | G21, P22-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P22-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P22-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G22 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G22.md)；有效签收后才能继续。

### Phase 23 · Agent Orchestration → G23

前置阶段 Gate：G22；阶段额外验收：四角色有界协调、父取消传播、工具注入/越权拒绝；确认令牌绑定对象/actor/revision并防重放。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P23-01 实现四角色路由、取消与有界协调](../../docs/prompts/09-agents/P23-01-agent-orchestration.md) | DSH-A | G22 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P23-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P23-01.md) |
| [P23-02 实现 Agent 会话 API 与攻击性输入验收](../../docs/prompts/09-agents/P23-02-agent-api-safety.md) | DSH-A | G22, P23-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P23-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P23-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G23 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G23.md)；有效签收后才能继续。

### Phase 24 · React Application Shell → G24

前置阶段 Gate：G23；阶段额外验收：11导航可达；375px可用；loading/empty/error分开；OpenAPI生成类型无漂移。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P24-01 建立 React 应用壳、路由与统一状态展示](../../docs/prompts/10-frontend/P24-01-react-shell.md) | DSH-A | G23 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P24-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P24-01.md) |
| [P24-02 建立 OpenAPI 生成客户端和数据请求层](../../docs/prompts/10-frontend/P24-02-generated-api-client.md) | DSH-A | G23, P24-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P24-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P24-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G24 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G24.md)；有效签收后才能继续。

### Phase 25 · Orders / Vehicles / Warehouses UI → G25

前置阶段 Gate：G24；阶段额外验收：订单/车辆/仓库资源页使用真实API；If-Match冲突可见；执行中变更走事件；无业务规则复制。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P25-01 实现订单查询、编辑和取消事件入口](../../docs/prompts/10-frontend/P25-01-orders-ui.md) | DSH-A | G24 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P25-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P25-01.md) |
| [P25-02 实现车辆、司机和可用日历页面](../../docs/prompts/10-frontend/P25-02-vehicles-ui.md) | DSH-A | G24 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P25-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P25-02.md) |
| [P25-03 实现仓库、温区、库位及作业资源页面](../../docs/prompts/10-frontend/P25-03-warehouses-ui.md) | DSH-A | G24 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P25-03.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P25-03.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G25 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G25.md)；有效签收后才能继续。

### Phase 26 · Transport Scheduling UI → G26

前置阶段 Gate：G25；阶段额外验收：运输请求/Job/取消/诊断/路线表/费用/确认可操作；T1数值一致，TIMEOUT不显示成功。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P26-01 实现运输请求、作业进度与不可行诊断页面](../../docs/prompts/10-frontend/P26-01-transport-request-ui.md) | DSH-A | G25 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P26-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P26-01.md) |
| [P26-02 实现路线、逐站执行表和候选确认视图](../../docs/prompts/10-frontend/P26-02-transport-plan-ui.md) | DSH-A | G25, P26-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P26-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P26-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G26 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G26.md)；有效签收后才能继续。

### Phase 27 · Warehouse Scheduling UI → G27

前置阶段 Gate：G26；阶段额外验收：仓储甘特显示任务/setup/日历，J1交接冲突可见；只能统一确认有效联合候选。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P27-01 实现仓储请求和资源甘特图](../../docs/prompts/10-frontend/P27-01-warehouse-gantt-ui.md) | DSH-A | G26 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P27-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P27-01.md) |
| [P27-02 实现仓运交接与联合方案对照视图](../../docs/prompts/10-frontend/P27-02-joint-handoff-ui.md) | DSH-A | G26, P27-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P27-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P27-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G27 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G27.md)；有效签收后才能继续。

### Phase 28 · Digital Twin UI → G28

前置阶段 Gate：G27；阶段额外验收：仿真暂停/步进/注入/快照/分支比较可操作；正式状态不污染，3D不是必要依赖。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P28-01 实现数字孪生场景、暂停、步进和事件注入](../../docs/prompts/10-frontend/P28-01-simulation-controls-ui.md) | DSH-A | G27 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P28-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P28-01.md) |
| [P28-02 实现快照回放和反事实分支对比](../../docs/prompts/10-frontend/P28-02-replay-comparison-ui.md) | DSH-A | G27, P28-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P28-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P28-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G28 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G28.md)；有效签收后才能继续。

### Phase 29 · Exception Center UI → G29

前置阶段 Gate：G28；阶段额外验收：异常九步、原因路径、六项diff可检查；原方案/候选/新版本区分，失效候选不可确认。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P29-01 实现异常列表、影响图和处置流水](../../docs/prompts/10-frontend/P29-01-exception-center-ui.md) | DSH-A | G28 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P29-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P29-01.md) |
| [P29-02 实现候选比较、版本差异和重排确认](../../docs/prompts/10-frontend/P29-02-reschedule-diff-ui.md) | DSH-A | G28, P29-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P29-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P29-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G29 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G29.md)；有效签收后才能继续。

### Phase 30 · Agent Chat UI → G30

前置阶段 Gate：G29；阶段额外验收：聊天澄清/工具状态/取消/刷新恢复可用；建议卡数值有证据，脚本注入不执行，明确点击才确认。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P30-01 实现聊天、澄清和工具执行状态页面](../../docs/prompts/10-frontend/P30-01-agent-chat-ui.md) | DSH-A | G29 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P30-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P30-01.md) |
| [P30-02 实现有证据的建议确认与风险提示](../../docs/prompts/10-frontend/P30-02-agent-confirmation-ui.md) | DSH-A | G29, P30-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P30-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P30-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G30 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G30.md)；有效签收后才能继续。

### Phase 31 · WebSocket Real-time System → G31

前置阶段 Gate：G30；阶段额外验收：WS授权/补发/重复去重/过期cursor重取/慢客户端限额通过；断线轮询继续获得正确终态。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P31-01 实现带游标的实时事件与断线补偿服务](../../docs/prompts/10-frontend/P31-01-websocket-events.md) | DSH-A | G30 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P31-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P31-01.md) |
| [P31-02 实现前端实时订阅与轮询回退](../../docs/prompts/10-frontend/P31-02-frontend-realtime.md) | DSH-A | G30, P31-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P31-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P31-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G31 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G31.md)；有效签收后才能继续。

### Phase 32 · Metrics / Evaluation → G32

前置阶段 Gate：G31；阶段额外验收：14指标逐项M1及边界通过；source/窗口/定义明确；Dashboard与Metrics不伪造null为0。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P32-01 实现14项调度指标与统一统计口径](../../docs/prompts/11-evaluation/P32-01-metric-calculators.md) | DSH-A | G31 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P32-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P32-01.md) |
| [P32-02 实现指标持久化、版本比较与 Dashboard 聚合](../../docs/prompts/11-evaluation/P32-02-metrics-api.md) | DSH-A | G31, P32-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P32-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P32-02.md) |
| [P32-03 实现 Dashboard 与 Metrics 图表页面](../../docs/prompts/11-evaluation/P32-03-metrics-dashboard-ui.md) | DSH-A | G31, P32-02 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P32-03.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P32-03.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G32 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G32.md)；有效签收后才能继续。

### Phase 33 · Experiment Framework → G33

前置阶段 Gate：G32；阶段额外验收：至少10次配对seed、同预算实验；规则/solver/Agent与local/global对照；失败样本保留；实验UI/导出真实。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P33-01 实现对照实验、配对随机种子与结果留档](../../docs/prompts/11-evaluation/P33-01-experiment-runner.md) | DSH-A | G32 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P33-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P33-01.md) |
| [P33-02 实现实验创建、进度、结果与导出工作台](../../docs/prompts/11-evaluation/P33-02-experiments-api-ui.md) | DSH-A | G32, P33-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P33-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P33-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G33 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G33.md)；有效签收后才能继续。

### Phase 34 · End-to-End Integration → G34

前置阶段 Gate：G33；阶段额外验收：真实PostgreSQL+OR-Tools+SimPy+浏览器完整闭环；worker崩溃/陈旧提交/并发冲突/模型断线可恢复。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P34-01 建立真实数据库运输请求到确认的端到端验收](../../docs/prompts/12-integration/P34-01-transport-e2e.md) | DSH-A | G33 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P34-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P34-01.md) |
| [P34-02 建立仓运联合与异常重排的完整端到端验收](../../docs/prompts/12-integration/P34-02-joint-exception-e2e.md) | DSH-A | G33, P34-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P34-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P34-02.md) |
| [P34-03 建立崩溃、并发、模型断线与陈旧提交验收](../../docs/prompts/12-integration/P34-03-failure-recovery-e2e.md) | DSH-A | G33, P34-02 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P34-03.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P34-03.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G34 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G34.md)；有效签收后才能继续。

### Phase 35 · Demo Scenario → G35

前置阶段 Gate：G34；阶段额外验收：A/B/C1/C2/C3五演示均有输入hash、实际解、硬校验、事件、版本diff、指标和回放证据；重复可复现。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P35-01 交付 Scenario A 正常冷链运输演示](../../docs/prompts/12-integration/P35-01-demo-normal.md) | DSH-A | G34 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P35-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P35-01.md) |
| [P35-02 交付 Scenario B 仓储和运输联合演示](../../docs/prompts/12-integration/P35-02-demo-joint.md) | DSH-A | G34, P35-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P35-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P35-02.md) |
| [P35-03 交付 Scenario C1 车辆故障局部重排演示](../../docs/prompts/12-integration/P35-03-demo-vehicle-failure.md) | DSH-A | G34, P35-02 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P35-03.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P35-03.md) |
| [P35-04 交付 Scenario C2 订单取消局部重排演示](../../docs/prompts/12-integration/P35-04-demo-order-cancel.md) | DSH-A | G34, P35-03 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P35-04.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P35-04.md) |
| [P35-05 交付 Scenario C3 天气变化与一键复现演示包](../../docs/prompts/12-integration/P35-05-demo-weather.md) | DSH-A | G34, P35-04 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P35-05.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P35-05.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G35 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G35.md)；有效签收后才能继续。

### Phase 36 · Performance Optimization → G36

前置阶段 Gate：G35；阶段额外验收：参考机10次基准齐备；20单4车2仓HTTP目标与求解预算按Master验收；缓存64MiB有界且换版本失效，所有正确性回归通过。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P36-01 建立可重复的容量、耗时和内存基准](../../docs/prompts/12-integration/P36-01-benchmark-harness.md) | DSH-A | G35 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P36-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P36-01.md) |
| [P36-02 实现有内存上限的版本化矩阵缓存并复验](../../docs/prompts/12-integration/P36-02-bounded-performance-fix.md) | A/B 治理裁定后分区；DSH 主写者整合 | G35, P36-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P36-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P36-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G36 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G36.md)；有效签收后才能继续。

### Phase 37 · Security / Audit / Observability → G37

前置阶段 Gate：G36；阶段额外验收：访问控制/注入/依赖/密钥负例无未处置阻断项；trace可追V2；备份恢复到隔离库保持历史与账本。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P37-01 验证并修复访问控制、输入边界和依赖安全](../../docs/prompts/12-integration/P37-01-security-boundary.md) | DSH-A | G36 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P37-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P37-01.md) |
| [P37-02 实现全链追踪、指标端点和审计可检索性](../../docs/prompts/12-integration/P37-02-observability-audit.md) | DSH-A | G36, P37-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P37-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P37-02.md) |
| [P37-03 验证数据库备份恢复、迁移回滚与作业恢复](../../docs/prompts/12-integration/P37-03-backup-and-recovery.md) | DSH-A | G36, P37-02 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P37-03.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P37-03.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G37 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G37.md)；有效签收后才能继续。

### Phase 38 · Documentation → G38

前置阶段 Gate：G37；阶段额外验收：开发/使用/运维文档对真实实现，无夸大能力；干净环境命令可执行，缺模型密钥降级有明确指南。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P38-01 交付与实际实现一致的架构、API和算法文档](../../docs/prompts/13-release/P38-01-developer-docs.md) | DSH-A | G37 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P38-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P38-01.md) |
| [P38-02 交付演示、异常处置、运维和模型配置手册](../../docs/prompts/13-release/P38-02-operator-docs.md) | DSH-A | G37, P38-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P38-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P38-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G38 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G38.md)；有效签收后才能继续。

### Phase 39 · Release → G39

前置阶段 Gate：G38；阶段额外验收：G00–G38证据未失效；发布候选hash/SBOM/锁/迁移完整；干净安装五演示通过；没有凭据，限制与恢复点明确。

| 任务与原始完整 prompt | 主实现者 | 必需前置 | 实现启动消息 | ZCode 独立预验收消息 |
| --- | --- | --- | --- | --- |
| [P39-01 生成可安装发布候选及完整性清单](../../docs/prompts/13-release/P39-01-release-candidate.md) | DSH-A | G38 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P39-01.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P39-01.md) |
| [P39-02 签收发布 Gate 与复现证据索引](../../docs/prompts/13-release/P39-02-release-gate.md) | DSH-A | G38, P39-01 | [给实现者](../../artifacts/dispatch/2026-10-01/completion/messages/dsh/P39-02.md) | [给 ZCode](../../artifacts/dispatch/2026-10-01/completion/messages/zcode/P39-02.md) |

全部本阶段任务已验收且候选冻结后，发给独立 Codex：[完整 G39 review/Gate 消息](../../artifacts/dispatch/2026-10-01/completion/messages/codex/G39.md)；有效签收后才能继续。

