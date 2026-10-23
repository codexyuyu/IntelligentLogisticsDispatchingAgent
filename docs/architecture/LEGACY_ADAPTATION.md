# v0.1 → v1 迁移与旧契约转换

本文件是旧基线（`demo/`，契约版本 **0.1.0**）到新根级工程（契约版本 **1.0.0**）的**转换唯一权威**：命名、单位、枚举、路径与所有权映射都写在这里，实现与测试必须引用本表，不得另行发明转换规则。

词汇来源（本文件不发明任何 v0.1 取值）：`demo/backend/app/domain/states.py`、`demo/backend/app/contracts/*.py`、`demo/contracts/VERSION`、`demo/OWNERSHIP.json`。v1 目标词汇来源：`docs/architecture/DATA_CONTRACTS.md`、`docs/architecture/DOMAIN_CATALOG.md`、`PROJECT_MASTER_PLAN.md`。

基线清单见 `docs/architecture/BASELINE_INVENTORY.json`（173 条，含逐文件 sha256）；旧到新的逐路径映射见 `docs/architecture/MIGRATION_MAP.md`。

## 1. 所有权映射（v0.1 → v1）

旧 `demo/OWNERSHIP.json` 的相对路径只对旧基线有效，不能直接套用到新根级工程。对应关系：

| v0.1 路径（长前缀胜出） | owner | v1 归属（`OWNERSHIP.json` 前缀） | 说明 |
| --- | --- | --- | --- |
| `backend/app/adapters/routing/` | B | `packages/optimization/` | v1 不再单独设 routing 目录，运输求解器与矩阵同属 optimization |
| `backend/app/adapters/matrix/` | B | `packages/optimization/` | 矩阵提供器归 optimization（运输域） |
| `backend/app/adapters/simulation/` | B | `packages/simulation/` | 直接对应 |
| `backend/app/domain/transport_rules.py` | B | `packages/domain/` | 纯领域规则归 A 维护的 domain 包；运输语义的实现任务仍是 B（见第 4 节任务映射） |
| `backend/tests/transport/` | B | `tests/solver/`、`tests/**/transport/` | v1 求解器测试归 B |
| `backend/tests/simulation/` | B | `tests/simulation/` | 直接对应 |
| `data/transport/` | B | `data/transport/` | 路径未变（v1 根级） |
| `data/simulation/` | B | `data/simulation/` | 路径未变（v1 根级） |
| `benchmarks/transport/` | B | `benchmarks/transport/` | 路径未变（v1 根级） |
| `benchmarks/simulation/` | B | `benchmarks/simulation/` | 路径未变（v1 根级） |
| `backend/app/contracts/`、`backend/app/ports/`、`backend/app/domain/states.py` | A | `packages/contracts/`、`packages/domain/` | 共享契约与领域状态由 A 唯一维护 |
| `backend/app/common/`、`backend/app/main.py`、`backend/app/api/dependencies.py` | A | `apps/backend/` | 边界、错误与组合根 |
| `frontend/`、`frontend/src/client/generated.ts` | A | `apps/frontend/` | 生成客户端只能由生成器重写 |
| `contracts/` | A | `contracts/` | 旧 `openapi.json`/`schemas.json` 不作为 v1 主文档（见 MIGRATION_MAP） |
| `scripts/*`、`.github/`、`docs/*` | A | `scripts/`、`.github/`、`docs/` | 工程与文档资产 |
| `reference_demos/` | A | — 不迁移 | 教学参考，永久禁止从正式包导入 |

判定算法与拒绝语义由 `scripts/check_ownership.py` 的 `resolve_owner` 实现：最长**段感知**前缀胜出（`packages/simulation` 匹配 `packages/simulation/src/x.py`，不匹配 `packages/simulation_extra/x.py`）；未列出路径落到 `default_owner`（A）；绝对路径、盘符路径或越出仓库根的路径一律**拒绝**。

## 2. 命名转换

| 维度 | v0.1 | v1 | 规则 |
| --- | --- | --- | --- |
| 包/模块命名空间 | `app.*`（`app.contracts`、`app.ports`、`app.domain`、`app.adapters`） | `logistics_domain`、`logistics_contracts`、`logistics_optimization`、`logistics_simulation`、`logistics_agents`、`logistics_evaluation`、`logistics_backend` | 一个旧模块只能映射到一个新包；禁止从正式包导入 `app.*`/`demo/` |
| 分发名 | 无（仅为目录） | `logistics-<name>`（连字符），导入名 `logistics_<name>`（下划线） | 由 hatchling `targets.wheel.packages` 显式声明 |
| 类型命名 | 与目录同名（`backend/app/contracts/entities.py` 等） | 契约类型置于 `logistics_contracts`，纯领域类型置于 `logistics_domain` | 不得复制一份仅改名的 DTO 到 domain |
| 枚举成员字面量 | `snake_case`（`infeasible_proven`、`no_solution_within_budget`） | `SCREAMING_SNAKE_CASE`（`SolveStatus`）或 `kebab-case`（`JobStatus`、事件 kind） | 表格中出现字面量时统一使用**新值**；转换必须显式（见第 3 节） |
| 文件命名 | `backend/app/...` 扁平 | `packages/<name>/src/logistics_<name>/...`（src-layout） | 见 `docs/architecture/IMPLEMENTATION_CONVENTIONS.md` |
| 契约版本字段 | `contracts/VERSION` 固定文本 `0.1.0` | `schema_version` 字段 = `1.0.0` | 旧版本文件保持只读，不覆盖 |

## 3. 单位转换

| 维度 | v0.1 | v1 | 转换规则 |
| --- | --- | --- | --- |
| 时间粒度 | 分钟为主（教学探针、部分 fixture 以分钟表述） | **整数秒** | 显式换算：`1 分钟 = 60 秒`；不得隐式取整，不得接受小数秒 |
| 时长字段 | 旧分钟输入 `2` | `120` 秒 | 由 `convert_legacy_minutes(2)` 产出，返回值内嵌 `legacy_version = 0.1.0`，可审计 |
| 距离 | 米 | 米（整数） | 不变 |
| 重量 / 体积 | 克 / cm³ | 克 / cm³（整数） | 不变 |
| 成本 | 分（cent） | 分（int，`*_cents` 字段） | 不变；字段名统一带 `_cents` 后缀 |
| 温度 | `4.0` 摄氏度浮点 | `decic` 整数（`40` = 4.0 °C） | `decic = round(celsius * 10)`；阈值比较在 decic 上做 |
| 时间基准 | 本地/无明确基准 | UTC epoch 整数秒 | v1 一律 UTC epoch |
| 区间语义 | 未统一 | 服务开始窗**闭区间**；资源占用 `[start, end)` | v1 统一；v0.1 无对应声明，不做历史推断 |

负值与溢出：v1 的整数字段在 domain 层做非负与 int64 上界检查；旧值不得因为"看起来合理"而被接受。

## 4. 枚举转换表

转换由 `scripts/check_ownership.py::convert_legacy_status` 实现，只接受下表取值；**未映射取值抛 `LegacyConversionError`（明确拒绝，不猜测）**。`v1 目标 = —` 表示该 v0.1 取值在 v1 没有等价状态，按"不迁移"处理并显式登记，而不是改写成一个近似的状态。

### 4.1 `JobStatus`（v0.1：`demo/backend/app/domain/states.py`）

| v0.1 | v1 | 说明 |
| --- | --- | --- |
| `queued` | `JobStatus.queued` | 直接对应 |
| `running` | `JobStatus.running` | 直接对应 |
| `succeeded` | `JobStatus.completed` | v1 用 `completed` 表示"已执行并产出 typed 结果" |
| `failed` | `JobStatus.failed` | v1 仅指 worker 崩溃/代码错误或重试耗尽 |
| `cancelled` | `JobStatus.cancelled` | 直接对应 |

### 4.2 `SolveStatus`（v0.1 有 10 个取值，v1 有 8 个）

| v0.1 | v1 | 说明 |
| --- | --- | --- |
| `optimal` | `SolveStatus.OPTIMAL` | 直接对应 |
| `feasible` | `SolveStatus.FEASIBLE` | 直接对应；**不等于** OPTIMAL |
| `infeasible_proven` | `SolveStatus.INFEASIBLE` | v1 用 `INFEASIBLE` 表示已证明无解 |
| `no_solution_within_budget` | `SolveStatus.TIMEOUT` | 预算耗尽属于 TIMEOUT；无 incumbent 时不得报告可行 |
| `invalid_input` | `SolveStatus.INVALID_INPUT` | 直接对应 |
| `model_invalid` | `SolveStatus.ERROR` | v1 的 `ERROR` 覆盖模型自身错误；原始引擎状态另存 `engine_status` |
| `needs_clarification` | `SolveStatus.INVALID_INPUT` | v1 把"信息不足"归入输入问题，并在 `details` 给出缺字段 |
| `unsupported` | `SolveStatus.INVALID_INPUT` | 未知/不支持能力；HTTP 码的命名分歧见 `ARCH-0003` |
| `stale` | — | v1 的快照/版本过期是**冲突**（409），不是求解状态；转换时刻必须重新取快照 |
| `conflict` | — | 同上；v1 用 `RESOURCE_CONFLICT`/`STALE_SNAPSHOT` 错误码表达 |

### 4.3 `PlanStatus`（v0.1 计划状态 → v1 `ScheduleVersion` 生命周期）

| v0.1 | v1 | 说明 |
| --- | --- | --- |
| `draft` | `validated` 之前的状态（候选阶段） | v1 候选不落为正式版本；写入前必须先通过独立校验 |
| `validated` | `ScheduleVersion.status = validated` | 已通过硬约束校验 |
| `confirmed` | `ScheduleVersion.status = confirmed` | 只能由 `ScheduleService` 在最新快照上原子确认 |
| `executing` | `ScheduleVersion.status = executing` | |
| `completed` | `ScheduleVersion.status = completed` | |
| `rejected` | `ScheduleVersion.status = rejected` | |
| `stale` | `superseded` | v1 用"被新版本取代"表达过期；历史版本不可改写 |
| `superseded` | `superseded` | 直接对应 |

### 4.4 `OperationStatus`（v0.1 仓储作业状态 → v1 `WarehouseTask`）

| v0.1 | v1 | 说明 |
| --- | --- | --- |
| `pending` | `pending` | 直接对应 |
| `running` | `running` | 直接对应 |
| `interrupted` | `interrupted` | v1 显式区分中断与取消，中断后保留剩余工作 |
| `completed` | `completed` | 直接对应 |
| `cancelled` | `cancelled` | 直接对应 |
| `paused` | — | v1 无"暂停"作业状态：不可抢占作业只能中断（`interrupted`）或取消 |

### 4.5 `TemperatureZone`

| v0.1 | v1 | 说明 |
| --- | --- | --- |
| `chilled` | `chilled` | 冷藏 |
| `frozen` | `frozen` | 冷冻 |
| （无） | `ambient` | v1 新增常温；v0.1 数据不会产生该值，迁移时不得凭空补 |

### 4.6 `EventType`（v0.1 有 5 个取值 → v1 十类异常事件）

v1 的事件 `kind` 属于 `EventKind` 判别联合，具体成员由 **P13-01** 冻结（本任务不新造枚举字面量）。下表给出**已决定的类别对应**，其余 v1 类别标注为"v1 新增"：

| v0.1 | v1 类别 | 说明 |
| --- | --- | --- |
| `departure_delayed` | 延误（departure/delay） | 出发延误 |
| `dock_unavailable` | 仓储资源不可用（dock/资源） | 月台不可用归入仓储资源不可用 |
| `cargo_quarantined` | 货物异常（cargo incident） | 检疫/隔离属货物事件 |
| `weather_changed` | 天气变化（weather change） | 触发矩阵换版，不改变已走路段事实 |
| `demand_changed` | 需求增减（demand change） | 增减需求必须重算重量/容积/数量 |
| （无） | 车辆故障（vehicle breakdown） | v1 新增；需救援交接，禁止货物瞬移 |
| （无） | 交通（traffic） | v1 新增 |
| （无） | 订单取消（order cancel） | v1 新增；装车前与在途语义不同 |
| （无） | 设备故障（equipment failure） | v1 新增 |
| （无） | 救援交接（rescue handoff） | v1 新增；需源/目标资源、剩余载荷与暴露上限 |

v1 独有、v0.1 不存在的取值另见 `V1_ONLY_VALUES`（`SolveStatus.UNKNOWN`/`CANCELLED`、`TemperatureZone.ambient`、上表"v1 新增"行）：这些值**不得**从旧数据推断产生。

## 5. 未映射取值的处理

- 任何不在第 4 节表格中的 v0.1 取值：`convert_legacy_status` 抛 `LegacyConversionError`，消息包含 kind、非法取值与已知取值集合，**不返回近似值、不静默丢弃**。
- 任何 v1 新增取值：必须显式登记为"v1 新增"后才允许出现；旧数据永远不会产生它们。
- 转换结果 `LegacyConversion` 始终带 `legacy_version = 0.1.0` 与 `target_version = 1.0.0`，便于在证据中追溯来源版本。

## 6. 复用前置条件与禁止事项

- `reuse` 类旧资产（B 域矩阵/路由/仿真端口、固定矩阵适配器、运输请求样例、导出脚本）只有在**对应任务重新验证**后才可复用；当前无已验证引擎证据（见 `docs/architecture/MIGRATION_MAP.md`）。
- 禁止从正式包导入 `demo/**`、`demos/**` 或 `app.*`（由 `scripts/check_ownership.py` 的 `check_legacy_imports` 与 `scripts/check_architecture.py` 双重检查）。
- 禁止把旧占位适配器（抛 `FeatureNotImplemented` 的 scaffold）装配进 v1 `bootstrap`。
- 旧 `demo/` 是只读基线：迁移不得修改、移动或删除其中任何文件。
