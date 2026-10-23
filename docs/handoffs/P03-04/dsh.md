# P03-04 · 实现版本 CAS、资源预留与幂等存储 · DSH 交接

- **Task ID**：`P03-04`（phase 3 `atomic-version-store`，owner `A`，出口 Gate `G03`）
- **计划版本**：1.1.0（任务书）／`TASK_MANIFEST.json` plan_version 1.0.0
- **本角色**：DSH 初步开发 Agent
- **最终状态**：**BLOCKED**
- **签收声明**：本记录不签收任何 Gate，不生成 Codex review，不代表 P03-04 已实现。

## 1. 结论

P03-04 **未开始实现**：7 个交付物路径中 0 个被创建。任务书写「理论上已交付 `G02、P03-03`」，实测两项都无效：

1. **同阶段前置 `P03-03` 为 BLOCKED**：`artifacts/handoffs/P03-03/dsh/evidence.json`（status=`BLOCKED`）与 `artifacts/handoffs/P03-03/zcode/precheck.json`（status=`BLOCKED`）。`G03` 探针原文：`[FAIL] dsh-evidence:P03-03: unexpected status=BLOCKED`、`[FAIL] zcode-precheck:P03-03: status=BLOCKED (expected Z_PRECHECK_PASSED)`。
2. **跨阶段 `G02` 无记录、`G01` 为 failed**：`[FAIL] previous-gate:G01: status=failed`、`[FAIL] previous-gate:G02: missing artifacts/gates/G02.json`。

**至此 Phase 03 四个任务全部 BLOCKED**，`G03` 无法从任何方向拼装。

### 本轮新增的独立发现：本任务的冻结接口在本阶段**不可能**满足

`PlanCommitStore.commit(cmd: CommitCommand, report: ValidationReport) -> CommitReceipt` 需要 `CommitCommand`、`ValidationReport`、`CommitReceipt`、`ScheduleVersion`。契约已明确这些**纯值类型的归属是 P02-03**：

- `DATA_CONTRACTS.md:24`：`ValidationReport | ... | 纯类型P02-03；边界/注册P10-01`
- `DATA_CONTRACTS.md:55-56`：`CommitCommand | ... | P02-03/P16-03`；`CommitReceipt | ... | P02-03`
- `DATA_CONTRACTS.md:79`（阶段间类型依赖规则）：*"P02-03的`domain/planning.py`完整定义…`CandidatePlan`、`SolveBudget`和`ValidationReport`等纯值类型，**不能等P06/P08/P10才出现被P03引用的类型**……**不再创建同名第二份定义**。Schema所需类型必须真正可实例化，不能用Any、空类或TODO代替。"*

实测确认类型缺失：`logistics_domain.planning`、`logistics_domain.entities`、`logistics_domain.ports`、`logistics_backend.persistence.version_store` 全部 `ModuleNotFoundError`。

**这不是新的架构问题**，契约已经裁决过（P03 被允许引用这些类型，正是因为 P02-03 必须先定义它们）。因此**不登记 ARCH 条目**——登记会把"交付缺失"错误归因给契约。它作为**契约文本层面的独立佐证**记录：即便 `G02` 已签收，`P02-03` 未交付时 P03-04 也**无法实现**；`P02-03` 是 P03-04 的硬前置（纸面与实务皆是）。

## 2. 依赖核验（逐项，非按文件名认定）

| 前置 | 实测证据 | 判定 |
| --- | --- | --- |
| `G00` | `G00.json` status=passed | 有效 |
| `G01` | `G01.json` status=**failed**，失败项 `[zcode-precheck:P01-01/02/03, codex-review]`；本轮**重新确认**这四份记录仍全部缺失（`P01-0x/zcode/precheck.json`、`G01-codex-review.json`） | **无效（阻塞）** |
| `G02` | `G02.json` **不存在**；探针 `5/27` —— 四轮输出**逐字节一致**，Phase 02 毫无变化 | **无效（阻塞）** |
| `P03-03` | DSH=`BLOCKED`、ZCode=`BLOCKED`；3 个代码交付物全部不存在（`persistence/` 目录本身不存在） | **无效（阻塞）** |
| `P02-03`（类型层） | `logistics_domain.planning` `ModuleNotFoundError`；契约把 `CommitCommand`/`ValidationReport`/`CommitReceipt` 归属给它 | **无效（阻塞）** |

## 3. 实际执行的命令与结果

工作目录统一 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`；环境：Windows 11、CPython 3.12.10、`uv 0.12.13`（PATH 上无 `uv`，使用 `tools/bin/uv.exe`）。

| # | 命令 | exit code | 结果 | 原始日志（sha256） |
| --- | --- | --- | --- | --- |
| 1 | `uv run pytest tests/unit/test_p03_04_atomic_version_store.py tests/integration/test_p03_04_atomic_version_store.py -q` | **4** | `ERROR: file or directory not found: tests/unit/test_p03_04_atomic_version_store.py`；`no tests ran in 0.00s`（passed/failed/skipped/collected 全 0） | `artifacts/handoffs/P03-04/dsh/logs/cmd1-pytest.log`（`294b84dd…72e0`，3791 B） |
| 2 | `uv run python scripts/check_architecture.py` | 0 | `architecture-layers: scanned 7 module(s) across 7 layer(s); violations=0` | `.../cmd2-architecture.log`（`736db1ee…9d64`，3323 B） |
| 3 | `uv run python scripts/gates.py --phase 02 --revision auto --out-dir tmp/dsh-p0304-g02-probe` | 1 | `G02: 5/27 checks passed`（四轮一致） | `.../gates-probe-phase02-phase03.log`（`6b9c9897…053c`，3604 B） |
| 4 | `uv run python scripts/gates.py --phase 03 --revision auto --out-dir tmp/dsh-p0304-g03-probe` | 1 | `G03: 11/28 checks passed` | 同上日志 |
| 5 | `uv run python -c "import logistics_domain.planning, ..."` | 0 | 四个模块全部 `ModuleNotFoundError` | 见 `evidence.json` 的 `frozen-type-probe` |

**命令 2 的诚实标注**：exit 0 是**空洞通过**——扫到的 7 个模块是未改动的 P01-01 占位包，且它**无法**检查本任务的 Constraint 4 义务（application 不导入 adapters；ORM 不传出 adapter），因为不存在任何 application/persistence 模块。**不得**作为验收证据。

**关于 `G03: 11/28`**：四轮为 `5 → 7 → 9 → 11`，**每次增长都只来自文档行**（本轮是 P03-03 的 `docs:*` 转 PASS）。**通过的任务命令数四轮恒为 4/8，且全是空洞的 `cmd2` 架构行**。这个计数器度量的是文档存在性，不是进展。

命令 3/4 刻意写入 gitignored `tmp/`，**没有**创建或覆盖任何 Gate 记录（`artifacts/gates/` 仍只有 `G00.json`、`G01.json`）。

## 4. 未测试项（禁止读作通过或失败）

- **Test Case 1**：两个事务争最后 1 个 dock → **恰好一方成功**（需两个真实并发事务 + 资源/预留表）。
- **Test Case 2**：同幂等 key 不同 body → `IDEMPOTENCY_CONFLICT`（需真实唯一约束与已存 body hash）。
- 接口 `PlanCommitStore.commit(cmd: CommitCommand, report: ValidationReport) -> CommitReceipt`（输入输出类型均不存在）。
- Business Rules：固定顺序锁资源行、复核版本与时段容量、CAS `active_version_id`、单事务原子写新版本/预留/审计/outbox、同 key 同 hash 返回**原 receipt**、校验报告必须匹配候选与快照 hash。
- G03 出口断言中的「最后一份资源并发提交恰一成功」与「事务失败无半版本」正是本任务的断言，当前**完全没有证据**。
- 错误码（`IDEMPOTENCY_CONFLICT`/`STALE_SNAPSHOT`/`RESOURCE_CONFLICT` 409 等）：本阶段**刻意不暴露正式提交路由**，作为 HTTP 行为不适用。
- `check_architecture.py` 能否发现 application 导入 adapter 或 ORM 泄漏：无相关模块可违规，**无法验证**。

## 5. 文件变更

**新建（DSH 交接/文档路径）**

- `artifacts/handoffs/P03-04/dsh/evidence.json`
- `artifacts/handoffs/P03-04/dsh/logs/cmd1-pytest.log`
- `artifacts/handoffs/P03-04/dsh/logs/cmd2-architecture.log`
- `artifacts/handoffs/P03-04/dsh/logs/gates-probe-phase02-phase03.log`
- `docs/handoffs/P03-04/dsh.md`（本文件）
- `docs/implementation/P03-04.md`
- `docs/implementation/reports/P03-04.md`

**其余新建**：`tmp/dsh-p0304-g02-probe/`、`tmp/dsh-p0304-g03-probe/`（非官方探针记录）。

**修改**：无。`demo/`、`demos/`、`contracts/*.json`、包 marker、既有测试、P03-01..P03-03 已交付证据、任何 Gate 证据均未改动。

**未创建的任务交付物（0/7，刻意）**：`apps/backend/src/logistics_backend/persistence/idempotency.py`、`.../reservations.py`、`.../version_store.py`、`tests/unit/test_p03_04_atomic_version_store.py`、`tests/integration/test_p03_04_atomic_version_store.py`。**也没有**在本任务里发明 `CommitCommand`/`ValidationReport`/`CommitReceipt`/`ScheduleVersion`——契约第 79 行明确禁止第二份定义。

## 6. 契约版本与 hash

- 契约版本前/后：`1.0.0` → `1.0.0`（未触碰契约；不需要 `contracts/changes/`）。
- 代码 revision 标签（写入本交接**之前**由 `scripts/gates.py` 的 `compute_revision()` 实测）：`content-sha256:46b5929f85973753193c31429a4d328f8bf2eaa6ecf3084a8f273fdad7ec864b`。历轮：`0295429f…c33f`（P03-03）、`eecbc859…b33f`（P03-02）、`79261f8a…e08c`（P03-01）。该标签**自扰动**（覆盖 `artifacts/handoffs/**`、`.mimosa/**`、`tmp/**`；P01-02 缺陷 D6/D9），每轮证据写入都在推动它。
- 输入 hash（关键项）：`P03-04-atomic-version-store.md` = `3d2a8865…91df`、`artifacts/handoffs/P03-03/dsh/evidence.json` = `ae765a71…b7b7`、`artifacts/handoffs/P03-03/zcode/precheck.json` = `5a425382…b5a6`、`DATA_CONTRACTS.md` = `1c77514c…f422e`、`TASK_MANIFEST.json` = `aa8dfad3…2e5`、`G01.json` = `4383ccac…d4`。
- 输出 hash：无实现产物（0/7）；三份日志 hash 见 §3。
- Gate 证据引用：`G00`（passed）、`G01`（failed）、`G02` **无记录**、`G03` 未签收；出口断言见 `docs/plan/PHASE_GATES.md:24`、`:64`。
- 事件日志：未发出 `p03_04.started/completed/rejected`（无任何 P03-04 代码路径被执行）；结构化替代为 `evidence.json` 的 `commands[]` 与三份原始日志。未输出 secret、个人数据或模型内部推理。

## 7. 系统性发现（更新，Phase 03 已整体阻塞）

`evidence.json` 的 `systemic_finding` 更新为：**Phase 03 全部四个任务已 BLOCKED**（31 个声明交付文件 0 个存在），而 Gate 通过数四轮 `5 → 7 → 9 → 11` 全部由文档行贡献，**通过的任务命令数恒为 4/8**。

由此可推断：**再下发 Phase 04 也会同样失败**——`G03` 无法拼装，Phase 04 的依赖正是 `G03`。

**建议把修复单位从"任务"改为"屏障"**，按序执行：

1. ZCode 写 P01-01..P01-03 三份预验收记录（G01 五条断言已全 passed，这是链上**最便宜**的一处修复）；
2. Codex 出 `G01-codex-review.json`、定 revision 失效策略、处置 `ARCH-0004`；
3. 项目管理侧决定锁内数据库依赖（psycopg/SQLAlchemy/Alembic）+ 补 Phase 01 环境手册（隔离 PostgreSQL、`TEST_DATABASE_URL`）；
4. 角色 A 交付 `P02-01 → P02-04`（**P02-03 是 P03-04 的硬前置**）并签 `G02`；
5. 再按序重发 `P03-01 → P03-02 → P03-03 → P03-04`。

## 8. 交给 ZCode 的重点边界与未测试项

本角色状态为 **BLOCKED**，**不请求** ZCode 预验收（0/7 交付物，无候选可审）。

1. 预验收前置链起点未变：ZCode 三份 P01 预验收 + Codex 的 G01 review。
2. 待重发后的 P03-04 预验收重点：**固定顺序**的资源行锁、版本与时段容量**复核**、CAS 真的作用于 `active_version_id`、新版本/预留/审计/outbox **同一事务**原子写入、同 key 同 hash 返回**逐字段相同的原 receipt**（而非重新计算后形状相同）、同 key 不同 body 必须 `IDEMPOTENCY_CONFLICT`、校验报告的候选/快照 hash 与命令一致、本阶段**不暴露**正式提交路由。
3. Test Case 1 必须由**两个真实并发事务**复现"恰一成功"，并同时断言**失败方的类型化原因**与**无半版本残留**；不得用单连接或 SQLite 近似。
4. 请特别核查"同 key 同 hash 返回原 receipt"是否真的读回存量 receipt——这是最容易被形状相同掩盖的一处（关系到 G13 的 outbox 原子性）。
5. §4 中标为 UNVERIFIED 的全部条目即当前未测试面，不得由任何后续报告改述为已通过。

## 9. 建议的下一步动作（按顺序）

1. 先按 §7 修复屏障，**暂停继续下发 Phase 03 与 Phase 04 任务**。
2. `G01`/`G02` 签收后按 `P03-01 → P03-02 → P03-03 → P03-04` 重发；P03-04 落地时用两个并发事务证明两条用例，并完成 CAS 与幂等的逐字段断言。
3. **不得**启动 Phase 04 或任何后续阶段：`G02`、`G03` 均未签收。
