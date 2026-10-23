# P03-03 · ZCode → Codex 独立预验收报告

| 项目 | 值 |
| --- | --- |
| Task ID | `P03-03`（实现快照读取与事务工作单元；Phase 03 第 3 个任务，负责方 A） |
| 审查角色 | ZCode 独立预验收（**不是**开发方，DSH 的开发身份不覆盖本角色的审查职责） |
| 审查对象 | 仓库当前 candidate（`D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，与 DSH 同一项目、同一候选；本仓库无 `.git`，按整体内容哈希定位） |
| 本角色状态 | **`BLOCKED`**（与 DSH 自报一致，其全部依据已独立复现） |
| 阶段 Gate | `G03`（未签收；`G02` 无记录、`P03-02` 为 BLOCKED、`G01` 为 `failed`）；**本报告不签收任何 Gate** |
| 证据入口 | `artifacts/handoffs/P03-03/zcode/evidence.json`、`artifacts/handoffs/P03-03/zcode/logs/`（7 份日志） |
| 审查时间 | 2026-09-15（本机时区） |

## 0. 结论（先读这一段）

**P03-03 没有实现候选：5 个代码/测试交付物全部不存在，只有两份"BLOCKED 报告"文档（交付路径 2/7，代码与测试 0/5）。** 依赖 21 项中仅 2 项存在，而那两项正是 P03-01 与 P03-02 自己的 BLOCKED 证据记录——**受阻报告不是已交付的能力**。

判定 **`BLOCKED`**，与 DSH 一致，其依据我逐条复现（4 份日志哈希、17 条输入哈希全部一致；引用的前序结论正确）。

**本轮我做了两件 DSH 做不到的事，请 Codex 优先看这两条：**

### 新增 D5 · 架构检查器**无法**发现 ORM 泄漏出 adapter（已实测，非推测）

DSH 在自己的报告里把这个问题列为"无法验证"。我用两场景实验给出了确定答案：

| 场景 | 结果 |
| --- | --- |
| A：`apps/backend` **未**声明 sqlalchemy | 后端 API 层 `from sqlalchemy.orm import Session` → **1 条违规**（`ARCH-UNDECLARED`） |
| B：`apps/backend` **已**声明 sqlalchemy（**P03-01 必须造成的状态**） | 同一个文件 → **0 条违规，未被发现** |

原因是规则表结构：`LAYERS['backend']` 覆盖整个 `apps/backend/src` 作为**单一层**，没有 adapter 与 application 的子层规则；`THIRD_PARTY` 只把 `sqlalchemy`/`alembic`/`psycopg` 限制在 `domain` 层。所以场景 A 的检出**只是"依赖还没声明"的副产品**——P03-01 必须把 ORM 声明进去（否则持久化适配器根本无法工作），仓库就进入场景 B，**"ORM 不传出 adapter" 这条义务再无任何自动检查**。

后果很具体：P03-03 的验收标准 3 是"依赖边界检查通过"，而对该任务最关键的那条架构义务来说，它是**空洞通过**。一个把 SQLAlchemy `Session` 或 ORM 模型返回给应用层的仓储，仍然会得到 `violations=0`。

### 新增 D7 · Gate 通过数**会因任务受阻而上升**（已算术核实）

G03 的通过数四轮为 `5/28 → 7/28 → 9/28 → 11/28`，其构成为：

```
通过数 = 1（previous-gate G00）+ 4（四条空洞的 P03-0X-cmd2 架构行）+ 2 ×（只写了 BLOCKED 文档的 Phase 03 任务数）
```

11/28 的构成正是：1 + 4 + 6（三任务 × 2 份文档）。**每多一个受阻任务就白送 2 行**，而四个 `P03-0X-cmd1` 命令行全是 exit 4。也就是说**这个计数器与真实进展反相关**——只看通过数会以为 Phase 03 在推进。DSH 在自己的第 4 节独立得出了同一结论（它写明 7/28→9/28 的上升"全部来自文档行，通过的任务命令数未变，仍为 4/8"），并在 `systemic_finding SYS-1` 里记录了同一现象。我们双方独立结论一致，可作为定论。

## 1. 目标、白名单与契约核对

- **任务 Prompt 即验收需求**：`docs/prompts/03-database/P03-03-repositories-and-snapshot.md`。
- **白名单（Files，7 项）**：`apps/backend/src/logistics_backend/persistence/snapshots.py`、`.../uow.py`、`docs/implementation/P03-03.md`、`docs/implementation/reports/P03-03.md`、`packages/domain/src/logistics_domain/ports/storage.py`、`tests/integration/test_p03_03_repositories_and_snapshot.py`、`tests/unit/test_p03_03_repositories_and_snapshot.py`。manifest `allowed_files` = 7，与 Prompt 一致。
- **存在性矩阵**：**2/7 存在，两项均为 BLOCKED 报告文档**；代码/测试 **0/5**。
- **依赖核对**：`TASK_MANIFEST.json` deps = `["G02", "P03-02"]`，`TASK_GRAPH.md:60` 一致。实测 `G02` 记录不存在；`P03-02` 的 DSH 证据与 ZCode 预验收均 `BLOCKED`、代码 0/5；`G01` = `failed`。
- **冻结接口**：`PlanningSnapshotStore.capture(scope: PlanningScope) -> PlanningSnapshot; UnitOfWork.commit() -> None`。实测 `PlanningSnapshotStore`、`UnitOfWork`、`PlanningSnapshot`、`PlanningScope` 在 `apps|packages|tests|scripts` 下**零实现命中**。
- **一个值得记下的正面细节（D12 收窄）**：`logistics_domain._PENDING_APIS` **登记了** `ports`，且消息写明"P03-03/P06-01/P08-01/P11-01: framework-free Protocol definitions"，`Getting logistics_domain.ports` 会显式抛 `NotImplementedError` 并指明责任人。**P03-03 是第一个模块名被注册表预先覆盖的任务**——P01-01 的"失败即报"设计在这里正常工作。缺登记的只是 Phase 02 的 `planning`/`execution`/`runtime`/`common`。我为此收窄了此前 D10 的措辞，避免夸大。

## 2. 强制命令实跑结果（原始日志逐条保留）

| 命令 | 我的实测 | DSH 报告 | 一致性 |
| --- | --- | --- | --- |
| `uv run pytest tests/unit/test_p03_03_repositories_and_snapshot.py tests/integration/test_p03_03_repositories_and_snapshot.py -q` | `file or directory not found`；**exit 4**，0 用例 | exit 4、0 用例 | 一致 |
| `uv run python scripts/check_architecture.py` | `7 module(s) across 7 layer(s); violations=0`；**exit 0** | exit 0（DSH 自标空洞通过） | 一致 |

**对第二条命令，本轮有比"空洞通过"更严重的结论**：DSH 写道"`check_architecture.py` 能否真正发现 ORM 泄漏出 adapter：无持久化模块可违规，**无法验证**"。我把它验证成了确定结论——**不能发现**（见第 0 节 D5 与 `logs/architecture-coverage-probe.log`）。所以这条 exit 0 对本任务不仅是空洞的，而且**恰好覆盖不到本任务唯一重要的架构义务**。

**额外实跑的本任务关键检查**：

| 检查 | 结果 |
| --- | --- |
| 架构检查器覆盖实验（两场景） | 场景 A 检出（`ARCH-UNDECLARED`）、场景 B **0 违规**；探针脚本 `probe-architecture-coverage.py` 可复跑 |
| PostgreSQL 可用性 | `psql`/`pg_ctl` 不在 PATH；`TEST_DATABASE_URL` 未设置 |
| 迁移/驱动依赖 | `uv.lock` 40 个包中 **无 alembic/sqlalchemy/psycopg** |
| G03 沙箱 | `G03: 11/28`，构成见第 0 节 D7 |

**数字澄清**：DSH 报 `9/28`，我跑出 `11/28`——差在它那两份文档落盘后新增两条 `docs:` 通过（9 + 2 = 11），与它自己解释 7→9 的机制完全相同。

**未执行项（如实记录，不臆造成功）**：

- `alembic upgrade/downgrade`、任何真机迁移/快照/回滚/并发断言：无 PostgreSQL、无 alembic，**未执行**。
- `npm ci`、前端工作区测试、`npm run test:e2e:list`、ruff：本轮**未重跑**（P03-03 不涉及前端与 lint）。D8/D9/D10 标注 `reverified_this_pass: false`。
- `gates.py --phase 03`：**未写入官方记录**，改用 `--out-dir tmp/zcode-g03-dryrun-p3` 沙箱；`artifacts/gates/G03.json` 不存在，我也未创建。

## 3. 需求/用例覆盖情况

| 需求项（P03-03 Prompt） | 状态 |
| --- | --- |
| Objective / Files 交付对应 | **未交付**（代码/测试 0/5） |
| Test Case 1：并发更新车容量 → 单一快照不混合新旧读 | **无法验证**（无实现、无测试、无数据库；且需两个真实并发连接） |
| Test Case 2：UoW 内抛错 → 全部回滚 | **无法验证**（同上） |
| `PlanningSnapshotStore.capture` / `UnitOfWork.commit` | **不可用**（类型全不存在） |
| REPEATABLE READ 一致快照 | **未实现** |
| 快照包含矩阵与日历版本 | **未实现** |
| ORM 不传出 adapter | **未实现，且当前无自动检查可验证**（D5） |
| 规范化序列化计算 hash、DTO 映射到纯领域 snapshot | **未实现** |
| `ports/storage.py` 只对已冻结领域类型声明 Protocol | **未实现**（`ports/` 目录都不存在） |
| domain 不导入框架 | 当前 `violations=0`，属空壳状态，不能代表交付 |
| 命令零用例视为未验收 | 触发（0 用例，exit 4） |

用例覆盖率 **0/2**。

## 4. 对 DSH 提交的复核（独立重算）

| DSH 主张 | 我的复核 | 结论 |
| --- | --- | --- |
| 7 个交付物未创建（刻意） | 逐路径检查 | 成立（真实 2/7，含两份文档；同样的写入后快照现象） |
| 命令 1 exit 4 / 命令 2 exit 0 属空洞 | 亲自重跑 + 读码 | 一致 |
| 同阶段前置 `P03-02` BLOCKED、跨阶段 `G02` 无记录、`G01` failed | 读 Gate/预验收 JSON + 逐路径检查 | 成立 |
| 引用我上一轮的 P03-02 结论 | 读 `artifacts/handoffs/P03-02/zcode/precheck.json` | **引用正确**（BLOCKED、代码 0/5） |
| 自身证据的日志与输入哈希 | 独立重算 4 份日志 + 17 条输入哈希 | **全部一致** |
| 未夸大 | 通读 `reports/P03-03.md` | 成立；报告显式声明不声称未运行的测试通过 |
| "9/28 的上升全部来自文档行" | 亲自跑出 11/28 并逐行归类 | **成立且我给出了通式**（D7） |
| "`check_architecture.py` 能否发现 ORM 泄漏：无法验证" | 两场景实验 | **我补上了答案：不能发现**（D5） |

## 5. 确定缺陷清单（含路径与复现）

### D1 · 无实现候选【阻断本任务】

- 证据：第 1 节矩阵；`logs/cmd1-pytest.log`（exit 4）；`logs/gates-phase03-sandbox.log`；`logs/dsh-evidence-integrity.log`。
- 归属：DSH / P03-03（**刻意未开始**）。**其拒绝理由正确**：在领域类型冻结前先写 `ports/storage.py`，等于用 port 反推领域模型，正是 Architecture Constraint 6 禁止的"重复定义 Domain Model"。

### D2 · 两个声明依赖均未满足【阻断本任务】

- `G02` 无记录；`P03-02` BLOCKED（代码 0/5）；`G01` failed（**5 条断言全部 passed**，仅缺交接记录）。
- 依赖产物 **2/21**，且两项都是前序任务自己的 BLOCKED 证据。
- 归属：Codex（G01 review）+ **ZCode（P01-01/02/03 预验收记录，本角色自身缺口）** + 角色 A/DSH。

### D3 · 白名单仍不含所需依赖清单【阻断（重新下发时）—— 连续第三个任务同一缺口】

- `allowed_files` 7 项中无 `apps/backend/pyproject.toml` 与 `uv.lock`；而 Business Rules 要求 REPEATABLE READ + ORM 留在 adapter 内（即 sqlalchemy + 驱动），两条用例又都需要两个真实并发 PostgreSQL 连接。
- 已可判定：**这是规划层缺口，不是任务层疏忽**，应一次性解决。

### D4 · 被双重引用的"Phase 01 环境手册"仍不存在【阻断验收】

- `tests/conftest.py:158` 与 `docs/architecture/IMPLEMENTATION_CONVENTIONS.md:9` 都引用它；`docs/` 下无对应文档；本机无 PostgreSQL。

### D5 · 架构检查器无法发现 ORM 泄漏出 adapter【阻断本任务核心义务的验收】

- 见第 0 节。证据：`logs/architecture-coverage-probe.log`、探针脚本 `probe-architecture-coverage.py`、`scripts/check_architecture.py` 的 `LAYERS`/`THIRD_PARTY` 表。
- 建议：新增一条规则，只允许 `apps/backend/src/logistics_backend/persistence` 导入 ORM/驱动；并让预验收对该义务改用手工探针（我在 `acceptance_recheck_plan` 里已写明要求）。

### D6 · 执行器仍无"前置受阻"状态，已点名三个任务【非阻断，契约缺口】

- `dsh-evidence:P03-01/02/03` 全部 `unexpected status='BLOCKED'`，而每份任务书都要求前置缺失时报 BLOCKED。第三次显形，噪音随受阻任务线性增长。

### D7 · Gate 通过数因任务受阻而上升【非阻断，但会误导阅读者】

- 见第 0 节。建议把"任务命令行"与"文档行"分列统计，或让文档行不能掩盖"已实现交付物为 0"。

### D8–D10 · 沿用项（非阻断，本轮未重跑）

- **D8**：`apps/frontend` 声明 `"test": "vitest run"` 但无 `devDependencies` → `ci.yml:95` 必跑步骤失败（P01-01 或 P24-01）。
- **D9**：`npm run test:e2e:list` 零 spec 时 exit 1，而 `ci.yml:98` 当必跑步骤（P01-02）。
- **D10**：ruff 配了规则集但无任何 CI 步骤调用；`RUF001/RUF002` 与中文全角标点约定冲突（工程配置）。

### D11 · Gate revision 由易失文件构成【非阻断，P01-02】

- 本轮再次证实（写记录本身即推动标签，故标签现场计算）。DSH 已在三份 Phase 03 交接里独立复现同一现象，双方结论一致。

### D12 · `_PENDING_APIS` 观察项（本轮**收窄**）【观察项，P01-01】

- `ports` **已登记**且消息正确指向 P03-03 —— 本任务的设计意图正常工作。仍缺登记的只有 Phase 02 的 `planning`/`execution`/`runtime`/`common`。此前几轮我用了"未登记 Phase 02/03 模块名"的较宽措辞，本轮据实测收窄。

## 6. 正面发现（请 Codex 不要改动）

1. **`conftest` 的数据库护栏依然有效**：缺 `TEST_DATABASE_URL` 或缺 psycopg 时 `pytest.fail` 而非 skip，并拒绝库名不含 `test` 的 URL 与默认/生产库。P03-03 的两条并发/回滚用例**不可能静默跳过冒充通过**。
2. **DSH 第三次拒绝在无前置时写实现，且理由在架构上正确**（port 反推领域模型违反 Constraint 6）。
3. **DSH 主动纠正了对自己有利的数字**：它没有把 9/28 当作进展，而是主动说明"上升全部来自文档行、通过的任务命令数未变"。这是很少见的诚实。
4. **`ports` 的失败即报设计生效**：P03-03 的模块名已被注册表覆盖并带责任人——说明 P01-01 的设计本身没错，只是登记不全。

## 7. 给 Codex 的重点风险与复核优先级

1. **停止继续下发 Phase 03 任务**：P03-01/02/03 已连续三次产出同一份 BLOCKED 记录，且每次都让 Gate 通过数 +2（D7）。第四个任务只会再复现一次。建议把修复单位从"任务"改为"屏障"——这与 DSH 在 `SYS-1` 中的建议一致。
2. **`G01` 只差交接记录，不差技术**：5 条断言全 passed；缺 3 份 P01 预验收记录（**ZCode 自己的账**）与 1 份 `G01-codex-review.json`（Codex）。这是整条链唯一的源头。
3. **D5 请在 P03-03 重发之前处置**：否则它的验收标准 3 对本任务最关键的义务永远是空洞通过，一个泄漏 ORM 的实现也能拿到"依赖边界检查通过"。
4. **P03-01 → P03-02 → P03-03 是一条链**：0002 依赖 0001、Test Case 2 的 FK 目标 `orders` 在 0001、而 `snapshots.py` 要读这两者建出的表与 ORM 映射。任何"只交付其中一环"的方案都应直接拒绝。
5. **不要把"未执行"读成"未通过"**：G03 的"一致快照"断言正属本任务，当前**完全无证据**。
6. **Test Case 1 必须用两个真实并发连接复现**，不得用单连接或 SQLite 近似——这是该用例唯一有区分力的形式。
7. **`gates.py --check-only` 的 exit 0 不代表阶段就绪**（从未签收的 Gate 上它是空操作）；真实结论请用非官方 `--out-dir` 沙箱（我留了 `tmp/zcode-g03-dryrun-p3/G03.json`）。
8. **SQL 参数绑定**：P03-03 是第一个真正会发查询并涉及并发写的任务。当前仓库无数据库代码，**该条件在本任务范围内不适用、而非已通过**；重发后应逐条检查是否存在拼接/format/f-string 组装 SQL。

## 8. 我修改了什么（供 Codex 独立查验）

**修改的生产代码/测试/既有文档：无。** 未改动 `packages/`、`tests/`、`scripts/`、`contracts/`、`apps/`、`docs/implementation/`、`docs/plan/`、`docs/architecture/` 下任何文件；**也未改动 DSH 的任何记录**（`docs/handoffs/P03-03/dsh.md`、其 evidence、3 份日志、两份 BLOCKED 报告均只读并只做哈希）。

**新增文件（仅本角色预验收产物）**：

- `docs/handoffs/P03-03/zcode.md`（本报告）
- `artifacts/handoffs/P03-03/zcode/evidence.json` 与同内容的 `precheck.json`（`status=BLOCKED`，fail-closed）
- `artifacts/handoffs/P03-03/zcode/build-evidence.py`（可复跑的证据生成器）
- `artifacts/handoffs/P03-03/zcode/probe-architecture-coverage.py`（**本轮新增的覆盖实验探针**，只读仓库 + 在系统临时目录里构造两场景，不写仓库、不启进程）
- `artifacts/handoffs/P03-03/zcode/logs/`（7 份日志）
- `tmp/zcode-g03-dryrun-p3/`（G03 非官方沙箱证据，位于 gitignored 的 `tmp/`）

**DSH 原报告：完整保留**（第 12 节列出路径）。

## 9. 记录落盘约定（因 `ARCH-0004` 而需项目侧确认）

- 用户指令：`docs/handoffs/P03-03/zcode.md` + `artifacts/handoffs/P03-03/zcode/evidence.json` + 原始日志。
- Gate 执行器硬编码：`artifacts/handoffs/P03-03/zcode/precheck.json`（校验 `status == "Z_PRECHECK_PASSED"` 且输入哈希未漂移）。
- 两者不冲突，故**同时落盘**（内容一致）。`status` 取 `BLOCKED`，执行器会失败关闭，这是期望行为。**DSH 补交实现后需重新发起预验收，不能沿用本记录。**
- 本轮同样**未创建** `artifacts/gates/G03.json`，未签收任何 Gate。

## 10. 已修复 / 未修复 / 未验证清单

**已修复**：无（无可修复对象；本角色不代替开发）。

**未修复（已定位、需责任方处理）**：

| 编号 | 摘要 | 责任任务 | 阻断 |
| --- | --- | --- | --- |
| D1 | 无实现候选（代码/测试 0/5） | DSH / P03-03（前置解除后重做） | 是（本任务） |
| D2 | G02 无记录 + P03-02 BLOCKED + G01 failed（依赖 2/21） | Codex + **ZCode（P01 预验收记录）** + DSH | 是（本任务） |
| D3 | 白名单不含依赖清单（连续第三个任务） | 项目管理/规划侧 | 是（重新下发时） |
| D4 | 被引用的"Phase 01 环境手册"不存在 | 项目管理侧 / Phase 01 文档 owner | 是（验收侧） |
| D5 | **架构检查器无法发现 ORM 泄漏出 adapter** | P01-02 | 是（本任务核心义务的验收） |
| D6 | 执行器无"前置受阻"状态（已点名三个任务） | P01-02 + `ARCH-0004` | 否（契约缺口） |
| D7 | **Gate 通过数因任务受阻而上升（1+4+2N）** | P01-02 | 否（误导性指标） |
| D8 | 前端 `vitest` 未安装 → CI frontend job 失败 | P01-01（或 P24-01） | 否 |
| D9 | `test:e2e:list` 空结果 exit 1 与 CI 必跑步骤矛盾 | P01-02 | 否 |
| D10 | ruff 未入 CI 且与中文标点约定冲突 | 工程配置 | 否 |
| D11 | Gate revision 由易失文件构成（双方独立复现） | P01-02 | 否 |
| D12 | `_PENDING_APIS` 仍缺 Phase 02 模块名（本轮收窄） | P01-01 | 否（观察项） |

**未验证 / 无法验证（不臆造通过）**：

- **P03-03 全部业务要求**（两条用例、`capture`/`commit`、REPEATABLE READ、矩阵/日历版本、ORM 围栏、hash 稳定性）——**UNVERIFIED**：无实现、无数据库、无 alembic。
- G03 的"一致快照"断言**正属本任务，当前零证据**；其余出口断言依赖 P03-04。
- 静态类型检查：未配置 mypy/pyright。
- 本轮未重跑前端检查（D8/D9）、ruff（D10）、`npm ci`。
- CI 本体：本检出**无 `.git`**，`ci.yml` 的 git 相关步骤无法按其原文执行。

## 11. 基础安全检查（针对当前变更集）

当前变更集 = DSH 的证据文档 + 两份 BLOCKED 报告，无产品代码；由于本任务将首次发出查询并涉及并发写，我把重发后必须满足的控制写进记录：

- **凭据**：目标树无 `.env`/`.env.*`/`*.pem`/`*.p12`/`id_rsa*`；`sk-…`/`AKIA…` 字面量 0 命中。
- **`TEST_DATABASE_URL` 处理**：只检查"是否设置"，**未回显、未连接**；记录仅含 `test_database_url_set: false`。
- **SQL 注入入口**：当前无数据库访问代码 —— **该条件在本任务范围内不适用、而非"已通过"**。P03-03 是第一个会发查询的任务（快照读取 + 并发写），"所有外部输入必须参数绑定、不得拼接/format/f-string"已列为其重发后的门禁项。
- **事务安全**：UoW 是回滚正确性的所在；Test Case 2 就是项目对"无半状态"的控制项，而它**从未运行过**。
- **命令注入**：`apps/`、`packages/`、`scripts/`、`tests/` 中无 `shell=True`、`os.system`、`eval(`、`exec(`、`pickle.loads`；Gate 执行器与 `conftest` 均用 argv 数组。**本轮我新增的两个脚本（证据生成器、架构探针）也都不启进程、不拼 shell**（已过 ruff）。
- **数据库访问护栏（正面）**：`conftest._assert_test_database` 拒绝库名不含 `test` 的 URL 与默认/生产库。
- **依赖变化**：本次无变更；`uv lock --check` exit 0（这正是 D3 的症结：**要在受控变更下加入 DB 依赖，而不是绕过锁**）。
- **未对外部生产目标做任何扫描**：只探测本机工具可用性与环境变量；探针实验全部在系统临时目录内完成并已清理。

## 12. 证据索引

| 证据 | 路径 |
| --- | --- |
| 机器证据（输入哈希、交付/依赖矩阵、DSH 复核、**架构覆盖结论**、**通过数通式**、重验清单、缺陷表） | `artifacts/handoffs/P03-03/zcode/evidence.json` |
| Gate 执行器约定记录（同内容，`status=BLOCKED`） | `artifacts/handoffs/P03-03/zcode/precheck.json` |
| 证据生成脚本 | `artifacts/handoffs/P03-03/zcode/build-evidence.py` |
| **架构覆盖实验（本轮新增）** | `artifacts/handoffs/P03-03/zcode/probe-architecture-coverage.py`；输出 `logs/architecture-coverage-probe.log` |
| P03-03 强制命令日志（2 条） | `logs/cmd1-pytest.log`、`logs/cmd2-architecture.log` |
| 回归与基线日志 | `logs/regression-pytest.log`、`logs/baseline-checks.log` |
| G03 沙箱证据 | `logs/gates-phase03-sandbox.log`；`tmp/zcode-g03-dryrun-p3/G03.json`、`tmp/zcode-g03-dryrun-p3/G03-logs/` |
| DSH 证据独立重算 | `logs/dsh-evidence-integrity.log` |
| **DSH 原报告（保留，未改动）** | `docs/handoffs/P03-03/dsh.md`、`artifacts/handoffs/P03-03/dsh/evidence.json`、`artifacts/handoffs/P03-03/dsh/logs/`、`docs/implementation/P03-03.md`、`docs/implementation/reports/P03-03.md` |
| 上游 Gate / 任务状态 | `artifacts/gates/G00.json`（passed）、`G01.json`（failed）、`G02` 无记录、`P03-01`/`P03-02` 的 zcode precheck（BLOCKED） |
| D11 复现 | `artifacts/handoffs/P02-02/zcode/logs/revision-volatility.log`；DSH 三份 Phase 03 交接的 `revision_label_is_self_perturbing` |
| P03-03 任务书 / 依赖图 / 冻结文档 | `docs/prompts/03-database/P03-03-repositories-and-snapshot.md`、`TASK_GRAPH.md`、`docs/plan/{TASK_MANIFEST.json,PHASE_GATES.md}`、`docs/architecture/{DOMAIN_CATALOG.md,DATA_CONTRACTS.md,IMPLEMENTATION_CONVENTIONS.md}`、`tests/conftest.py` |
| 架构问题登记 | `docs/architecture/issues/README.md`（`ARCH-0004`、`ARCH-0005` 与本报告相关） |
