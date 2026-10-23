# P03-02 · ZCode → Codex 独立预验收报告

| 项目 | 值 |
| --- | --- |
| Task ID | `P03-02`（创建不可变计划、运行与审计迁移；Phase 03 第 2 个任务，负责方 A） |
| 审查角色 | ZCode 独立预验收（**不是**开发方，DSH 的开发身份不覆盖本角色的审查职责） |
| 审查对象 | 仓库当前 candidate（`D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，与 DSH 同一项目、同一候选；本仓库无 `.git`，按整体内容哈希定位） |
| 本角色状态 | **`BLOCKED`**（与 DSH 自报的 BLOCKED 一致，其全部依据已独立复现） |
| 阶段 Gate | `G03`（未签收；前置 `G02` 无记录、`P03-01` 为 BLOCKED、传递前置 `G01` 为 `failed`）；**本报告不签收任何 Gate** |
| 证据入口 | `artifacts/handoffs/P03-02/zcode/evidence.json`、`artifacts/handoffs/P03-02/zcode/logs/`（6 份命令日志） |
| 审查时间 | 2026-09-15（本机时区） |

## 0. 结论（先读这一段）

**P03-02 没有实现候选：5 个代码/测试交付物一个都不存在，只有两份"BLOCKED 报告"文档被写出（交付路径 2/7 存在，代码与测试 0/5）。**

与 P03-01 一样，DSH 提交了一份**诚实声明自己 BLOCKED** 的交接（`docs/handoffs/P03-02/dsh.md`、`artifacts/handoffs/P03-02/dsh/evidence.json`），我没有采信而是逐条复核：4 份命令日志哈希、15 条输入哈希全部重算一致；它引用的**我上一轮的 P03-01 结论也引用正确**；环境与依赖结论全部复现。

**本轮我给 DSH 的核心论证补上了一条结构性证据**：P03-02 并不是"差一点"，而是**与 P03-01 同属一条迁移链、无法独立成立**——

- `0002_planning_runtime.py` 是同一条 Alembic 链的第二个版本，而 `alembic.ini`、`apps/backend/migrations/env.py`、`0001_resources.py` **全部不存在，`apps/backend/migrations/` 目录本身都不存在**；单写 0002 只会得到 `down_revision` 悬空的迁移。
- 更硬的一条：**Test Case 2「删除被 V1 引用的 Order => 拒绝」要求 `orders` 表存在**，而那张表本应由 P03-01 的 0001 创建。也就是说这条用例**必须同时依赖两个迁移**才能断言。
- `DOMAIN_CATALOG.md:60` 明确"外键删除默认 RESTRICT"，所以"拒绝"必须由数据库层保证，不能靠应用层绕过。

因此本任务的阻断不是保守，而是**结构必然**；判定 **`BLOCKED`**。

复核者需要的最小动作见第 7 节。与前两轮相同，必须点名：**`G01` 失败的唯一剩余原因仍是缺 3 份 P01-01/02/03 的 ZCode 预验收记录 + 1 份 Codex review**（G01 的 5 条断言全部 passed），前 3 份是**我这一侧的账**。

## 1. 目标、白名单与契约核对

- **任务 Prompt 即验收需求**：`docs/prompts/03-database/P03-02-planning-schema.md`（哈希见 evidence.json 的 `verified_input_hashes`）。
- **白名单（Files，7 项）**：`apps/backend/migrations/versions/0002_planning_runtime.py`、`apps/backend/src/logistics_backend/persistence/planning_models.py`、`apps/backend/src/logistics_backend/persistence/runtime_models.py`、`docs/implementation/P03-02.md`、`docs/implementation/reports/P03-02.md`、`tests/integration/test_p03_02_planning_schema.py`、`tests/unit/test_p03_02_planning_schema.py`。manifest 的 `allowed_files` = 7，与 Prompt 一致，**口径无分歧**。
- **存在性矩阵**：**2/7 存在，且两项都是 BLOCKED 报告文档**；5 个代码/测试路径 **0/5**。
  - 再次更正一个数字快照（与 P03-01 同样的现象）：DSH 记录的 `deliverable_present_count` 是 **0/7**，但那两份文档在它写完记录之后才落盘。真实状态 **2/7**。DSH 在 `files_created_by_dsh` 里如实列出了这两份文档，所以不是误报，只是机器字段是写入前的快照。
- **依赖核对**：`TASK_MANIFEST.json` 的 P03-02 deps = `["G02", "P03-01"]`，`TASK_GRAPH.md:59` 一致。实测：`artifacts/gates/G02.json` **不存在**；`P03-01` 的 DSH 证据与 ZCode 预验收**都是 `BLOCKED`**，其代码交付 **0/6**；`G01` = `failed`。evidence.json 的 `dependency_presence` 给出 19 个依赖产物的存在性：**1/19 存在，而这 1 项恰恰是 P03-01 的"BLOCKED 证据"本身**——它是受阻报告，不是已交付的能力。
- **冻结接口**：`persist_version(version: ScheduleVersionDTO) -> VersionRef`。实测 `ScheduleVersionDTO`、`VersionRef`、`ScheduleVersion`、`Job`、`Outbox`、`AuditEntry` **全部不存在**（`packages/domain` 只有 P01-01 的 `__init__.py` 空壳）。
- **契约文档**：`docs/workflow/README.md`、`HANDOFF_CONTRACT.md` 不存在（既有 `ARCH-0004`）。我按"用户指令 + Gate 执行器硬编码约定"两处落盘（第 9 节）。

## 2. 强制命令实跑结果（原始日志逐条保留）

| 命令 | 我的实测 | DSH 报告 | 一致性 |
| --- | --- | --- | --- |
| `uv run pytest tests/unit/test_p03_02_planning_schema.py tests/integration/test_p03_02_planning_schema.py -q` | `file or directory not found`；`no tests ran in 0.00s`；**exit 4** | exit 4、0 用例 | 一致 |
| `uv run python scripts/check_architecture.py` | `7 module(s) across 7 layer(s); violations=0`；**exit 0** | exit 0（DSH 自标为空洞通过） | 一致 |

**第二条命令的 exit 0 不构成通过证据**，DSH 自己也标注了：扫到的 7 个模块仍是 P01-01 的空壳，本任务零新增代码。这不只是"没有意义"，更危险的是**它会在任何阶段让"零新增代码"看起来像"分层检查通过"**——G03 断言里的分层项必须与"schema 已存在"联合判定。

**额外实跑的本任务关键检查**：

| 检查 | 结果 |
| --- | --- |
| Alembic 链完整性 | `alembic.ini`、`migrations/env.py`、`0001_resources.py` **全部缺失**，`apps/backend/migrations/` 目录不存在 → 0002 会是悬空的第二环 |
| PostgreSQL 可用性 | `psql`/`pg_ctl` 不在 PATH；`TEST_DATABASE_URL` 未设置 |
| 迁移/驱动依赖 | `uv.lock` 40 个包中 **无 alembic / sqlalchemy / psycopg**（P03-02 的"迁移往返检查"因此无从执行） |
| G03 沙箱 | `G03: 9/28`；`previous-gate:G01 failed`、`previous-gate:G02 missing`；`dsh-evidence:P03-01/P03-02` 均 `unexpected status='BLOCKED'`；`zcode-precheck:P03-01 BLOCKED`、`P03-02 missing`；4 条 `P03-0X-cmd1` 全 exit 4 |

**一个需要澄清的数字**：DSH 报告 `G03: 7/28`，我这次跑出 `G03: 9/28`。两者都对——差在 DSH 探针时它那两份文档还没落盘，而现在 `docs:docs/implementation/P03-02.md: present` 与 `reports/P03-02.md: present` 两条通过（7 + 2 = 9）。DSH 自己在报告里也正确解释了上一轮 5/28 → 7/28 的同源变化，说明它读懂了执行器语义。

**未执行项（如实记录，不臆造成功）**：

- `alembic upgrade head` / `downgrade`、任何真机迁移/回滚/FK/唯一约束断言：无 PostgreSQL、无 alembic，**未执行**。
- `npm ci`、前端工作区测试、`npm run test:e2e:list`：本轮**未重跑**（P03-02 的 Files 不涉及前端）。D6/D7/D8 沿用 2026-09-14 证据并标注 `reverified_this_pass: false`。
- `uv run python scripts/gates.py --phase 03 --revision auto`：**未写入官方记录**。改用 `--out-dir tmp/zcode-g03-dryrun-p2` 沙箱运行；`artifacts/gates/G03.json` 不存在，我也未创建。

## 3. 需求/用例覆盖情况

| 需求项（P03-02 Prompt） | 状态 |
| --- | --- |
| Objective / Files 交付对应 | **未交付**（代码/测试 0/5） |
| Test Case 1：同 schedule 两个 `version_no=2` → 拒绝 | **无法验证**（无实现、无测试、无数据库） |
| Test Case 2：删除被 V1 引用的 Order → 拒绝 | **无法验证**（同上；且需 P03-01 的 `orders` 表） |
| 接口 `persist_version(ScheduleVersionDTO) -> VersionRef` | **不可用**（两个类型都不存在） |
| `ScheduleVersion` 内容与审计追加不可覆盖 | **未实现** |
| `active_version_id` 单独保存 | **未实现** |
| 唯一 `(schedule_id, version_no)` | **未实现** |
| JSONB 带 `schema_version` | **未实现** |
| 计划任务按 `(version_id, task_id)` 关联 | **未实现** |
| 金额 `bigint` | **未实现** |
| 索引覆盖 job 状态 / 事件游标 / `parent_version_id` | **未实现** |
| 迁移往返检查 | **不可执行**（锁内无 alembic） |
| domain 不导入框架（分层约束） | 当前 `violations=0`，但属空壳状态，不能代表交付 |
| Unit + Integration 两条测试命令零用例视为未验收 | 触发（0 用例，exit 4） |

用例覆盖率 **0/2**。按 Prompt"命令零用例或关键skip视为未验收"，本任务在任何解释下都不成立。

## 4. 对 DSH 提交的复核（独立重算）

| DSH 主张 | 我的复核方式 | 结论 |
| --- | --- | --- |
| 7 个交付物未创建（刻意） | 逐路径存在性检查 | 成立（真实 2/7，含两份报告文档；见第 1 节更正） |
| 命令 1 exit 4 / 0 用例 | 亲自重跑 | 一致 |
| 命令 2 exit 0 属空洞通过，不得引用 | 亲自重跑 + 读码 | 一致 |
| 同阶段前置 `P03-01` BLOCKED（含引用我的原文） | 读 `artifacts/handoffs/P03-01/zcode/precheck.json` | **引用正确**：status=BLOCKED、`signs_gate=false`、代码 0/6 |
| `G02` 无记录、`G01` failed、Phase 02 交付 0/15 | 读 Gate JSON + 逐路径检查 | 成立 |
| 0002 无法单独写（`down_revision` 悬空） | 检查 `alembic.ini`/`env.py`/`0001` 与 `migrations/` 目录 | **成立且我补充了更硬的证据**（Test Case 2 需要 0001 的 `orders` 表） |
| 自身证据的日志与输入哈希 | 独立重算 4 份日志 + 15 条输入哈希 | **全部一致**，无漂移 |
| 未夸大、未声称未运行的测试通过 | 通读 `reports/P03-02.md` | 成立；报告显式声明"不声称任何未运行的测试通过""不声称 P03-02 已实现" |

两处数字快照更正（0/7 → 2/7；7/28 → 9/28）都不影响其结论。

## 5. 确定缺陷清单（含路径与复现）

### D1 · 无实现候选【阻断本任务】

- 证据：第 1 节存在性矩阵；`logs/cmd1-pytest.log`（exit 4、0 用例）；`logs/gates-phase03-sandbox.log`；`logs/dsh-evidence-integrity.log`。
- 归属：DSH / P03-02（**刻意未开始**，理由见 D2 与本报告第 0 节的结构性论证，判断正确）。

### D2 · 两个声明依赖均未满足【阻断本任务】

- `artifacts/gates/G02.json` 不存在（Phase 02 探针 `5/27`，交付文件 0/15）。
- `P03-01`：DSH 证据与 ZCode 预验收均为 `BLOCKED`，代码交付 0/6。
- `G01`：`failed`，且其 5 条验收断言**全部 passed** —— 卡住的唯一原因是缺交接记录。
- evidence.json 的 `dependency_presence`：**1/19**，唯一存在的那项还是 P03-01 的 BLOCKED 报告本身。
- 归属：Codex（G01 review）+ **ZCode（P01-01/02/03 预验收记录，本角色自身缺口）** + 角色 A/DSH（P02-01→04，然后 P03-01→02）。

### D3 · 白名单不含它需要的依赖清单（重新下发仍失败）【阻断（重新下发时）】

- `allowed_files` 7 项中**没有 `apps/backend/pyproject.toml` 与 `uv.lock`**；而 `uv.lock` 无 alembic/sqlalchemy/psycopg，本任务的两条用例又都是数据库级断言，`conftest` 的 `db_connection` 要求 psycopg 已安装。
- 与 P03-01 同一缺陷（那里我记为 D3），**说明这是跨任务的规划缺口，不是单任务疏忽**。建议一次解决：把依赖清单加入 Phase 03 任务白名单并授权 `uv add`，或另设依赖引入任务。

### D4 · 被双重引用的"Phase 01 环境手册"仍不存在【阻断验收】

- `tests/conftest.py:158` 与 `docs/architecture/IMPLEMENTATION_CONVENTIONS.md:9` 都引用它（后者明确要求写清 Docker 与本地 PostgreSQL 两种启动方式）；`docs/` 下无任何对应文档。

### D5 · Gate 执行器没有"前置受阻"状态，现已点名两个诚实报告的任务【非阻断，契约缺口】

- 本轮 `dsh-evidence:P03-01` 与 `dsh-evidence:P03-02` **同时**被判 `unexpected status='BLOCKED'`。这是同一契约缺口第二次显形，且随受阻任务增多会持续累积噪音。建议二选一：承认 BLOCKED 并给出专门措辞，或在交接契约中规定受阻时不得写入 `artifacts/handoffs/<task>/dsh/`。

### D6–D8 · 沿用项（非阻断，本轮未重跑）

- **D6**：`apps/frontend` 声明 `"test": "vitest run"` 但无 `devDependencies` → `ci.yml:95` 必跑步骤失败（P01-01 或 P24-01）。
- **D7**：`npm run test:e2e:list` 零 spec 时 exit 1，而 `ci.yml:98` 当必跑步骤（P01-02）。
- **D8**：ruff 配了规则集但无任何 CI 步骤调用；`RUF001/RUF002` 与中文全角标点约定冲突（工程配置）。

### D9 · Gate revision 由易失文件构成【非阻断，P01-02】

- 本轮再次被间接证实：写入本记录本身就会推动 revision 标签（故标签现场计算而非手抄）。**本轮 DSH 也第二次独立复现**（其交接的 `candidate.revision_label_is_self_perturbing`），三方独立结论一致，可作为定论。

### D10 · `_PENDING_APIS` 未登记 Phase 02/03 模块名【观察项，P01-01】

- `logistics_domain._PENDING_APIS` 与 `logistics_contracts._PENDING_APIS` 都不含 `planning`/`execution`/`runtime`/`common`，探测只得到裸 `AttributeError`。仅影响可诊断性。

## 6. 正面发现（请 Codex 不要改动）

1. **`conftest` 的数据库护栏仍然有效**：`database_url`/`db_connection` 在缺 `TEST_DATABASE_URL` 或缺 psycopg 时 `pytest.fail` 而非 skip，并拒绝库名不含 `test` 的 URL 与默认/生产库。Phase 03 的数据库用例**不可能静默跳过冒充通过**。
2. **DSH 两次都选择不写迁移**，并给出了正确的技术理由（链完整性 + Architecture Constraint 6）。若它当时"顺手"写了 0002，产出的迁移链会与将来的真实 0001 冲突，两条用例也很可能被 SQLite 或凭空 DDL 弄成假阳性。
3. **交接证据可自校验且跨轮引用准确**：DSH 记录的每个哈希我都能重算一致，它引用我上一轮的结论也一字不差。这种可复核性应成为后续默认做法。

## 7. 给 Codex 的重点风险与复核优先级

1. **`G01` 只差交接记录，不差技术**：5 条断言全 passed；缺 3 份 `artifacts/handoffs/P01-0X/zcode/precheck.json`（**ZCode 自己的账**）与 1 份 `artifacts/gates/G01-codex-review.json`（Codex）。这是整条链唯一的源头。
2. **Phase 02 仍是空仓**（0/15），`G02` 无记录；必须整链交付，逐个补预验收记录没有意义。
3. **P03-01 与 P03-02 必须作为一条链验收**：0002 依赖 0001，Test Case 2 的 FK 目标 `orders` 表在 0001 里。任何"只交付 0002"的方案都应直接拒绝。
4. **重新下发前先解决 D3 与 D4**，否则两个 Phase 03 任务会以完全相同的方式再次 BLOCKED——这是范围与环境的前置缺失，不是 DSH 的能力问题。
5. **不要把"未执行"读成"未通过"**：真机迁移/回滚/FK/唯一约束/并发恰一成功/事务无半版本这些 G03 断言**从未运行过**。
6. **不要用 `gates.py --check-only` 的 exit 0 判断阶段就绪**：从未签收的 Gate 上它是空操作（我留了 `tmp/zcode-g03-dryrun-p2/G03.json` 作为真实沙箱结果）。
7. **不可变语义是本任务的验收核心**：`ScheduleVersion` 内容与审计追加不可覆盖、`active_version_id` 单独存放在 `Schedule` 上——这三条正是 G03 最关键断言（一致快照、并发恰一成功、无半版本）的数据库基础，容易在"看起来能跑"的迁移里被做错。
8. **SQL 参数绑定**：当前无数据库访问代码，**该验收条件在本任务范围内不适用、而非已通过**；重新下发后应逐条检查是否存在拼接/format/f-string 组装 SQL。

## 8. 我修改了什么（供 Codex 独立查验）

**修改的生产代码/测试/既有文档：无。** 未改动 `packages/`、`tests/`、`scripts/`、`contracts/`、`apps/`、`docs/implementation/`、`docs/plan/`、`docs/architecture/` 下任何文件；**也未改动 DSH 的任何记录**（`docs/handoffs/P03-02/dsh.md`、其 `evidence.json`、其 3 份日志、两份 BLOCKED 报告均只读并只做哈希）。

**新增文件（仅本角色预验收产物）**：

- `docs/handoffs/P03-02/zcode.md`（本报告）
- `artifacts/handoffs/P03-02/zcode/evidence.json`
- `artifacts/handoffs/P03-02/zcode/precheck.json`（Gate 执行器约定的同内容记录，`status=BLOCKED`，fail-closed）
- `artifacts/handoffs/P03-02/zcode/build-evidence.py`（可复跑：只读仓库、不启进程、不拼 shell、revision 现场计算；含 DSH 证据独立重算）
- `artifacts/handoffs/P03-02/zcode/logs/`（6 份命令日志）
- `tmp/zcode-g03-dryrun-p2/`（G03 非官方沙箱证据 + 日志，位于 `.gitignore` 忽略的 `tmp/` 下）

**DSH 原报告：完整保留**，路径见第 12 节与 evidence.json 的 `preserved_dsh_report`。

## 9. 记录落盘约定（因 `ARCH-0004` 而需项目侧确认）

- 用户指令：`docs/handoffs/P03-02/zcode.md` + `artifacts/handoffs/P03-02/zcode/evidence.json` + 原始日志。
- Gate 执行器硬编码：`artifacts/handoffs/P03-02/zcode/precheck.json`，校验 `status == "Z_PRECHECK_PASSED"` 且 `verified_input_hashes` 未漂移。
- 两者不冲突，故我**同时落盘** `evidence.json` 与 `precheck.json`（内容一致）。`status` 取 `BLOCKED`：执行器会以 `status='BLOCKED' (expected 'Z_PRECHECK_PASSED')` 失败关闭，这是期望行为。**DSH 补交实现后需重新发起预验收，不能沿用本记录。**
- 本轮同样**未创建** `artifacts/gates/G03.json`，未签收任何 Gate。

## 10. 已修复 / 未修复 / 未验证清单

**已修复**：无（无可修复对象；本角色不代替开发）。

**未修复（已定位、需责任方处理）**：

| 编号 | 摘要 | 责任任务 | 阻断 |
| --- | --- | --- | --- |
| D1 | 无实现候选（代码/测试 0/5） | DSH / P03-02（前置解除后重做） | 是（本任务） |
| D2 | G02 无记录 + P03-01 BLOCKED + G01 failed（依赖 1/19） | Codex + **ZCode（P01 预验收记录）** + DSH | 是（本任务） |
| D3 | 白名单不含 `apps/backend/pyproject.toml`/`uv.lock`（跨任务规划缺口） | 项目管理/规划侧 | 是（重新下发时） |
| D4 | 被引用的"Phase 01 环境手册"不存在 | 项目管理侧 / Phase 01 文档 owner | 是（验收侧） |
| D5 | 执行器无"前置受阻"状态，已点名两个任务 | P01-02 + `ARCH-0004` | 否（契约缺口） |
| D6 | 前端 `vitest` 未安装 → CI frontend job 失败 | P01-01（或 P24-01） | 否 |
| D7 | `test:e2e:list` 空结果 exit 1 与 CI 必跑步骤矛盾 | P01-02 | 否 |
| D8 | ruff 未入 CI 且与中文标点约定冲突 | 工程配置 | 否 |
| D9 | Gate revision 由易失文件构成（三方独立复现） | P01-02 | 否 |
| D10 | `_PENDING_APIS` 未登记 Phase 02/03 模块名 | P01-01 | 否（观察项） |

**未验证 / 无法验证（不臆造通过）**：

- **P03-02 的全部业务要求**（两条 Test Case、`persist_version`、不可覆盖/`active_version_id` 独立/JSONB `schema_version`/`bigint`/索引覆盖、迁移往返）——**UNVERIFIED**：无实现、无数据库、无 alembic。
- G03 出口断言的大部分（真机迁移/回滚/FK、一致快照、并发恰一成功、无半版本）依赖 P03-03/P03-04。
- 静态类型检查：未配置 mypy/pyright。
- 本轮未重跑前端类检查（D6/D7）与 ruff（D8）、未重跑 `npm ci`。
- CI 本体：本检出**无 `.git`**，`ci.yml` 的 `git ls-files`、`git grep`、`git diff --exit-code -- package-lock.json` 无法按其原文执行。

## 11. 基础安全检查（针对当前变更集）

当前变更集 = DSH 的证据文档 + 两份 BLOCKED 报告，无产品代码；由于本任务终将引入数据库，我也把重新下发后必须满足的控制写进记录：

- **凭据**：目标树无 `.env`/`.env.*`/`*.pem`/`*.p12`/`id_rsa*`；`sk-…`/`AKIA…` 字面量 0 命中。
- **`TEST_DATABASE_URL` 处理**：只检查"是否设置"，**未回显内容、未发起连接**；记录仅含 `test_database_url_set: false`。
- **SQL 注入入口**：当前无数据库访问代码 —— **该验收条件在本任务范围内不适用，而非"已通过"**。已把"参数绑定、禁止字符串插值/format/f-string 组装 SQL"列为 Phase 03 任务重新下发后的门禁项。
- **命令注入**：`apps/`、`packages/`、`scripts/`、`tests/` 中无 `shell=True`、`os.system`、`eval(`、`exec(`、`pickle.loads`；Gate 执行器与 `conftest` 均以 argv 数组执行、不经 shell。
- **数据库访问护栏（正面）**：`conftest._assert_test_database` 拒绝库名不含 `test` 的 URL 并显式拒绝默认/生产库。
- **依赖变化**：本次无依赖变更；`uv lock --check` exit 0（注意：这也正是 D3 的症结——**需要在受控变更下加入 DB 依赖，而不是绕过锁**）。
- **未对外部生产目标做任何扫描**：只探测本机工具可用性与环境变量，未连接任何外部主机。

## 12. 证据索引

| 证据 | 路径 |
| --- | --- |
| 机器证据（输入哈希、交付/依赖矩阵、DSH 提交复核、链耦合、重验清单、缺陷表、日志清单） | `artifacts/handoffs/P03-02/zcode/evidence.json` |
| Gate 执行器约定记录（同内容，`status=BLOCKED`） | `artifacts/handoffs/P03-02/zcode/precheck.json` |
| 证据生成脚本（可复跑复现全部哈希） | `artifacts/handoffs/P03-02/zcode/build-evidence.py` |
| P03-02 强制命令日志（2 条） | `logs/cmd1-pytest.log`、`logs/cmd2-architecture.log` |
| 回归与工程基础日志 | `logs/regression-pytest.log`、`logs/baseline-checks.log` |
| G03 沙箱证据 | `logs/gates-phase03-sandbox.log`；`tmp/zcode-g03-dryrun-p2/G03.json`、`tmp/zcode-g03-dryrun-p2/G03-logs/` |
| DSH 证据独立重算 + Alembic 链检查 | `logs/dsh-evidence-integrity.log` |
| **DSH 原报告（保留，未改动）** | `docs/handoffs/P03-02/dsh.md`、`artifacts/handoffs/P03-02/dsh/evidence.json`、`artifacts/handoffs/P03-02/dsh/logs/`、`docs/implementation/P03-02.md`、`docs/implementation/reports/P03-02.md` |
| 上游 Gate / 任务状态 | `artifacts/gates/G00.json`（passed）、`G01.json`（failed）、`G02` 无记录、`artifacts/handoffs/P03-01/zcode/precheck.json`（BLOCKED） |
| D9 复现（双方独立） | `artifacts/handoffs/P02-02/zcode/logs/revision-volatility.log`；DSH 两份 Phase 03 交接的 `revision_label_is_self_perturbing` |
| P03-02 任务书 / 依赖图 / 冻结文档 | `docs/prompts/03-database/P03-02-planning-schema.md`、`TASK_GRAPH.md`、`docs/plan/{TASK_MANIFEST.json,PHASE_GATES.md}`、`docs/architecture/{DOMAIN_CATALOG.md,DATA_CONTRACTS.md,IMPLEMENTATION_CONVENTIONS.md}`、`tests/conftest.py` |
| 架构问题登记 | `docs/architecture/issues/README.md`（`ARCH-0004`、`ARCH-0005` 与本报告相关） |
