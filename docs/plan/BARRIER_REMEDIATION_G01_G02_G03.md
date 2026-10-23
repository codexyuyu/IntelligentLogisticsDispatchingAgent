# 屏障处置清单 · G01 / G02 / G03（只读诊断）

> 2026-10-01 更正：本文保留为历史诊断，不作为当前启动任务。P01-01 precheck 已于 2026-09-28 写入；P01-02 测试硬编码该记录缺失，补齐记录会触发失败。本次隔离缓存复测为 186 passed / 1 failed。此外候选哈希自扰动、空输入哈希和前置 Gate 仅检查 status 的缺口已复现。下文“G01 只差四份记录”“写四个 JSON 即 26/26”“无须代码改动”的判断已不成立，C4 的不写文件次序不能替代哈希实现修复。当前执行[P01-02 限定返工](../agent-toolchain/11-dsh-repair-g01.md)，依据见[检查报告](../agent-toolchain/current-project-review-2026-10-01.md)；不得直接补写通过状态解除屏障。

- **性质**：只读诊断 + 可执行处置清单。**不是**任何任务的交付物，**不是** Gate 证据，**不签收**任何 Gate。
- **产出角色**：DSH（开发 Agent A），按用户显式授权（选项 A：屏障侧只读诊断）产出，供 ZCode / Codex / 项目管理侧/角色 A 使用。
- **依据**：`scripts/gates.py` 的判定逻辑（已逐行核对）+ 现场只读探测。
- **本诊断未修改任何交付物、Gate 记录或审查记录**；唯一新增文件即本文件。
- **生成时**代码 revision：`content-sha256:46b5929f85973753193c31429a4d328f8bf2eaa6ecf3084a8f273fdad7ec864b`
  （该标签由 `GateRunner.compute_revision()` 实测；它覆盖 `artifacts/handoffs/**`、`.mimosa/**`、`tmp/**`，**任何证据写入都会使其变化**，详见第 5 节 C4）

## 0. 结论（一句话）

**G01 差的不是实现，只有 4 份记录**：本轮现场复测 `uv run python scripts/gates.py --phase 01 --revision auto` 得 **22/26**——7 条任务命令、5 条验收断言、`previous-gate:G00`、6 份文档/报告、3 份 DSH 证据**全部通过**；2 项验收断言与 40/40 个输入 hash 亦全部有效。4 项失败全是「审查/预验收记录不存在」。因此整条链（G01 → Phase 02 → G02 → Phase 03 → G03）的解锁成本，第一步只是 **4 个 JSON 文件**；其后是 **Phase 02 的四个任务**（严格串行）与 **2 个环境前置决定**。

**关键次序警告**：`uv.lock` 与 `apps/backend/pyproject.toml` 被登记为 **G01 的输入产物**（`artifacts/gates/G01.json:input_artifact_hashes`）。一旦为了数据库把 psycopg/SQLAlchemy/Alembic 加进锁，G01 的输入就会漂移、**必须重签**。所以「锁变更」应发生在 G01 最终签收**之前**，否则签收要付两次。

## 1. G01 精确缺口（已逐项核对）

`scripts/gates.py` 对 G01 共判定 **26 项 = 14 条记录检查 + 7 条任务命令 + 5 条验收断言**，现状 **22/26 通过**，明细如下：

| 组 | 检查 | 现状 |
| --- | --- | --- |
| 7 条任务命令 | `P01-0{1,2,3}-cmd{1..3}` | **7/7 passed**（本轮现场复测） |
| 5 条验收断言 | `clean-install-imports`、`layer-boundaries`、`lock-reproducible`、`runner-fails-closed`、`legacy-demo-untouched` | **5/5 passed** |
| 前序 Gate | `previous-gate:G00` | **passed** |
| 任务文档/报告 | `docs/implementation/{P01-01,P01-02,P01-03}.md` 与 `reports/…` | **6/6 present** |
| DSH 证据 | `artifacts/handoffs/P01-0x/dsh/evidence.json` | **3/3 status=`READY_FOR_ZCODE`（合规，`accepted={"READY_FOR_ZCODE","Z_PRECHECK_PASSED"}`）** |
| ZCode 预验收 | `artifacts/handoffs/P01-0x/zcode/precheck.json` | **3/3 缺失 → 3 项 FAIL** |
| Codex 阶段 review | `artifacts/gates/G01-codex-review.json` | **缺失 → 1 项 FAIL** |

`failed_checks` 因此恰为 `[zcode-precheck:P01-01, zcode-precheck:P01-02, zcode-precheck:P01-03, codex-review]` —— **与 `artifacts/gates/G01.json` 记录一致，且"4 项失败"是当前真实状态**：写这 4 份记录，G01 即达 **26/26**，无需任何代码改动。

**输入 freshness 实测**：`G01.json:input_artifact_hashes` 共 40 项，**40/40 与当前文件一致（drifted=0）**。也就是说 G01 的旧证据没有过期，缺的只是记录。

## 2. 可执行处置项（按依赖顺序；含精确路径与判定字段）

### Z1 · ZCode：三份预验收记录（解 3 项 FAIL）

**路径**（`gates.py:305-311` 固化，无契约文档，见 Z4）：

- `artifacts/handoffs/P01-01/zcode/precheck.json`
- `artifacts/handoffs/P01-02/zcode/precheck.json`
- `artifacts/handoffs/P01-03/zcode/precheck.json`

**判定字段**（`gates.py:616-649`）：`status` 必须**精确等于** `"Z_PRECHECK_PASSED"`；`verified_input_hashes` 中每个条目都必须在运行 Gate 时**仍与磁盘一致**（`stale_input_hashes()` 逐条比对 `sha256_file`）。

**硬警告（新发现，务必遵守）**：`artifacts/handoffs/P01-02/dsh/evidence.json` 内 `artifacts.conftest.sha256` 记录的是 `95ad3430…`，而当前 `tests/conftest.py` 是 `b4c985aa…`（P01-03 后续为数据库 fixture 扩展过该文件）。**切勿照抄 DSH 证据里的历史 hash**，必须以**当前磁盘**为准重新计算，否则预验收会以 `N stale input hash(es)` 失败。

**建议冻结集合**（稳定、不自扰动；每条都应在写入前现场计算）：

```text
TASK_GRAPH.md
docs/plan/TASK_MANIFEST.json
docs/plan/PHASE_GATES.md
docs/architecture/DOMAIN_CATALOG.md
docs/architecture/DATA_CONTRACTS.md
docs/architecture/IMPLEMENTATION_CONVENTIONS.md
docs/prompts/01-foundation/P01-0N-*.md          （该任务自己的任务书）
docs/implementation/P01-0N.md
docs/implementation/reports/P01-0N.md
docs/handoffs/P01-0N/dsh.md
artifacts/handoffs/P01-0N/dsh/evidence.json
scripts/gates.py
scripts/check_architecture.py
tests/conftest.py
```

**不要冻结** `artifacts/gates/G01.json`（它含自身摘要，会自指漂移）、也不要冻结 `artifacts/gates/**` 与 `tmp/**`。

**文件形态样例**（字段名以 `gates.py` 为准；其余字段可自由补充，例如 `candidate`、`commands`、`defects`，与既存 `P02-02..P02-04/zcode/precheck.json` 保持同一风格）：

```json
{
  "schema_version": "1.0.0",
  "task_id": "P01-01",
  "phase": 1,
  "phase_gate": "G01",
  "reviewer": "ZCode",
  "review_role": "independent-pre-acceptance",
  "status": "Z_PRECHECK_PASSED",
  "reviewed_at_local": "<写入时刻>",
  "verified_input_hashes": { "<仓库相对路径>": "<写入前现场计算的 sha256>" }
}
```

### Z2 · ZCode：三份记录的**写入时序**（解「谁先谁后」）

`stale_input_hashes()` 是在**运行 Gate 的那一刻**比对的。因此：

1. 先把 P01-01、P01-02、P01-03 三份记录**全部写齐**（彼此不再互相扰动 —— 记录之间的路径不重叠）；
2. **再**运行 `uv run python scripts/gates.py --phase 01 --revision auto`。

若在第 1 步之间还改动任何被冻结文件（包括 `scripts/gates.py`、`tests/conftest.py`），对应记录的 hash 立即失效，必须重算重写。

### C1 · Codex：`artifacts/gates/G01-codex-review.json`（解 1 项 FAIL）

**必须字段**（`gates.py:659-687`）：

| 字段 | 要求 |
| --- | --- |
| `gate_id` | **必须等于 `"G01"`** |
| `status` | 必须是 `"approved"` 或 `"passed"` |
| `code_revision` | 必填，且**必须等于运行 Gate 当时的 revision**（`compute_revision()`；用 `--revision auto` 时即为该自动值） |
| `verified_input_hashes` | 与 Z1 同样逐条比对，必须 fresh |
| `reviewer` | 非空 |

**写入时序**：必须在 **Z1 三份记录写完之后**再计算并写入 `code_revision`——否则写入 Z1 会把 revision 推走，导致 `review covers revision '…', current revision is '…'` 失败。写入 C1 之后、运行 Gate 之前，**不得再改任何文件**。

### P1 · 项目管理侧：两个决定（阻塞 G03 验收，不阻塞开发）

| 编号 | 决定 | 现场证据 | 为什么必须由项目侧定 |
| --- | --- | --- | --- |
| P1-a | **允许把 psycopg（及 SQLAlchemy / Alembic）加入工作区锁** | `uv.lock` 中 `sqlalchemy`/`alembic`/`psycopg`/`asyncpg` **全部不存在**；`apps/backend/pyproject.toml` 亦无 | P03 属于数据库阶段，但依赖新增会改动 `uv.lock`+`apps/backend/pyproject.toml`（**两者都是 G01 输入**），需要被授权并接受 G01 重签 |
| P1-b | **补写 Phase 01 环境手册：隔离 PostgreSQL 启动方式 + `TEST_DATABASE_URL` 约定** | `tests/conftest.py:148-163` 在缺 `TEST_DATABASE_URL` 时 `pytest.fail`（**不 skip**）；`tests/conftest.py:173-179` 在缺 `psycopg` 时 `pytest.fail`；`docs/architecture/IMPLEMENTATION_CONVENTIONS.md:9` 引用该手册，但它**在仓库中不存在** | 契约要求「Docker PostgreSQL 与本地 PostgreSQL 两种明确启动方式，不能隐式连接个人数据库」，属于项目级文档 |

**本机现状**（供决策参考，非本清单可解决项）：`psql`/`pg_ctl` 不在 PATH；Docker CLI 已安装但守护进程不可达（`npipe:////./pipe/dockerDesktopLinuxEngine`）；`TEST_DATABASE_URL` 未设置。

### A1 · 角色 A（DSH）：Phase 02 四任务，**严格串行**

`TASK_MANIFEST.json` 的依赖链为 **全串行**（无并行候选）：

```text
P02-01 (deps [G01])
  └─ P02-02 (deps [G01, P02-01])
       └─ P02-03 (deps [G01, P02-02])      ← 定义 CommitCommand/ValidationReport/CommitReceipt/ScheduleVersion
            └─ P02-04 (deps [G01, P02-03])  ← 生成 contracts/schemas.json（只能由脚本生成）
                 └─ G02
```

各任务必须落地的文件（`allowed_files` 共 7 项 = 代码 3/2/2/6 + 任务文档 + 报告 + 单元测试 + 集成测试）：

| 任务 | 代码交付物 | 测试用例（各 2 条） |
| --- | --- | --- |
| P02-01 | `packages/domain/src/logistics_domain/{errors,primitives,states}.py` | `[0,10)` 与 `[10,20)` 不冲突；`delivered -> draft` ⇒ `INVALID_TRANSITION` |
| P02-02 | `packages/{contracts/src/logistics_contracts/entities.py,domain/src/logistics_domain/orders.py,domain/src/logistics_domain/resources.py}` | 需求 1001g 与车辆 1000g ⇒ 可表示且判容量违规；`cargo.temperature=[80,20]` ⇒ 输入无效 |
| P02-03 | `packages/{contracts/src/logistics_contracts/planning.py,domain/src/logistics_domain/planning.py}` | `status=TIMEOUT` 且 `candidate=null` ⇒ 合法失败结果；`parent_version_id` 指向自身 ⇒ 拒绝 |
| P02-04 | `packages/domain/src/logistics_domain/{execution,runtime}.py`、`packages/contracts/src/logistics_contracts/{common,runtime}.py`、`scripts/export_contracts.py`、`contracts/schemas.json` | `Event(kind=vehicle_failure, payload 缺 vehicle_id)` ⇒ 校验失败；两次 export ⇒ 字节一致 |

**结构性好消息（降低 Phase 02 风险）**：G01 的 `input_artifact_hashes` **不包含**这些新文件；Phase 02 只要**不修改**已登记文件（`uv.lock`、`apps/backend/pyproject.toml`、`scripts/gates.py`、`tests/conftest.py`、各 `__init__.py` 等），G01 的有效性就**不会**因新增代码而失效。而 `tests/conftest.py` 已提供隔离数据库 fixture，P02 的集成测试可以直接跑真机 PostgreSQL，**不需要也不能**用 SQLite 或测试替身替代。

### A2 · 角色 A（DSH）：Phase 03 四任务重发（G02 签收之后）

现有 `P03-01..P03-04` 的 DSH 证据状态均为 `BLOCKED`，而 Gate 只接受 `READY_FOR_ZCODE` / `Z_PRECHECK_PASSED`。即使前置修好，**必须重发任务并重写这四份证据**，旧记录不可复用。

### C2 · Codex：G02 / G03 阶段签收

`artifacts/gates/G02-codex-review.json`、`artifacts/gates/G03-codex-review.json`，字段要求与 C1 相同（`gate_id` 分别等于 `"G02"` / `"G03"`）。G02 需在 P02-01..04 全部预验收通过后运行 `scripts/gates.py --phase 02`，G03 同理。

## 3. 为什么「重发任务」不会推进（数据）

四轮 Gate 探针的 G03 计数与「通过的任务命令数」：

| 轮次 | G03 通过 | 通过的任务命令 |
| --- | --- | --- |
| P03-01 | 5/28 | 4/8（全为空洞 `cmd2`） |
| P03-02 | 7/28 | 4/8 |
| P03-03 | 9/28 | 4/8 |
| P03-04 | 11/28 | 4/8 |
| 本诊断（写完 P03-04 文档后复测） | **13/28** | 4/8 |

**每次增长都只来自文档行**（BLOCKED 文档使 `docs:*` 由 missing 变 present），任务命令通过数**恒为 4/8**，且那 4 条是 `check_architecture.py` 对未改动占位包的空洞扫描。Phase 03 声明交付文件 **31 个，存在 0 个**。

结论：G03 计数器度量的是**文档存在性**，不是进展。继续逐任务下发只会复现 `BLOCKED`，并继续消耗 Gate 探针与证据成本。

## 4. Definition of Done（每一步的可判定出口）

| 步骤 | 完成判据（可直接运行） | 期望 |
| --- | --- | --- |
| Z1+Z2 | `artifacts/handoffs/P01-0{1,2,3}/zcode/precheck.json` 存在且 `status="Z_PRECHECK_PASSED"`，`verified_input_hashes` 全 fresh | 3 项由 FAIL → PASS |
| C1 | `artifacts/gates/G01-codex-review.json` 字段齐全且 `code_revision` 与当时 revision 一致 | 第 4 项 FAIL → PASS |
| G01 签收 | `uv run python scripts/gates.py --phase 01 --revision auto` | `status: passed`（**实测当前 22/26，4 项失败恰为上述 4 条记录；补齐后应为 26/26**） |
| A1 | `uv run python scripts/gates.py --phase 02 --revision auto` | 全部 PASS → 再由 C2 签 G02 |
| A2 | `uv run python scripts/gates.py --phase 03 --revision auto` | 全部 PASS → 再由 C2 签 G03 |

## 5. 附：四条易踩的坑（均有现场证据）

- **C3 · 计数口径（已实测，非估算）**：G01 合计 **26 项 = 14 条记录检查 + 7 条任务命令 + 5 条验收断言**，当前 **22/26**，失败的恰是 4 条记录：
  `zcode-precheck:P01-01/02/03` + `codex-review`；补齐后应为 **26/26**。
  参考：G02 当前 **5/27**（22 项失败）、G03 当前 **13/28**（15 项失败；本轮由 11 升至 13，仅因本诊断前 P03-04 的 `docs:*` 转 present）。
  若某次运行出现 `REVIEW-UNREADABLE`，说明 JSON 无法解析（`gates.py:316-323` 会把该文件视为缺失并记录失败原因），请先校验 JSON 合法性。
- **C4 · revision 自扰动（P01-02 缺陷 D6/D9）**：`compute_revision()` 覆盖 `artifacts/handoffs/**`、`.mimosa/**`、`tmp/**`。因此 **Codex review 的 `code_revision` 永远只能覆盖“写入它的那一刻”**，之后任何证据写入都会使其不匹配。正确做法：Z1 三份写好 → 立即写 C1 → 立即跑 Gate，中途不写任何其他文件。（本清单自身写入也会推动 revision。）
- **C5 · 修 D6 会连带作废 G01**：`scripts/gates.py` 本身是 G01 的登记输入（40 项之一，当前 fresh）。若为修 D6 改动 `scripts/gates.py`，G01 输入立即漂移、必须重跑重签。**建议把 D6 的修复排到 G01 最终签收之后**，或与 P1-a 的锁变更一起、在最终签收之前一次做完。
- **C6 · 不要照抄历史 hash**：除第 2 节 Z1 提到的 `tests/conftest.py`（P01-02 记录 `95ad3430…` vs 现值 `b4c985aa…`）外，任何「从旧证据里搬 hash」的做法都会以 `N stale input hash(es)` 失败。**一律现场计算。**

## 6. 本清单未做与不做的事

- 未创建任何 `zcode/precheck.json`、`G0x-codex-review.json`、Gate 记录或任务交付物；未修改 `artifacts/gates/**`、`artifacts/handoffs/**`、`demo/`、`demos/`、任何既有测试或证据。
- 未评估 Phase 01/02 已有代码的**正确性**（本清单只处理「记录缺失」与「次序/环境」两类问题；G01 的五条断言已由 DSH 侧执行器判定为 passed，独立复核仍属 ZCode/Codex 职责）。
- 未就接口/类型问题登记新的 ARCH 条目：`DATA_CONTRACTS.md:24/55/56/79` 已把 `CommitCommand`/`ValidationReport`/`CommitReceipt` 明确归属 P02-03 并禁止在 P03 重复定义，属**交付缺失**而非契约冲突（详见 `artifacts/handoffs/P03-04/dsh/evidence.json` 的 `frozen_interface_unreachable`）。
