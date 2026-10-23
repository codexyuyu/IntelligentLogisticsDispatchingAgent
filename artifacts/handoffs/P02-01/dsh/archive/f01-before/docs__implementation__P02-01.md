# P02-01 · 领域 ID、单位与唯一状态枚举

任务：`P02-01`（owner A，阶段 Gate `G02`）。契约：业务 2.0.0 / 计划 1.0.3 / Gate 证据 schema 1.0.0。

本文件说明已交付的能力、单位与失败语义。字段与成员的**唯一来源**是
`contracts/changes/N01-R01-contract-decisions.json`（P02-01 名下 `states.py` / `primitives.py` 条目）、
`docs/architecture/DATA_CONTRACTS.md` §公共类型与状态 与 `docs/architecture/DOMAIN_CATALOG.md`
的「状态与生命周期」列；本文件不新增第二套定义。

## 1. 承载文件

| 文件 | 内容 |
| --- | --- |
| `packages/domain/src/logistics_domain/states.py` | 17 个状态/枚举 + `ErrorCode` + `EntityState`/`Transition` + 生命周期图 |
| `packages/domain/src/logistics_domain/primitives.py` | 标量规则、`TimeWindow`、`Load`、`Money`、`CalendarInterval`、`ResourceCalendar`、`Rational`、`EntityRef`、`ArtifactRef` |
| `packages/domain/src/logistics_domain/errors.py` | 领域异常层级（`DomainError`/`InvalidInputError`/`InvalidTransitionError`/`UnknownEnumValueError`）与 `parse_enum` |
| `packages/domain/src/logistics_domain/__init__.py` | **白名单外的唯一改动**（见 §6） |

`states.py` 是叶子模块（不导入任何兄弟模块）；`primitives.py` 依赖 `states.py`；`errors.py` 只依赖 `states.py`。

## 2. 单位与标量规则

`DATA_CONTRACTS.md` 第 118 行冻结的标量规则全部实现：

- 整数拒绝 `bool`/`float`，并限制在 int64 内；`PositiveInt >= 1`、`NonNegativeInt >= 0`；
- `UUID` 为小写规范文本或 `UUID` 实例；`UTC` 为**秒精度、带 UTC 时区**的 `datetime`（naive 或非 UTC 偏移一律拒绝）；
- `Sha256` 为 64 位小写十六进制；`SafeText` 为 1..256 字符；
- 重量 g、容积 cm³、距离 m、金额**分**、温度 decic、求解相对秒；资源占用 `[start_s, end_s)`，服务开始窗 `[earliest_s, latest_s]` 闭区间；horizon 上限 604800 s。

`Money(cents: int)` 是金额载体（单位=分），**不**限制符号，因为同一值对象也要表达费用差额；需要非负的调用方在自己的边界断言。

`SafeArtifactPath` 在冻结输入中没有给出形状定义（只在 `ArtifactRef` 中被引用）。本任务实现最小安全读法：相对 POSIX 路径、正斜杠、无盘符/UNC、无空段/`.`/`..`，并在 §6 登记该缺口。

## 3. 状态枚举（唯一来源）

`states.py` 定义并唯一导出：`JobKind`(5)、`JobStatus`(5)、`JobOptimizationMode`(3)、`ActorRole`(2)、
`ResourceKind`(5)、`GenerationPolicy`(12)、`CargoCondition`(4)、`ReturnPolicy`(2)、`WeatherProfile`(4)、
`EntityKind`(45)、`ExpectationMeasure`(5)、`AttemptOutcome`(4)、`TerminalJobStatus`(3)、`ImportStatus`(3)、
`RuntimeMode`(3)、`ReadyStatus`(2)、`DependencyStatus`(2)、`ErrorCode`(18)，全部为 `StrEnum`，
序列化值就是契约中的小写固定值（Test Case 3）。

`ErrorCode` 逐项对应 `DATA_CONTRACTS.md` 第 13 行错误表，加上第 156 行明确纳入唯一映射的
`RESULT_NOT_READY`、`UNVERIFIED_SOLVER_RESULT`；`HTTP_STATUS_BY_ERROR_CODE` 保存冻结的 code→HTTP 映射。
`UNSUPPORTED` **不是** `ErrorCode`（第 156 行），`MANUAL_REQUIRED`/`NO_FEASIBLE_CANDIDATE` 是业务结果原因，均排除。

`EntityState` 是 `DOMAIN_CATALOG.md` 全部生命周期状态词的并集（66 个成员），`LIFECYCLE_TRANSITIONS`
按 owner 逐行转写目录的状态列（32 实体 + §必需辅助实体），`↔` 展开为两条有向边。

## 4. 接口与失败语义

```text
TimeWindow(earliest_s: int, latest_s: int)
transition(state: EntityState, event: Transition) -> EntityState
```

- `transition` 按 `LIFECYCLE_TRANSITIONS` 的并集判定：`delivered -> draft` 抛 `InvalidTransitionError`
  （`code = invalid_transition`，携带 `state` / `to_state` / `allowed`）。`delivered` 在目录中唯一的后继是
  cargo 的 `returned`，所以该拒绝不是"因为终态所以什么都拒绝"的巧合。
- 需要按实体精确判定时使用 `LIFECYCLE_TRANSITIONS[owner]` 或 `allowed_next_states(state)`。
- `ResourceCalendar` 的 `epoch_utc` 是**必填**字段：缺参构造直接 `TypeError`，naive/非 UTC/微秒非零抛 `InvalidInputError`。
- 日历区间必须 `0 <= start_s < end_s <= 604800`、`available_units >= 0`、按 `start_s` 严格升序且不重叠；
  **相邻不算冲突**（`[0,10)` 与 `[10,20)`）。未被任何区间覆盖的时刻表示 0 可用，日历从不隐式补容量；空日历合法且表示 0。
- 领域失败只用 `errors.py` 的领域类型；不含任何框架/ORM/Pydantic 依赖。

## 5. 不可变性与确定性

`TimeWindow`、`Load`、`Money`、`CalendarInterval`、`ResourceCalendar`、`Rational`、`EntityRef`、`ArtifactRef`
均为 `@dataclass(frozen=True, slots=True)`：可哈希、可作 dict 键、赋值抛 `FrozenInstanceError`。
`Rational` 在构造时约到最简，`scale(duration_s)` 用 `ceil` 并在 int64 溢出时拒绝，保证下游整数求解可复算。

## 6. 白名单外的改动与登记缺口（需治理决定）

1. **`packages/domain/src/logistics_domain/__init__.py`（唯一白名单外改动）**。原任务 §Files 允许
   「包marker只有确需导出本任务类型时可修改，须先在完成报告列出精确路径」。改动原因：`_PENDING_APIS`
   仍把 `states` 列为未交付，导致 `from logistics_domain import states` 抛 `NotImplementedError`
   （`from logistics_domain.states import ...` 与 `import logistics_domain.states` 均正常）。修复是
   从 `_PENDING_APIS` 移除已交付的 `states`，并在包内显式 `from . import errors, primitives, states`；
   `entities` / `ids` / `units` / `ports` 仍按原样抛 `NotImplementedError`。
2. **`ConstraintCode` / `ViolationCode` 没有冻结成员表**。`TYPE_DEFINITION_OWNERSHIP.md` 把二者归 P02-01，
   但没有任何冻结输入列出成员：契约只说 `ConstraintParameters` 按 `ConstraintCode` 判别，覆盖注册表由
   P10-01（`constraint_id`/`version`）承担。本任务只交付**类型名**（`NewType(..., str)`），不臆造成员值。
3. **`SafeArtifactPath` 无形状定义**，只在 `ArtifactRef` 中被引用；本任务按 §2 的最小安全读法实现。
4. 上述 2、3 应登记到 `docs/architecture/issues/README.md`；该文件**不在本任务白名单**，DSH 未写入，
   逐字文本见 `artifacts/handoffs/P02-01/dsh/evidence.json` 的 `issues_to_register`。

## 7. 关联测试

- `tests/unit/test_p02_01_primitives_and_states.py`：37 例，覆盖全部 6 个 Test Case、17 个枚举成员/值、
  `ErrorCode` 表、生命周期边、标量与值对象正反例。
- `tests/integration/test_p02_01_primitives_and_states.py`：9 例，在真实边界上核对冻结决定表、
  归属表、DOMAIN_CATALOG 生命周期列、域名层无框架导入、以及在隔离解释器（cwd 之外）的导入行为。

## 8. 实际限制

- 本任务不实现实体、不导出 JSON Schema/OpenAPI/TS（P02-04/P02-05 负责），因此 `G02` 的
  「32 实体可表达、Schema 确定导出」尚不成立。
- 设计谓词仍非正式 domain/handler/worker；本任务只交付 P02-01 名下的类型。
- 无数据库、求解器、仿真、模型或浏览器验收。
