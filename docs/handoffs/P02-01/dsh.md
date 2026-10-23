# P02-01 · DSH → ZCode 交接说明

| 项 | 值 |
| --- | --- |
| Task ID | `P02-01`（owner A，阶段 Gate `G02`） |
| 交付方 | DSH-A（本任务唯一主写者，本会话） |
| 交接对象 | ZCode N04 独立预验收（按 `docs/workflow/02-ZCODE-PRECHECK.md`；不签 G02） |
| 本角色状态 | **`READY_FOR_ZCODE`** |
| 阶段 Gate | `G02`：**未签收**（本任务不写任何 Gate 记录） |
| 前置 `G01` | 官方 `artifacts/gates/G01.json` sha256 `b7ac0c60de7438dc0cd88cc7f277b6ac2e93b8216ee05efdfb3124089c98dee8`，`status=passed`；我独立复算 40/40 输入新鲜、7/7 命令日志 hash 匹配、依赖 G00 新鲜（`tmp/P02-01/precondition/verify-g01.py`，exit 0） |
| 证据入口 | `artifacts/handoffs/P02-01/dsh/evidence.json`、`artifacts/handoffs/P02-01/dsh/logs/p02-01-2026-10-04/` |
| 任务文档 / 报告 | `docs/implementation/P02-01.md`、`docs/implementation/reports/P02-01.md` |

## 1. 候选与依赖绑定

- 候选（本轮实测）：`code_revision = content-sha256:dadad19614a86a39ddf880c8ae8011e5fff889d1f02d12b7a0cfa28aaaad3cf8`，`dirty_tree_hash = content-sha256:2b8deb75aa6b28d7529b6f00e0fc958d9556792574a6b8de7018ac4aac20d297`，**82** 个白名单文件。用 `scripts/gates.py` 的 `GateRunner.relevant_manifest_rows()` 复算（`tmp/P02-01/recon/gather-facts.py`）。
- 与阶段 1 候选的关系：P02-01 新增 5 个白名单文件（`errors.py`、`primitives.py`、`states.py`、两份测试），候选**必然**从 G01 的 `23930f7a…` 变为 `dadad196…`。G01 记录本身仍是其阶段候选上的有效签收，未被本任务修改。
- 白名单外唯一改动：`packages/domain/src/logistics_domain/__init__.py`（原因见 §4）。

## 2. 交付物与接口

```text
TimeWindow(earliest_s: int, latest_s: int)                       # 服务开始窗，闭区间
transition(state: EntityState, event: Transition) -> EntityState # 按 DOMAIN_CATALOG 生命周期判定
```

- `states.py`：17 个枚举（`JobKind`/`JobStatus`/`JobOptimizationMode`/`ActorRole`/`ResourceKind`/`GenerationPolicy`/`CargoCondition`/`ReturnPolicy`/`WeatherProfile`/`EntityKind`(45)/`ExpectationMeasure`/`AttemptOutcome`/`TerminalJobStatus`/`ImportStatus`/`RuntimeMode`/`ReadyStatus`/`DependencyStatus`）+ `ErrorCode`(18) + `EntityState`(66) + `Transition` + `LIFECYCLE_TRANSITIONS` + `allowed_next_states` + `transition`。
- `primitives.py`：标量规则（int/UUID/UTC 秒/`Sha256`/`SafeText`/`SafeArtifactPath`）与 `TimeWindow`、`Load`、`Money`、`CalendarInterval`、`ResourceCalendar`、`Rational`、`EntityRef`、`ArtifactRef`（全部 frozen/slots）。
- `errors.py`：`DomainError`/`InvalidInputError`/`InvalidTransitionError`/`UnknownEnumValueError`/`parse_enum`。

## 3. 本轮实跑（真实退出码与计数，取自原始日志）

| 命令 | 退出码 | 实测结果 | 原始日志 |
| --- | --- | --- | --- |
| `uv run pytest tests/unit/test_p02_01_primitives_and_states.py tests/integration/test_p02_01_primitives_and_states.py -q` | 0 | **46 passed / 0 failed / 0 skipped**（unit 37 + integration 9） | `logs/p02-01-2026-10-04/required-cmd1-pytest.log` |
| `uv run python scripts/check_architecture.py` | 0 | `scanned 10 module(s) across 7 layer(s); violations=0` | `…/required-cmd2-check-architecture.log` |
| `uv run pytest tests/unit tests/integration -q`（补充） | 0 | **272 passed / 0 failed**（P01 的 226 + P02-01 的 46） | `…/full-regression.log` |

两份测试文件也可单独收集通过（integration 单文件 9 passed）；修复包 marker 之前 integration 单文件收集会直接 error。

## 4. 需要独立复核的边界

1. **6 个冻结 Test Case 都是真断言**：相邻 `[0,10)`/`[10,20)` 不冲突；`delivered -> draft` 抛 `InvalidTransitionError` 且 `code=invalid_transition`；`JobKind.SIMULATION`/`JobOptimizationMode.TRANSPORT` 经 `json.dumps` 得固定小写值；`JobKind("routing")` 与 `parse_enum(JobKind,"routing")` 均拒绝；`CalendarInterval(10,10)` 拒绝；日历缺 `epoch_utc` 拒绝（缺参 `TypeError`、naive 值 `InvalidInputError`）。
2. **枚举唯一性与取值**：逐成员对照 `contracts/changes/N01-R01-contract-decisions.json` 与 `TYPE_DEFINITION_OWNERSHIP.md`，确认没有第二套定义、没有多余序列化值；`UNSUPPORTED` 不在 `ErrorCode`。
3. **生命周期图与目录一致**：`LIFECYCLE_TRANSITIONS` 的边逐条对照 `DOMAIN_CATALOG.md` 的状态列（尤其 cargo `delivered→returned`、schedule `active↔suspended`、route「可 superseded」的分支语义），并确认 `delivered -> draft` 的拒绝不是因为"终态一律拒绝"的巧合。
4. **包 marker 改动**：`from logistics_domain import states` 修复前抛 `NotImplementedError`（复现命令见报告）；修复后其余未交付名（`entities`/`ids`/`units`/`ports`）仍必须抛 `NotImplementedError`，`__getattr__` 语义未被削弱。
5. **域名层纯净**：三个新模块只依赖标准库与兄弟模块；集成测试在隔离解释器（`-I`，cwd 为临时目录）中确认没有第三方模块被拉入。
6. **候选自扰动**：写 `tmp/`、`artifacts/`、`docs/implementation/`、`docs/handoffs/` 后 `code_revision` 必须不变；改任一白名单文件必须改变它。

## 5. 未执行/未覆盖

- `G02` 签收所需的其余任务（P02-02/03/04）与 JSON Schema/OpenAPI/TS 导出。
- 数据库、OR-Tools、SimPy、模型、浏览器验收（不属本任务）。
- `docs/architecture/issues/README.md` 的登记（不在本任务白名单）：三条缺口文本见证据文件的 `issues_to_register`，请治理会话登记。

## 6. 停止条件

本交接与 `evidence.json` 写出后，本轮**停止修改该候选**，交 ZCode N04 独立预验收；不签任何 Gate，不启动 P02-02。

---

> **当前候选已变更（`P02-01-F01`，2026-10-05）。** 本文件保留交付轮原文；当前候选的交接是
> [`dsh-f01.md`](dsh-f01.md)，本文件不再代表最新前置。缺陷 `ZC-P02-01-F01`（Reservation 生命周期）已修，
> 新候选 `content-sha256:477a883d2a29deb5cb60f8269c8712693d9e7aedeb3a620ba4953a630289158c`；G01 与该文件上的旧绑定因本轮合法返工而过期，待调度交独立证据恢复。
