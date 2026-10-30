# 项目执行规则

以当前代码、配置、实跑日志和可复算哈希为事实依据。区分已确认事实、推断与未验证项；证据不足时明确说明。输出先给结论和必要证据。

## 工作根与事实来源

- 本文件约束 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent` 这一受检副本。另一目录 `D:\Agent\Codex\IntelligentLogisticsDispatchingAgent` 使用不同计划和证据；投送前核对 agent 实际工作目录，不符则停止，不能混用 Gate/任务状态。

- 正式工程根是本文件所在目录；实现位于 `apps/`、`packages/`、`scripts/`、`tests/`。`demo/`、`demos/` 是只读历史资产，禁止修改或作为正式实现的导入来源。
- 开始前读取 `AI-CODING-PLAN.md`、`docs/plan/TASK_MANIFEST.json`、`docs/plan/PHASE_GATES.md`、`OWNERSHIP.json`、当前任务提示词和最新交接。manifest 的 `planned` / `not_run` 是规划初始值，不是实时进度。
- Gate 状态必须同时核验原始记录、输入及日志哈希、依赖证据和实际测试；文件存在、编号较大、记录写着 passed 均不足以证明通过。`--check-only` 退出 0 也不能单独证明已签收，必须确认官方记录存在且有效。
- 当前目录未建立 Git 仓库；执行时重新核对。无 Git 使用相关文件清单及内容哈希，不虚构提交、分支、PR 或 worktree。

## 前端所有权

- 唯一正式前端是 `apps/frontend`。前端代码（`apps/frontend/**`）**只能由 codexyuyu 修改**；其他 agent 不得改动、替换或新增前端目录，需要前端变更时提交说明交由 codexyuyu 处理。
- 仓库曾并存多套前端（根 `frontend/`、`merged/frontend`、`tmp/pr1-frontend`、`tmp/pr2-frontend`、`tmp/pr6-check`、`tmp/repo-inspect`、`tmp/demo-integration/frontend`），已于 2026-10-30 删除。删除原因是改了一套却在另一套里看效果、误判为“改动没生效”。不得重新引入并行前端副本。
- 以下目录不是可运行前端，不能用来判断前端是否生效：`demo/frontend`（未跟踪，`demo/` 只读）、`archive/frontend-legacy`、`archive/partner_engine/frontend`（历史归档）。
- 后端不存在同类重复：顶层 `backend/` 只是 7 个 README 设计占位（停在 `d2f07bd`），实现只在 `apps/backend`、`packages/`。

## 当前 DSH 调度边界

- 2026-10-01 返工后：P01-02 为 READY_FOR_ZCODE，20 项交付哈希复算一致；仍待独立验收。Codex 已补 AGENTS.md 显式所有权，unit + integration 实跑为 226 passed / exit 0。G00 的问题登记输入漂移，P01-01 旧 precheck 已过期；P01-02/P01-03 precheck 与 G01 Codex review 缺失，G01 未有效签收。完整业务系统未交付。
- 当前调度以 `docs/agent-toolchain/12-project-completion-dispatch.md` 为准：Codex 治理解阻 → 独立复核 G00 → DSH 刷新自身 Phase 01 交接 → ZCode 三任务重验 → 独立 Codex 审查 G01。P01-02 的四项限定返工已停止；无新缺陷卡不得默认重启旧返工。G01 有效前不启动 P02–P39，不重新分发已阻塞的 P03–P05。
- 每次只执行一个明确任务。任务 ID 缺失时先定位最早阻塞点；不能从“继续”推断为任意扩展范围。具体返工任务卡限定的路径优先于通用角色提示词。
- 一次失败后可在同任务内定位和修复；输入及根因未改变时，不重跑整套必败验收。缺少外部必要条件时提交一次最小阻塞说明，指出责任方及恢复条件。

## 修改与验收

- 按任务精确文件白名单修改。A/B 所有权以 `OWNERSHIP.json` 为准；禁止改 B 的业务模块、公共类型、依赖锁或权限规则来掩盖 A 的缺陷。范围变更需有具体任务依据，不能自行放宽白名单。
- DSH 只生成自己的实现交接；禁止生成、覆盖或冒签 ZCode precheck、Codex review。开发探针必须使用 `--out-dir tmp/<本任务>/...`，不能覆盖 `artifacts/gates/` 的官方记录及旧日志。
- 修复测试必须保留正确性断言和有意义的正反例。禁止删除失败用例、skip/xfail、降低断言、伪造成功字段或把缓存/权限失败写成代码通过。
- 候选哈希仅覆盖明确相关的代码、配置、契约、测试和生成的业务 Schema；报告、日志、审查文件、`.mimosa/`、`tmp/`、缓存不能使候选自扰动。依赖证据分别保存、复算，不混入实现候选身份。
- 先写实际文件、完成验证，再计算交接哈希与存在数量。新候选使受影响旧证据失效；不得重算哈希后沿用未经重验的通过结论。保留历史日志和证据。
- 零测试、只跑旧测试、空目录分层检查和文档数量增长不证明业务实现。需要 PostgreSQL、OR-Tools、SimPy、模型或浏览器的验收按任务使用真实依赖。
- 当前执行器只注册 G01 附加业务断言；后续阶段签收必须核验对应断言/证据覆盖，缺覆盖即阻断。P13-01 按文件分 A/B；P36-02 的 A 任务/B 源码归属冲突须先裁定，任务标题不覆盖路径所有权。
- 常规已授权修复直接执行；不在业务开发中升级 DSH、增删插件、修改用户全局配置或启动其他自治执行循环。

返工前检查保存在 `docs/agent-toolchain/current-project-review-2026-10-01.md`；返工后状态与完整派发见 `docs/agent-toolchain/12-project-completion-dispatch.md`。本文件是执行约束，不代表运行中的 DSH 已加载它，也不替代进程权限或 Gate 实现。
