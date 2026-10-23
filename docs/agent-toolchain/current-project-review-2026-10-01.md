# 当前项目成果与 DSH 执行修正

检查日期：2026-10-01。角色：Codex 项目检查与提示词修正。本次不修改业务实现、不签收任何 Gate、不冒签 ZCode 记录、不修改 DSH 用户级配置。

**分发时发现的范围差异：**本报告仅对应当前会话目录 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`。DSH 当前界面及另一树的 `docs/plan/PROJECT_STATE_20260918.md` 指向 `D:\Agent\Codex\IntelligentLogisticsDispatchingAgent`，该树计划已为 1.2.0，尚无正式 `G00.json`、根 workspace 清单或 apps/packages 实现。该文档还明确另一树不能作为其正式候选证据。因此下面的 186/1、G01 与 P01-02 返工结论不能外推到 DSH 当前目录；目标确认前任务不投送。另一树只进行了文件级核查，未修改或验收。

## 结论

正式工程已交付 Phase 01 基础环境、分层/所有权检查及 Gate 执行器；业务系统尚未实现。G01 官方记录为 failed，当前代码仍存在阻断性测试缺陷和证据判定缺口。下一项限定为 [P01-02 返工](11-dsh-repair-g01.md)，G01 有效签收前不启动后续阶段。

## 已确认的成果

| 范围 | 当前磁盘事实 | 判定边界 |
| --- | --- | --- |
| 规划与契约 | 109 个任务、40 个 Gate、14 个提示词目录；规划检查与 12 项检查器自测通过 | 静态规划通过不证明业务可用 |
| 正式 Python workspace | 六个 `packages/*` 和 `apps/backend` 已有清单及包 marker | 包导入成功不证明实体、API 或算法已实现 |
| 工程检查 | `check_architecture.py` 实跑 7 modules / 7 layers，0 violations | 当前业务模块基本未实现，覆盖有限 |
| P01-01 | `zcode/precheck.json` 状态为 `Z_PRECHECK_PASSED`；本次 Gate 检查未报告其输入漂移 | 只覆盖该记录固定的输入，不等于 G01 通过 |
| 当前测试 | 可写 uv 缓存下 187 项：186 passed / 1 failed，0 skipped | 唯一失败是 P01-02 集成测试的固定缺失记录断言 |
| Gate | G00 记录为 passed；G01 记录为 failed；G02–G05 官方文件缺失 | 本次未重新签收 G00/G01；不能以交接报告代替 Gate |
| 应用成果 | 正式 `domain` / `contracts` 等主要只有 `__init__.py`；`apps/backend` 无 main/API/persistence/worker，`apps/frontend` 无应用页面 | 旧 demo 的页面、API 与探针不能计入新工程成果 |

目录依据：`rg --files apps packages tests contracts`（排除依赖、缓存与构建物）。源码依据：`packages/domain/src/logistics_domain/__init__.py` 和 `packages/contracts/src/logistics_contracts/__init__.py` 明确声明业务尚未实现；后续名字访问显式抛出 `NotImplementedError`。

## 已复现的问题

| 问题 | 关键证据 | 对后续操作的影响 |
| --- | --- | --- |
| 测试把审查缺口固定为预期 | `tests/integration/test_p01_02_checks_and_gate_runner.py:555` 断言 P01-01 precheck 必须缺失；`pytest-isolated-cache.log` 唯一失败正是此断言 | 补齐正确预验收会使测试失败；应在受控临时仓库设置正反例 |
| 候选哈希自扰动 | `scripts/gates.py:327` 的 `compute_revision()`；最小探针写 `tmp/`、`.mimosa/`、handoff log 后 revision 均改变；`dirty_tree_hash()` 也纳入取证脚本 | 证据写入会改变候选，不能靠“不再写文件”的次序维持长期有效性 |
| 空预验收输入可通过 | `scripts/gates.py:636`；最小探针的 `verified_input_hashes={}` 被 `check_zcode_precheck()` 接受 | 只有通过状态、不含可复核输入的文件不能当作预验收证据 |
| 前置 Gate 仅检查状态 | `scripts/gates.py:689` 的 `check_previous_gates()`；只有 `{"status":"passed"}` 的 G00 文件被接受 | 违反冻结契约 F2/F3/F4/F6 的证据要求，需要核验字段、输入/日志及依赖 |
| 启动文档漂移 | 根 README 原来要求“只在 demo/ 开发”；实际 manifest、所有权和交接已使用根 `apps/` / `packages/` | 已修正根入口，历史资料继续保留为历史资料 |

最小探针在临时目录执行，证明具体判定函数的缺口；没有向官方 Gate 或其他角色证据写入伪造记录。机器结果见 [snapshot-and-evidence-probes.json](../../artifacts/reviews/2026-10-01/codex/snapshot-and-evidence-probes.json)。

旧 [BARRIER_REMEDIATION](../plan/BARRIER_REMEDIATION_G01_G02_G03.md) 的“只补四份 JSON 即可通过”判断已被当前实跑否定，已添加更正。不能直接填通过状态绕过真实审查。

## 本次验证记录

| 命令/检查 | 退出码 | 实测结果 | 原始日志 |
| --- | --- | --- | --- |
| `.venv/Scripts/python.exe -m pytest tests/unit tests/integration -q -p no:cacheprovider --basetemp tmp/codex-review-20261001-tests --tb=short` | 1 | 182 passed / 5 failed；4 项由默认 uv 缓存写权限引起，1 项为上述测试断言 | [首次日志](../../artifacts/reviews/2026-10-01/codex/pytest-current.log) |
| 同测试命令，`UV_CACHE_DIR=tmp/codex-review-20261001-uv-cache`、`UV_OFFLINE=1`，使用独立 basetemp | 1 | **186 passed / 1 failed**；原代码未改，环境问题消除 | [隔离缓存复测](../../artifacts/reviews/2026-10-01/codex/pytest-isolated-cache.log) |
| `uv lock --check`，同可写缓存与离线设置 | 0 | Resolved 40 packages；未修改锁 | [锁检查](../../artifacts/reviews/2026-10-01/codex/lock-check-current.log) |
| `python scripts/check_architecture.py` | 0 | 7 modules / 7 layers / violations=0 | [分层检查](../../artifacts/reviews/2026-10-01/codex/architecture-current.log) |
| `python scripts/gates.py --phase 01 --revision auto --check-only` | 1 | 官方记录 failed；整体 revision 漂移；P01-02/P01-03 precheck 和 G01 Codex review 缺失 | [Gate 现状](../../artifacts/reviews/2026-10-01/codex/g01-freshness-current.log) |
| `python tools/ai_coding_plan/validate_plan.py --self-test`，修改前 | 0 | 12 checker tests；109 prompts / 40 gates；errors=[] | [规划修改前](../../artifacts/reviews/2026-10-01/codex/plan-before.log) |

首次环境失败来自 `C:\Users\30382\AppData\Local\uv\cache\sdists-v9\.git` 的写权限；不能据此断言 uv.lock 已过期。切换到项目内可写缓存后锁检查成功，复测只剩代码缺陷。离线设置是本次环境的可用方案，不是所有机器的必要条件。

官方 G01 的 40 项输入 hash 在修正前逐项复算无漂移，整体 revision 变化来自其过宽文件集合；两种 freshness 结果应区分。官方 G00/G01 原始文件保持不变；完整日志、哈希与修改后的规划复核见 [本次证据](../../artifacts/reviews/2026-10-01/codex/evidence.json)。

## 已修改的执行提示词

- 根 [AGENTS.md](../../AGENTS.md)：固定正式工程根、证据要求、DSH 单任务边界、角色分离和停止条件。
- [DSH 角色提示词](04-dsh-development.md)、[共同规则](00-common.md)、[日常调度](10-daily-dispatch.md)：当前入口指向最早阻塞点；禁止重复下游阻塞轮次和冒签。
- [P01-02 原提示词](../prompts/01-foundation/P01-02-checks-and-gate-runner.md)：补充本轮事实与限定返工入口，原 manifest 节点和必需命令保留。
- [P01-02 返工任务卡](11-dsh-repair-g01.md)：列明可写文件、四项已复现缺口、验收命令、交接路径和结束条件。
- 根 README、AI-CODING-PLAN、两处提示词索引及旧屏障诊断：统一当前入口，纠正旧目录和过期解锁判断。

## 尚未验证或完成

Gate 实现缺陷仍交由本次 DSH 返工；本次只修改对应提示词及执行说明。真实 PostgreSQL、API、作业 worker、优化器、仿真、模型和前端闭环未验收。`docs/workflow/` 的交接治理、后续依赖/隔离数据库环境、ScenarioBundle 等类型归属仍须在相关任务实施前解决，不能因本次提示词修改声称已解阻。

本次未联系 DSH、未重启其进程、未更改用户级 profile。上述规则只对读取新项目入口的执行生效；提示词本身不等于操作系统权限或运行时强制拦截。
