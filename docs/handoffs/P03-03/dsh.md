# P03-03 · 实现快照读取与事务工作单元 · DSH 交接

- **Task ID**：`P03-03`（phase 3 `repositories-and-snapshot`，owner `A`，出口 Gate `G03`）
- **计划版本**：1.1.0（任务书）／`TASK_MANIFEST.json` plan_version 1.0.0
- **本角色**：DSH 初步开发 Agent
- **最终状态**：**BLOCKED**
- **签收声明**：本记录不签收任何 Gate，不生成 Codex review，不代表 P03-03 已实现。

## 1. 结论

P03-03 **未开始实现**：7 个交付物路径中 0 个被创建。任务书写「理论上已交付 `G02、P03-02`」，实测两项都无效：

1. **同阶段前置 `P03-02` 为 BLOCKED**：`artifacts/handoffs/P03-02/dsh/evidence.json`（status=`BLOCKED`）与 `artifacts/handoffs/P03-02/zcode/precheck.json`（status=`BLOCKED`）。`G03` 探针原文：`[FAIL] dsh-evidence:P03-02: unexpected status=BLOCKED`、`[FAIL] zcode-precheck:P03-02: status=BLOCKED (expected Z_PRECHECK_PASSED)`。任务书要求同阶段前置必须有有效 `Z_PRECHECK_PASSED`，此条不成立。
2. **跨阶段 `G02` 无记录、`G01` 为 failed**：`[FAIL] previous-gate:G01: status=failed`、`[FAIL] previous-gate:G02: missing artifacts/gates/G02.json`。`docs/plan/PHASE_GATES.md` 明确 `G01`/`G02` 失败阻塞 Phase 03 及以后。

`TASK_MANIFEST.json:707-710` 与 `TASK_GRAPH.md:60` 均把依赖写作 `[G02, P03-02]`。

**为什么不能"先写快照层再解释"**：`snapshots.py`/`uow.py` 必须读取 P03-01/P03-02 建出的表与 ORM 映射（`resource_models.py`、`planning_models.py`、`runtime_models.py`、`0001/0002` 迁移与 `migrations/env.py`），这些**全部不存在**；`PlanningScope`/`PlanningSnapshot`/`ResourceRevision`/`InventoryLedger` 领域类型也不存在；而 `packages/domain/src/logistics_domain/ports/` 目录本身都不存在，`ports/storage.py` 没有父包。在领域类型冻结之前先写 storage port，就等于用 port 反推领域模型——正是 Architecture Constraint 6 禁止的"重复定义 Domain Model"，也违反「Domain Contract → Schema → Service Interface → Implementation」的顺序。

## 2. 依赖核验（逐项，非按文件名认定）

| 前置 | 实测证据 | 判定 |
| --- | --- | --- |
| `G00` | `artifacts/gates/G00.json` status=passed | 有效 |
| `G01` | `G01.json` status=**failed**（5 条断言全 passed，失败仅因缺 `zcode-precheck:P01-01/02/03` 与 `codex-review` 记录） | **无效（阻塞）** |
| `G02` | `G02.json` **不存在**；探针 `5/27 checks passed` | **无效（阻塞）** |
| `P03-02` | DSH=`BLOCKED`、ZCode=`BLOCKED`；3 个代码交付物全部不存在 | **无效（阻塞）** |
| `P03-01`（传递） | DSH=`BLOCKED`、ZCode=`BLOCKED` | 无效 |

Phase 03 阻塞链已成型：`P03-01 → P03-02 → P03-03` 三者全部 BLOCKED，根因完全相同。

## 3. 实际执行的命令与结果

工作目录统一 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`；环境：Windows 11、CPython 3.12.10、`uv 0.12.13`（PATH 上无 `uv`，使用 `tools/bin/uv.exe`）。

| # | 命令 | exit code | 结果 | 原始日志（sha256） |
| --- | --- | --- | --- | --- |
| 1 | `uv run pytest tests/unit/test_p03_03_repositories_and_snapshot.py tests/integration/test_p03_03_repositories_and_snapshot.py -q` | **4** | `ERROR: file or directory not found: tests/unit/test_p03_03_repositories_and_snapshot.py`；`no tests ran in 0.00s`（passed/failed/skipped/collected 全 0） | `artifacts/handoffs/P03-03/dsh/logs/cmd1-pytest.log`（`cc1bf8ca…33e3`，2858 B） |
| 2 | `uv run python scripts/check_architecture.py` | 0 | `architecture-layers: scanned 7 module(s) across 7 layer(s); violations=0` | `.../cmd2-architecture.log`（`5c45f26d…11fe`，2375 B） |
| 3 | `uv run python scripts/gates.py --phase 02 --revision auto --out-dir tmp/dsh-p0303-g02-probe` | 1 | `G02: 5/27 checks passed`（与上一轮完全一致） | `.../gates-probe-phase02-phase03.log`（`74c191f0…393a`，3435 B） |
| 4 | `uv run python scripts/gates.py --phase 03 --revision auto --out-dir tmp/dsh-p0303-g03-probe` | 1 | `G03: 9/28 checks passed` | 同上日志 |

**命令 2 的诚实标注**：exit 0 是**空洞通过**，且它**无法**检查本任务的核心架构义务——「ORM 不传出 adapter」。持久化模块不存在，因此该检查当前覆盖不到本任务的任何 Constraint 4 义务，**不得**作为验收证据引用。

**关于 `9/28` 的解读**：本轮较上轮 `7/28` 上升，**全部来自文档行**（P03-02 的两份 BLOCKED 文档使其 `docs:*` 转为 `[PASS]`，以及 DSH 证据行由 missing 变为 `unexpected status=BLOCKED`）。**通过的任务命令数未变，仍为 4/8，且全是空洞的 `cmd2` 架构行**。数字上升不代表任何前置更接近满足。

命令 3/4 刻意写入 gitignored `tmp/`，**没有**创建或覆盖任何 Gate 记录（`artifacts/gates/` 仍只有 `G00.json`、`G01.json`）。

## 4. 未测试项（禁止读作通过或失败）

- **Test Case 1**：并发更新车容量 → 单一快照不混合新旧读（需两个真实并发连接 + 资源表）。
- **Test Case 2**：UoW 内抛错 → 全部回滚，无半状态。
- 接口 `PlanningSnapshotStore.capture(scope: PlanningScope) -> PlanningSnapshot`、`UnitOfWork.commit() -> None`（类型与会话均不存在）。
- Business Rules：`REPEATABLE READ` 一致快照、快照包含**矩阵与日历版本**、ORM 不传出 adapter、快照 hash 规范化序列化、DTO 映射到纯领域 snapshot。
- G03 出口断言中的「一致快照」一项正属本任务，当前**完全无证据**。
- 错误码映射（`INVALID_INPUT`/422、`STALE_SNAPSHOT`/`RESOURCE_CONFLICT` 409、503）：本任务无 HTTP 边界，**不适用**。
- `check_architecture.py` 能否真正发现 ORM 泄漏出 adapter：无持久化模块可违规，**无法验证**。

## 5. 文件变更

**新建（DSH 交接/文档路径）**

- `artifacts/handoffs/P03-03/dsh/evidence.json`
- `artifacts/handoffs/P03-03/dsh/logs/cmd1-pytest.log`
- `artifacts/handoffs/P03-03/dsh/logs/cmd2-architecture.log`
- `artifacts/handoffs/P03-03/dsh/logs/gates-probe-phase02-phase03.log`
- `docs/handoffs/P03-03/dsh.md`（本文件）
- `docs/implementation/P03-03.md`
- `docs/implementation/reports/P03-03.md`

**其余新建**：`tmp/dsh-p0303-g02-probe/`、`tmp/dsh-p0303-g03-probe/`（非官方探针记录）。

**修改**：无。`demo/`、`demos/`、`contracts/*.json`、包 marker、既有测试、P03-01/P03-02 已交付证据、任何 Gate 证据均未改动。

**未创建的任务交付物（0/7，刻意）**：`apps/backend/src/logistics_backend/persistence/snapshots.py`、`.../uow.py`、`packages/domain/src/logistics_domain/ports/storage.py`、`tests/unit/test_p03_03_repositories_and_snapshot.py`、`tests/integration/test_p03_03_repositories_and_snapshot.py`。

## 6. 契约版本与 hash

- 契约版本前/后：`1.0.0` → `1.0.0`（未触碰契约；不需要 `contracts/changes/` 条目）。
- 代码 revision 标签（写入本交接**之前**由 `scripts/gates.py` 的 `compute_revision()` 实测）：`content-sha256:0295429feba1f68bdc37c3e338c96d9e10ff1c10eb77c2a5b8f63e0fa542b33f`。前两轮同工具实测值：`eecbc859…b33f`（P03-02）、`79261f8a…e08c`（P03-01）。该标签**自扰动**（覆盖 `artifacts/handoffs/**`、`.mimosa/**`、`tmp/**`；P01-02 缺陷 D6/D9）。
- 输入 hash：见 `evidence.json` 的 `input_hashes`。本任务特有：`docs/prompts/03-database/P03-03-repositories-and-snapshot.md` = `24e66522…b677`、`artifacts/handoffs/P03-02/dsh/evidence.json` = `58078810…b1b8`、`artifacts/handoffs/P03-02/zcode/precheck.json` = `68e85cac…b1ac4`。
- 输出 hash：无实现产物（0/7）；三份日志 hash 见 §3。
- Gate 证据引用：`G00`（passed）、`G01`（failed）、`G02` **无记录**、`G03` 未签收；出口断言见 `docs/plan/PHASE_GATES.md:24`、`:64`。
- 事件日志：未发出 `p03_03.started/completed/rejected`（无任何 P03-03 代码路径被执行）；结构化替代为 `evidence.json` 的 `commands[]` 与三份原始日志。未输出 secret、个人数据或模型内部推理。

## 7. 系统性发现（本轮新增，建议优先处置）

`evidence.json` 的 `systemic_finding` 记录：**Phase 03 已有三个任务连续因同一未修复根因 BLOCKED**，而 Gate 通过数却从 `5/28 → 7/28 → 9/28` 上升，上升全部来自文档行，**通过的任务命令数始终是 4/8 且都是空洞架构检查**。

结论：**当前条件下重新下发 P03-03 或 P03-04 只会复现本记录**（换一个 task id），不会产生工程进展，却要再付一轮 Gate 探针与证据成本。建议把修复单位从"任务"改为"屏障"：

1. ZCode 写 P01-01..P01-03 三份预验收记录（G01 失败的全部剩余原因）；
2. Codex 出 `G01-codex-review.json` 与 revision 失效策略，处置 `ARCH-0004`；
3. 项目管理侧决定锁内数据库依赖 + 补 Phase 01 环境手册（隔离 PostgreSQL、`TEST_DATABASE_URL`）；
4. 角色 A 交付 `P02-01 → P02-04` 并签 `G02`；
5. 再按序重新下发 `P03-01 → P03-02 → P03-03`。

## 8. 交给 ZCode 的重点边界与未测试项

本角色状态为 **BLOCKED**，**不请求** ZCode 预验收（0/7 交付物，无候选可审）。

1. 预验收前置链：ZCode 的三份 P01 预验收记录 + Codex 的 G01 review，是整条链的起点。
2. 待重发后的 P03-03 预验收重点：`snapshots.py` 是否真的在**一次事务**内读取范围内实体与版本向量、是否使用 REPEATABLE READ、快照是否包含**矩阵与日历版本**、hash 规范化序列化是否稳定、DTO 是否映射到**纯领域** snapshot、ORM 是否**绝不**传出 adapter、`uow.py` 的 `commit()` 是否 all-or-nothing。
3. Test Case 1 必须由**两个真实并发连接**复现"不混合新旧读"，不得用单连接或 SQLite 近似。
4. `ports/storage.py` 只能对 P02 已冻结的领域类型声明 Protocol；若 ZCode 发现该 port 反过来定义了领域类型，应判为重复定义 Domain Model 缺陷。
5. §4 中标为 UNVERIFIED 的全部条目即当前未测试面，不得由任何后续报告改述为已通过。

## 9. 建议的下一步动作（按顺序）

1. 先按 §7 修复屏障，**暂停继续下发 Phase 03 任务**。
2. `G01`/`G02` 签收后，按 `P03-01 → P03-02 → P03-03` 顺序重发；P03-03 落地时在真机 PostgreSQL 上用两个并发连接证明两条用例，并完成快照 hash 的确定性检查。
3. **不得**启动 P03-04 或任何后续阶段：`G02`、`G03` 均未签收。
