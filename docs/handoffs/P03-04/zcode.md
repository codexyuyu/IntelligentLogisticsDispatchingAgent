# P03-04 · ZCode → Codex 独立预验收报告

| 项目 | 值 |
| --- | --- |
| Task ID | `P03-04`（实现版本 CAS、资源预留与幂等存储；**Phase 03 最后一个任务**，负责方 A） |
| 审查角色 | ZCode 独立预验收（**不是**开发方，DSH 的开发身份不覆盖本角色的审查职责） |
| 审查对象 | 仓库当前 candidate（`D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，与 DSH 同一项目、同一候选；本仓库无 `.git`，按整体内容哈希定位） |
| 本角色状态 | **`BLOCKED`**（与 DSH 自报一致，其全部依据已独立复现，含它对契约的逐行引用） |
| 阶段 Gate | `G03`（未签收；`G02` 无记录、`P03-03` 为 BLOCKED、`G01` 为 `failed`）；**本报告不签收任何 Gate** |
| 证据入口 | `artifacts/handoffs/P03-04/zcode/evidence.json`、`artifacts/handoffs/P03-04/zcode/logs/`（8 份日志） |
| 审查时间 | 2026-09-15（本机时区） |

## 0. 结论（先读这一段）

**P03-04 没有实现候选：5 个代码/测试交付物全部不存在，只有两份"BLOCKED 报告"文档（交付路径 2/7，代码与测试 0/5）。** 依赖 23 项中仅 3 项存在，而那三项正是 P03-01/P03-02/P03-03 自己的 BLOCKED 证据记录——**受阻报告不是已交付的能力**。

判定 **`BLOCKED`**，与 DSH 一致。

**本任务是 Phase 03 的最后一个任务，所以这一轮同时是阶段层面的终点：Phase 03 四个任务全部提交了交接，且全部是 BLOCKED、代码交付合计 0/21。`G03` 无法从任何方向拼装**，而 G03 的四条出口断言（真机迁移/回滚/FK、一致快照、最后一份资源并发提交恰一成功、事务失败无半版本）**从未被执行过一次**。Phase 04 及以后继续被挡在 `G03` 之后。

### 本轮新增的独立验证：P03-04 被**契约文本**锁死在 P02-03 之后

DSH 提出了一条纸面级论证，我逐行核对了它的引用，**全部准确**：

| 契约位置 | 原文要点 | 后果 |
| --- | --- | --- |
| `DATA_CONTRACTS.md:24` | `ValidationReport` 归属 = **纯类型P02-03** | 本任务接口的入参类型不在 P03 手上 |
| `:55` | `CommitCommand` 归属 = **P02-03/P16-03** | 同上 |
| `:56` | `CommitReceipt` 归属 = **P02-03** | 同上 |
| `:79` | "P02-03的 `domain/planning.py` 完整定义…`ValidationReport` 等纯值类型，**不能等 P06/P08/P10 才出现被 P03 引用的类型**……**不再创建同名第二份定义**。Schema所需类型必须真正可实例化，不能用 Any、空类或 TODO 代替" | 顺序被契约钉死，且**禁止**用同名的第二份定义绕过 |

也就是说：**即使 `G02` 已签收，只要 `P02-03` 未交付，P03-04 也无法实现**——它不能在存储层自己声明一份 `CommitCommand`。DSH 因此**刻意没有**新开 ARCH 条目（因为契约已经裁决过，登记会把"交付缺失"错误归因给契约），我同意这个判断。

### 一条顺带澄清的正面结论

DSH 的 Test Case 2 期望错误码 `IDEMPOTENCY_CONFLICT`。我核对冻结错误表：`STALE_SNAPSHOT/RESOURCE_CONFLICT/IDEMPOTENCY_CONFLICT/CONFIRMATION_EXPIRED→409` —— **该错误码确实已冻结**，所以这条用例的期望有契约来源，不是自造。对比之下 `UNSUPPORTED` 不在错误表内（那是已登记的 `ARCH-0003`），**不是本任务的新缺口**。我把这条记下来，避免有人重复推导成"P03-04 用了未登记错误码"的误报。

## 0.1 · 本轮中途出现的关键产物：G01 缺口已实测为「4 个文件、0 行代码」

审查进行中，DSH 在用户显式授权下产出了一份**只读屏障诊断** `docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md`（05:45，非任务交付物、非 Gate 证据、不签收任何 Gate，它自己也这么声明）。它给出了目前**最有杠杆的一条事实**，我没有采信而是逐条复核，**六条全部成立**：

| DSH 的诊断主张 | 我的独立复核 | 结论 |
| --- | --- | --- |
| `G01` 实测 **22/26**，唯一失败是 4 份记录缺失 | 我用沙箱自跑 `gates.py --phase 01 --out-dir tmp/zcode-g01-diagnostic`（不签收、不覆盖官方记录）：**22/26** —— 7/7 任务命令、5/5 验收断言、`previous-gate:G00`、3/3 DSH 证据（`READY_FOR_ZCODE`）、6/6 文档行**全部 PASS**；失败的恰是 3 份 zcode 预验收 + 1 份 codex review | **成立** |
| `G01.json` 的 40 条 `input_artifact_hashes` **0 条漂移** | 逐条重算：40 条记录、**0 条不一致** → 旧证据没过期，缺的只是记录 | **成立** |
| `uv.lock` 与各 `pyproject.toml` **是 G01 的输入产物** | 匹配到 9 个相关输入键（`uv.lock` + 7 个成员 `pyproject.toml` + 根 `pyproject.toml`） | **成立，且这是个顺序陷阱** |
| P01-02 的 DSH 证据里 `conftest` 哈希是陈旧的 | 实测：其记录 `95ad3430…`，而磁盘上的 `tests/conftest.py` 是 `b4c985aa…`（P01-03 后来为数据库 fixture 扩展过它） | **成立，是个真陷阱** |
| 4 份缺失记录的具体路径 | 逐路径检查：3 份 `P01-0x/zcode/precheck.json` 与 `G01-codex-review.json` 确实全不存在 | **成立** |
| 3 份 P01 DSH 证据是 `READY_FOR_ZCODE`（执行器接受） | 逐份读取，三份均为 `READY_FOR_ZCODE`，在 `gates.py` 的接受集合内 | **成立** |

**由此得到两条可执行结论，请 Codex 优先处理：**

1. **`G01` 距 26/26 只差 4 个 JSON 文件、0 行代码改动**，其中 **3 份是本角色（ZCode）自己的欠账**。整条链（G01 → Phase 02 → G02 → Phase 03 → G03）解锁成本的第一跳极低，但后续仍是 Phase 02 四个任务的严格串行交付与 2 个环境前置决定。
2. **顺序陷阱**：`uv.lock` 与 7 个 `pyproject.toml` 被登记为 G01 的输入。**一旦为数据库加入 psycopg/SQLAlchemy/Alembic，G01 的输入即漂移、必须重签**。所以"加锁依赖"应当发生在 **G01 最终签收之前**，否则签收要付两次。同理，D3 的解法与 G01 的签收顺序必须一起排。

**我本轮没有代写那 3 份预验收记录，理由请 Codex 认可：** 本轮被指派的任务是 P03-04；而 `Z_PRECHECK_PASSED` 只有在**真正逐任务做过独立验证之后**才是诚实的——那需要每个任务各自的强制命令、边界检查与原始日志。在没有做那轮工作的情况下发出三份"通过"判定，正是本角色存在的意义所要防止的"走形式"。它是**一件独立、完整的活**，应当被单独指派（另见第 7 节与 evidence.json 的 `mid_review_artifact.what_i_did_not_do_and_why`）。

## 1. 目标、白名单与契约核对

- **任务 Prompt 即验收需求**：`docs/prompts/03-database/P03-04-atomic-version-store.md`。
- **白名单（Files，7 项）**：`apps/backend/src/logistics_backend/persistence/idempotency.py`、`.../reservations.py`、`.../version_store.py`、`docs/implementation/P03-04.md`、`docs/implementation/reports/P03-04.md`、`tests/integration/test_p03_04_atomic_version_store.py`、`tests/unit/test_p03_04_atomic_version_store.py`。manifest `allowed_files` = 7，与 Prompt 一致。
- **存在性矩阵**：**2/7 存在，两项均为 BLOCKED 报告文档**；代码/测试 **0/5**。注意 `apps/backend/src/logistics_backend/persistence/` **目录本身不存在**，三个模块连父包都没有。
- **依赖核对**：`TASK_MANIFEST.json` deps = `["G02", "P03-03"]`。实测 `G02` 记录不存在；`P03-03` 的 DSH 证据与 ZCode 预验收均 `BLOCKED`、代码 0/5；`G01` = `failed`。
- **冻结接口**：`PlanCommitStore.commit(cmd: CommitCommand, report: ValidationReport) -> CommitReceipt`。契约第 96 行还冻结了它的**调用语义**："由ScheduleService调用，**单事务**"；第 97 行把 `ScheduleService` 定为"唯一正式计划提交用例"。这与 Prompt 的 Business Rule"**此阶段只测试存储事务，尚不得公开正式提交路由**"一致——**重新下发时不得新增 HTTP 路由**，我把它列进了重验清单。

## 2. 强制命令实跑结果（原始日志逐条保留）

| 命令 | 我的实测 | DSH 报告 | 一致性 |
| --- | --- | --- | --- |
| `uv run pytest tests/unit/test_p03_04_atomic_version_store.py tests/integration/test_p03_04_atomic_version_store.py -q` | `file or directory not found`；**exit 4**，0 用例 | exit 4、0 用例 | 一致 |
| `uv run python scripts/check_architecture.py` | `7 module(s) across 7 layer(s); violations=0`；**exit 0** | exit 0（DSH 自标空洞通过） | 一致 |

**第二条命令对本任务尤其空洞**：它扫到的 7 个模块是 P01-01 的空壳，而且按我在 P03-03 轮实测的结论（本轮已再次复现验证），**它根本无法检查本任务的核心义务**——"事务写留在存储层、ORM 不传出 adapter"（见 D5）。也就是说 P03-04 的验收标准 3"依赖边界检查通过"对其最关键的不变量**是空洞通过**。

**额外实跑的本任务关键检查**：

| 检查 | 结果 |
| --- | --- |
| 契约引用核对 | DSH 引用的 `DATA_CONTRACTS.md` 第 24/55/56/79/96/97 行**逐行准确**；`IDEMPOTENCY_CONFLICT` **在冻结错误表内** |
| 架构检查器覆盖（复现验证） | 场景 A 检出、场景 B（ORM 已声明）**0 违规** —— 与 P03-03 轮结论一致（`logs/architecture-coverage-reverify.log`） |
| PostgreSQL 可用性 | `psql`/`pg_ctl` 不在 PATH；`TEST_DATABASE_URL` 未设置 |
| 迁移/驱动依赖 | `uv.lock` 40 个包中 **无 alembic/sqlalchemy/psycopg** |
| G03 沙箱 | `G03: 13/28`，构成为 `1 + 4 + 2×4`（见 D7） |

**数字澄清**：DSH 报 `11/28`，我跑出 `13/28` —— 差在它那两份文档落盘后新增两条 `docs:` 通过（11 + 2 = 13），机制与它自己解释的完全一致。

**未执行项（如实记录，不臆造成功）**：

- `alembic upgrade/downgrade`、任何真机迁移/快照/并发提交/回滚断言：无 PostgreSQL、无 alembic，**未执行**。
- `npm ci`、前端工作区测试、`npm run test:e2e:list`、ruff：本轮**未重跑**。D8/D9/D10 标注 `reverified_this_pass: false`。
- `gates.py --phase 03`：**未写入官方记录**，改用 `--out-dir tmp/zcode-g03-dryrun-p4` 沙箱；`artifacts/gates/G03.json` 不存在，我也未创建。

## 3. 需求/用例覆盖情况

| 需求项（P03-04 Prompt） | 状态 |
| --- | --- |
| Objective / Files 交付对应 | **未交付**（代码/测试 0/5） |
| Test Case 1：两个事务争最后 1 个 dock → **恰好一方成功** | **无法验证**（无实现、无测试、无数据库；需两个真实并发事务） |
| Test Case 2：同幂等 key 不同 body → `IDEMPOTENCY_CONFLICT` | **无法验证**（错误码本身已冻结，期望明确，但无代码可跑） |
| `PlanCommitStore.commit(...)`（单事务，由 ScheduleService 调用） | **不可用**（`CommitCommand`/`ValidationReport`/`CommitReceipt` 全不存在，且按契约归属 P02-03） |
| 固定顺序锁资源行、复核版本与时段容量、CAS `active_version` | **未实现** |
| 原子写新版本/预留/审计/outbox | **未实现** |
| 相同 key 同 hash 返回原 receipt | **未实现** |
| 校验报告必须匹配候选与快照 hash | **未实现** |
| 此阶段不得公开正式提交路由 | 未触发（无代码），已列为重发后的门禁项 |
| 命令零用例视为未验收 | 触发（0 用例，exit 4） |

用例覆盖率 **0/2**。

## 4. 对 DSH 提交的复核（独立重算）

| DSH 主张 | 我的复核 | 结论 |
| --- | --- | --- |
| 7 个交付物未创建（刻意） | 逐路径检查 | 成立（真实 2/7，含两份文档；同样的写入后快照现象） |
| 命令 1 exit 4、命令 2 exit 0 属空洞 | 亲自重跑 + 读码 | 一致 |
| `G02` 无记录、`G01` failed、`P03-03` BLOCKED | 读 Gate/预验收 JSON | 成立 |
| 引用我上一轮的 P03-03 结论 | 读 `P03-03/zcode/precheck.json` | **引用正确**（BLOCKED、代码 0/5） |
| **契约把 `CommitCommand`/`ValidationReport`/`CommitReceipt` 归属 P02-03，且要求先定义后引用、禁止第二份同名定义** | 逐行读 `DATA_CONTRACTS.md` 24/55/56/79 | **逐行准确** |
| 刻意不新开 ARCH 条目（契约已裁决，登记会错误归因） | 判断复核 | **同意**：这是交付缺失，不是契约缺陷 |
| 自身证据的日志与输入哈希 | 独立重算 4 份日志 + 15 条输入哈希 | **全部一致** |
| "11/28 的增长只来自文档行" | 亲自跑出 13/28 并逐行归类 | 成立，且我的通式已覆盖到 N=4（D7） |
| 未夸大 | 通读 `reports/P03-04.md` | 成立；报告显式声明不声称未运行的测试通过 |

## 5. 确定缺陷清单（含路径与复现）

### D1 · 无实现候选【阻断本任务】

- 证据：第 1 节矩阵；`logs/cmd1-pytest.log`（exit 4）；`logs/gates-phase03-sandbox.log`；`logs/dsh-evidence-integrity.log`。`persistence/` 目录不存在，三个模块无父包。
- 归属：DSH / P03-04（前置解除后重做）。

### D2 · 前置未满足，且类型层被契约锁在 P02-03 之后【阻断本任务】

- `G02` 无记录（四轮探针 `5/27` 逐字节一致）；`P03-03` BLOCKED（代码 0/5）；`G01` failed（**5 条断言全部 passed**，仅缺交接记录）。
- 类型层：见第 0 节的契约逐行核对——`CommitCommand`/`ValidationReport`/`CommitReceipt` 归 P02-03，**禁止第二份同名定义**，所以 P02-03 未交付时 P03-04 无法实现。
- 依赖产物 **3/23**，三项都是前序任务自己的 BLOCKED 证据。
- 归属：Codex（G01 review）+ **ZCode（P01-01/02/03 预验收记录，本角色自身缺口）** + 角色 A/DSH（**P02 必须先行**）。

### D3 · 白名单不含所需依赖清单【阻断（重新下发时）—— 连续第四个任务同一缺口】

- `allowed_files` 7 项无 `apps/backend/pyproject.toml` 与 `uv.lock`；而 Test Case 1 需要两个真实并发事务（真 PostgreSQL + ORM/驱动）。
- **四个 Phase 03 任务全部复现**，已可判定为规划层缺口，应一次解决。

### D4 · 被双重引用的"Phase 01 环境手册"仍不存在【阻断验收】

- `tests/conftest.py:158` 与 `docs/architecture/IMPLEMENTATION_CONVENTIONS.md:9` 都引用它；`docs/` 下无对应文档；本机无 PostgreSQL。

### D5 · 架构检查器无法发现 ORM 泄漏出 adapter【阻断本任务核心义务的验收；本轮已复现验证】

- 场景 A（未声明 ORM）检出、场景 B（已声明 ORM，即 P03-01 必须造成的状态）**0 违规**（`logs/architecture-coverage-reverify.log`）。
- 对 P03-04 比对 P03-03 更关键：本任务的全部意义就在于**预留与版本写入都留在一个事务内、ORM 对象不外泄**，而验收标准 3 对这两点都无能为力。
- 归属：P01-02。

### D6 · 执行器仍无"前置受阻"状态，现已点名**全部四个** Phase 03 任务【非阻断，契约缺口】

- `dsh-evidence:P03-01/02/03/04` 全部 `unexpected status='BLOCKED'`。第四次显形，且本轮已达上限（Phase 03 就四个任务）。

### D7 · Gate 通过数因任务受阻而上升【非阻断，但会误导阅读者；本轮在 N=4 处确认通式】

- 五次测量：`5/28 → 7/28 → 9/28 → 11/28 → 13/28`；`13 = 1（G00）+ 4（空洞 cmd2）+ 2×4（四个任务的文档）`。
- **四个任务全部受阻时该计数器达到最大值，而已实现交付物为 0**。DSH 在 P03-03 与 P03-04 两轮独立记录同一观察。

### D8–D10 · 沿用项（非阻断，本轮未重跑）

- **D8**：`apps/frontend` 声明 `"test": "vitest run"` 但无 `devDependencies` → `ci.yml:95` 必跑步骤失败（P01-01 或 P24-01）。
- **D9**：`npm run test:e2e:list` 零 spec 时 exit 1，而 `ci.yml:98` 当必跑步骤（P01-02）。
- **D10**：ruff 配了规则集但无任何 CI 步骤调用；`RUF001/RUF002` 与中文全角标点约定冲突（工程配置）。

### D11 · Gate revision 由易失文件构成【非阻断，P01-02】

- 本轮再次证实（写记录本身即推动标签）。DSH 已在四份 Phase 03 交接里独立复现，双方结论一致。

### D12 · `_PENDING_APIS` 观察项【观察项，P01-01】

- `ports` 已登记且责任人正确（P03-03 轮已验证）；仍缺登记的只有 Phase 02 的 `planning`/`execution`/`runtime`/`common`。

## 6. 正面发现（请 Codex 不要改动）

1. **`conftest` 的数据库护栏依然有效**：缺库或缺驱动是 `pytest.fail` 而非 skip，并拒绝库名不含 `test` 的 URL 与默认/生产库。本任务的并发提交用例**不可能静默跳过冒充通过**。
2. **DSH 四次都拒绝在无前置时写实现**，本轮还给出了纸面级的契约依据并**主动不登记** ARCH 条目，避免把交付缺失错误归因给契约——这个判断很关键，我同意并复核了其引用。
3. **DSH 连续两轮主动纠正对自己有利的数字**（不把 9/28、11/28 当进展），并把它写进 `systemic_finding`。
4. **`IDEMPOTENCY_CONFLICT` 已在冻结错误表内**：本任务的两条用例期望都有契约来源，无需自造错误码。

## 7. 给 Codex 的重点风险与复核优先级

1. **最先做的一件事：把 G01 补到 26/26**（见第 0.1 节，已实测：4 个文件、0 行代码）。其中 3 份 `P01-0x/zcode/precheck.json` 是**本角色自己的欠账**，1 份 `G01-codex-review.json` 属 Codex。**顺序上先决定"加锁依赖 vs G01 签收"的先后**，否则 G01 会被迫签两次。
2. **Phase 03 应视为"零实现的阶段"并停止逐个重发任务**：四个任务全部 BLOCKED、代码交付 0/21、`G03` 无组装路径，且每多发一个任务只会让 Gate 通过数 +2（D7）。
3. **顺序不可颠倒：P02 必须先于 P03**。这不只是依赖图要求，而是**契约文本要求**——`CommitCommand`/`ValidationReport`/`CommitReceipt` 归 P02-03，且禁止第二份同名定义（`DATA_CONTRACTS.md:24/55/56/79`）。绕不过去。
4. **`G01` 只差交接记录，不差技术**：5 条断言全 passed；缺 3 份 P01 预验收记录（**ZCode 自己的账**）与 1 份 `G01-codex-review.json`（Codex）。这是整条链唯一的源头。
5. **D5 请在任何一个 Phase 03 存储任务重发之前处置**：否则"事务不变量 + ORM 不外泄"这类最关键义务的验收永远是空洞通过。
6. **重新下发 P03-04 时，验收要点**（已写入 `acceptance_recheck_plan` 共 10 条）：两个真实并发事务争最后一个 dock 必须**恰一成功**且失败方不留预留/版本/审计；同 key 同 body 必须返回**原 receipt 且不二次写入**；提交中途失败**不留半状态**且 `active_version_id` 不变；校验报告必须匹配候选与快照 hash，不匹配即中止且无副作用；资源行必须按**固定顺序**加锁（反向顺序的两个提交不得死锁）；`active_version_id` 必须用 CAS；**不得新增 HTTP 路由**；版本/预留/审计/outbox 必须在**一个**事务内；DSN 必须是 postgresql 而非 sqlite。
7. **不要把"未执行"读成"未通过"**：G03 的四条出口断言**从未运行过**，任何人不得把它们转述为已通过或已失败。
8. **`gates.py --check-only` 的 exit 0 不代表阶段就绪**；真实结论请用非官方 `--out-dir` 沙箱（我留了 `tmp/zcode-g03-dryrun-p4/G03.json`）。
9. **幂等与并发安全属安全相关不变量**，不只是业务规则：P03-04 是项目第一处反重放控制（同 key 同 body 不得二次写入），其行为从未被执行过。

## 8. 我修改了什么（供 Codex 独立查验）

**修改的生产代码/测试/既有文档：无。** 未改动 `packages/`、`tests/`、`scripts/`、`contracts/`、`apps/`、`docs/implementation/`、`docs/plan/`、`docs/architecture/` 下任何文件；**也未改动 DSH 的任何记录**（`docs/handoffs/P03-04/dsh.md`、其 evidence、3 份日志、两份 BLOCKED 报告均只读并只做哈希）。

**新增文件（仅本角色预验收产物）**：

- `docs/handoffs/P03-04/zcode.md`（本报告）
- `artifacts/handoffs/P03-04/zcode/evidence.json` 与同内容的 `precheck.json`（`status=BLOCKED`，fail-closed）
- `artifacts/handoffs/P03-04/zcode/build-evidence.py`（可复跑：只读仓库、不启进程、不拼 shell、revision 现场计算）
- `artifacts/handoffs/P03-04/zcode/logs/`（8 份日志，含契约引用核对与架构覆盖复现）
- `tmp/zcode-g03-dryrun-p4/`（G03 非官方沙箱证据，位于 gitignored 的 `tmp/`）

**复用了上一轮我自己的探针** `artifacts/handoffs/P03-03/zcode/probe-architecture-coverage.py`（只读仓库 + 系统临时目录内构造两场景），本轮重跑后把 D5 标为 `reverified_this_pass: true`，而不是原样搬运旧结论。

**DSH 原报告：完整保留**（第 12 节列出路径）。

## 9. 记录落盘约定（因 `ARCH-0004` 而需项目侧确认）

- 用户指令：`docs/handoffs/P03-04/zcode.md` + `artifacts/handoffs/P03-04/zcode/evidence.json` + 原始日志。
- Gate 执行器硬编码：`artifacts/handoffs/P03-04/zcode/precheck.json`（校验 `status == "Z_PRECHECK_PASSED"` 且输入哈希未漂移）。
- 两者不冲突，故**同时落盘**（内容一致）。`status` 取 `BLOCKED`，执行器会失败关闭，这是期望行为。**DSH 补交实现后需重新发起预验收，不能沿用本记录。**
- 本轮同样**未创建** `artifacts/gates/G03.json`，未签收任何 Gate。

## 10. 已修复 / 未修复 / 未验证清单

**已修复**：无（无可修复对象；本角色不代替开发）。

**未修复（已定位、需责任方处理）**：

| 编号 | 摘要 | 责任任务 | 阻断 |
| --- | --- | --- | --- |
| D1 | 无实现候选（代码/测试 0/5） | DSH / P03-04（前置解除后重做） | 是（本任务） |
| D2 | G02 无记录 + P03-03 BLOCKED + G01 failed + **类型归 P02-03**（依赖 3/23） | Codex + **ZCode（P01 预验收记录）** + DSH（**P02 先行**） | 是（本任务） |
| D3 | 白名单不含依赖清单（四个 Phase 03 任务全部复现） | 项目管理/规划侧 | 是（重新下发时） |
| D4 | 被引用的"Phase 01 环境手册"不存在 | 项目管理侧 / Phase 01 文档 owner | 是（验收侧） |
| D5 | 架构检查器无法发现 ORM 泄漏出 adapter | P01-02 | 是（本任务核心义务的验收） |
| D6 | 执行器无"前置受阻"状态（已点名全部四个任务） | P01-02 + `ARCH-0004` | 否（契约缺口） |
| D7 | Gate 通过数因任务受阻而上升（1+4+2N，N=4 达最大） | P01-02 | 否（误导性指标） |
| D8 | 前端 `vitest` 未安装 → CI frontend job 失败 | P01-01（或 P24-01） | 否 |
| D9 | `test:e2e:list` 空结果 exit 1 与 CI 必跑步骤矛盾 | P01-02 | 否 |
| D10 | ruff 未入 CI 且与中文标点约定冲突 | 工程配置 | 否 |
| D11 | Gate revision 由易失文件构成 | P01-02 | 否 |
| D12 | `_PENDING_APIS` 仍缺 Phase 02 模块名 | P01-01 | 否（观察项） |

**未验证 / 无法验证（不臆造通过）**：

- **P03-04 全部业务要求**（两条用例、`commit` 接口、CAS/幂等/原子性、固定锁序）——**UNVERIFIED**。
- **G03 的四条出口断言从未被任何任务执行过**。
- 静态类型检查：未配置 mypy/pyright。
- 本轮未重跑前端检查（D8/D9）、ruff（D10）、`npm ci`。
- CI 本体：本检出**无 `.git`**，`ci.yml` 的 git 相关步骤无法按其原文执行。

## 11. 基础安全检查（针对当前变更集）

当前变更集 = DSH 的证据文档 + 两份 BLOCKED 报告，无产品代码；由于本任务将落地 Phase 03 风险最高的一层，我把重发后必须满足的控制写进记录：

- **凭据**：目标树无 `.env`/`.env.*`/`*.pem`/`*.p12`/`id_rsa*`；`sk-…`/`AKIA…` 字面量 0 命中。
- **`TEST_DATABASE_URL` 处理**：只检查"是否设置"，**未回显、未连接**；记录仅含 `test_database_url_set: false`。
- **SQL 注入入口**：当前无数据库访问代码 —— **该条件在本任务范围内不适用、而非"已通过"**。本任务会写幂等记录与预留，"所有外部输入必须参数绑定、不得拼接/format/f-string"已列为其重发后的门禁项。
- **幂等与反重放（安全相关）**：同 key 同 body 必须返回**原 receipt 且不产生第二次写入**，同 key 不同 body 必须拒绝。这是项目第一处反重放控制，**从未被执行过**。
- **并发安全**：固定锁序要求的存在就是为了避免并发提交死锁；从未验证，且死锁倾向只有在真实并发下才暴露。
- **命令注入**：`apps/`、`packages/`、`scripts/`、`tests/` 中无 `shell=True`、`os.system`、`eval(`、`exec(`、`pickle.loads`；Gate 执行器与 `conftest` 均用 argv 数组；**本轮我自己的脚本不启进程、不拼 shell**（已过 ruff）。
- **数据库访问护栏（正面）**：`conftest._assert_test_database` 拒绝库名不含 `test` 的 URL 与默认/生产库。
- **依赖变化**：本次无变更；`uv lock --check` exit 0（这正是 D3 的症结：**要在受控变更下加入 DB 依赖，而不是绕过锁**）。
- **未对外部生产目标做任何扫描**：只探测本机工具可用性与环境变量；探针实验全部在系统临时目录内完成并已清理。

## 12. 证据索引

| 证据 | 路径 |
| --- | --- |
| 机器证据（输入哈希、交付/依赖矩阵、DSH 复核、**契约引用核对**、**类型链耦合**、**Phase 03 收口**、重验清单、缺陷表） | `artifacts/handoffs/P03-04/zcode/evidence.json` |
| Gate 执行器约定记录（同内容，`status=BLOCKED`） | `artifacts/handoffs/P03-04/zcode/precheck.json` |
| 证据生成脚本 | `artifacts/handoffs/P03-04/zcode/build-evidence.py` |
| 契约引用核对（本轮新增） | `logs/contract-citation-check.log` |
| **G01 缺口实测（本轮新增，沙箱、不签收）** | `logs/g01-diagnostic.log`；产物 `tmp/zcode-g01-diagnostic/G01.json` |
| **屏障诊断主张复核（本轮新增）** | `logs/g01-claim-verification.log`；被核对文档 `docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md` |
| 架构覆盖复现（本轮重跑） | `logs/architecture-coverage-reverify.log`；探针脚本 `artifacts/handoffs/P03-03/zcode/probe-architecture-coverage.py` |
| P03-04 强制命令日志（2 条） | `logs/cmd1-pytest.log`、`logs/cmd2-architecture.log` |
| 回归与基线日志 | `logs/regression-pytest.log`、`logs/baseline-checks.log` |
| G03 沙箱证据 | `logs/gates-phase03-sandbox.log`；`tmp/zcode-g03-dryrun-p4/G03.json`、`tmp/zcode-g03-dryrun-p4/G03-logs/` |
| DSH 证据独立重算 | `logs/dsh-evidence-integrity.log` |
| **DSH 原报告（保留，未改动）** | `docs/handoffs/P03-04/dsh.md`、`artifacts/handoffs/P03-04/dsh/evidence.json`、`artifacts/handoffs/P03-04/dsh/logs/`、`docs/implementation/P03-04.md`、`docs/implementation/reports/P03-04.md` |
| 上游 Gate / 任务状态 | `artifacts/gates/G00.json`（passed）、`G01.json`（failed）、`G02` 无记录、`P03-01`/`P03-02`/`P03-03` 的 zcode precheck（均 BLOCKED） |
| D11 复现 | `artifacts/handoffs/P02-02/zcode/logs/revision-volatility.log`；DSH 四份 Phase 03 交接的 `revision_label_is_self_perturbing` |
| P03-04 任务书 / 依赖图 / 冻结文档 | `docs/prompts/03-database/P03-04-atomic-version-store.md`、`TASK_GRAPH.md`、`docs/plan/{TASK_MANIFEST.json,PHASE_GATES.md}`、`docs/architecture/{DOMAIN_CATALOG.md,DATA_CONTRACTS.md,IMPLEMENTATION_CONVENTIONS.md}`、`tests/conftest.py` |
| 架构问题登记 | `docs/architecture/issues/README.md`（`ARCH-0003`、`ARCH-0004`、`ARCH-0005` 与本报告相关） |
