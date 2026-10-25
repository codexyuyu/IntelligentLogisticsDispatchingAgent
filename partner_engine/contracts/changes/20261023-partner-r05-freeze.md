# 20261023-partner-r05-freeze · R05 冷链公共契约冻结

- 状态：**integrated**（契约源与生成物已由乙方串行集成；域实现与独立校验未实现、未验收）
- 提出者：DSH（原提案 `20261022-dsh-r05.md`）；集成者：PARTNER（乙方）
- 契约版本：**0.1.0 → 0.2.0**（加法变更，无删除、无字段语义改写）
- 基线提交：`7434337`（`origin/main`，建立 R30-E 合并工程共同基线）
- 集成分支：`partner/r05-contracts-20261023`

本文件是 R05 的**契约冻结记录**。它固定 DTO 名称、字段必填/可空语义、区间与容量口径、
领域映射调用签名、结果格式与兼容迁移；**不**表示 CP-SAT 已接入、**不**表示独立校验规则
已实现或已通过任何业务正反例。

## 1. 问题与可复现输入

`data/scenarios/prep_import_report.json` 记录了当前契约无法承载的字段，按类型归并：

| 丢失项（原报告原文摘要） | 涉及规模 |
| --- | --- |
| `contract has no time-varying storage occupancy` | T1×1、A8×2、B20×4 个 StorageLocation 容量 |
| `N simultaneous resource requirements reduced to 1 (contract Operation occupies one resource)` | B20 每条 unload/load 3 项、sort 2 项需求 |
| `setup_class=40 / -200 dropped (no sequence setup)` | B20 全部 100 条工序 |
| `res_B20_H1D/H2D: dock setup_duration_s=30 not expressible` | 2 个月台 |
| `max_exposure_s=120 dropped (no exposure field)` | T1、A8、B20 全部订单 |
| `20 ExternalArrival arrival_s folded into on_hand_units` | B20 |
| `soft_due_at_s`、`fixed_cost_cents`、`rate_cents_per_km` | 全部场景（**本轮不冻结**，见 §7） |

这些字段此前被丢弃，因此“用现有快照跑 R05”在数据层就不成立。本冻结让快照能**无损承载**
这些输入，并且让缺失数据显式表现为未校验，而不是默认通过。

## 2. 冻结的内容（契约 0.2.0）

### 2.1 新增模块 `backend/app/contracts/coldchain.py`（SHARED）

| DTO | 关键字段 | 语义要点 |
| --- | --- | --- |
| `CapacityAmount` | `unit` ∈ `weight_g`/`volume_cm3`/`quantity_units`、`amount` | 一个量只属于一个维度，禁止件/托盘/体积混算 |
| `WarehouseZone` | `zone_id`、`temperature_zone`、`setpoint_decic`、`capacities` | 温区**只**在 zone 上声明，位置不重复声明温度 |
| `StorageLocation` | `location_id`、`zone_id`、`capacities`、`available_windows` | 容量维度非空且互异；`available_windows` 为空 = 未声明日历限制，不是“全天可用”的断言 |
| `StorageOccupancy` | `occupancy_id`、`batch_id`、`location_id`、`capacity_use`、`origin`、`inbound_operation_id`、`outbound_operation_id`、`declared_start_s` | 只声明“谁占了哪、占用多少、由哪两道工序夹住”，计划区间由求解结果解析 |
| `ScheduledOccupancy` | 同上 + `start_s`/`end_s` | 结果侧解析后的 `[start_s, end_s)` |
| `ResourceRequirement` | `requirement_id`、`requirement_kind`、`eligible_resource_ids`、`quantity_units`、`selection` | `fixed` 必须恰好 1 个资源；`choose_one` 可给多个候选 |
| `ResourceAssignment` | `requirement_id`、`resource_id`、`quantity_units` | 结果侧的实际分配，逐需求一条 |
| `ChangeoverRule` / `SetupPolicy` | `from_class`/`to_class`/`duration_s`；`rendering`、`rules`、`default_duration_s` | `default_duration_s=None` 表示**未知**，未知换批不得按 0 处理 |
| `PrecoolRequirement` | `precool_operation_id`、`loading_operation_ids`、`min_duration_s`、`target_temperature_zone`、`eligible_resource_ids` | 预冷是真实工序 + 资源资格 + 与装载的先后关系 |
| `ExposureLimit` / `ExposureSegment` | `max_exposure_s`、`scopes`；`scope`、`[start_s,end_s)`、`source_kind` | 分段观测，跨段按**并集**累计，重叠不重复计时 |
| `BatchCompatibility` / `CompatibilityPolicy` | `min/max_temperature_decic`、`compatibility_class`；`incompatible_class_pairs` | 禁混批对为对称关系，`forbidden(a,b)` 与 `forbidden(b,a)` 等价 |
| `ColdChainSnapshot` | `rule_version`、`horizon_s` + 上述集合 | 挂在 `PlanningSnapshot.coldchain` 上，`None` = 本场景不做 R05 声明 |
| `ScheduledChangeover` | `from_class`/`to_class`/`duration_s`/`after_operation_id`/`before_operation_id`/`setup_operation_id` | 显式换批模式下的证据，记录相邻两道工序 |
| `ColdChainPlan` | `occupancies`、`exposure_segments`、`changeovers` | 挂在 `WarehouseScheduleResult.coldchain` 上，`None` = 本次求解不做 R05 声明 |

### 2.2 区间与容量口径（唯一解释）

- 时间一律为场景整数秒，相对 `PlanningSnapshot.origin_at`。
- 存储占用区间为**半开** `[start_s, end_s)`：同一秒先释放后占用。
  `contracts/examples/r05_coldchain_plan.json` 里 `occ_init1` 结束于 `1200`、
  `occ_in2` 始于 `1200`，即两批在同一时刻不被判为重叠。
- 峰值容量按**每个占用区段的端点逐段核查**，不是对时间积分求平均，也不是只看总量。
- 初始库存从 `0` 起算；期末仍在库的占位覆盖到 `ColdChainSnapshot.horizon_s`。
- 容量比对只在同一 `unit` 内进行；某维度未声明即该维度不参与比较（并由校验方记为未校验）。

### 2.3 对既有共享模型的加法

| 文件 | 变化 |
| --- | --- |
| `common.py` | `CONTRACT_VERSION` → `0.2.0`；新增 `RuleEvidence`（规则版本 + 半开区间 + 观测值/上限 + 单位）；`Violation.evidence` 可空字段；`ValidationReport.not_checked_rule_ids`；`passed` 携带未校验规则、`failed` 无违规均直接报错 |
| `entities.py` | `Order.max_exposure_s`；`Operation.requirements` / `primary_requirement_id` / `setup_class`；`ScheduledOperation.resource_assignments` / `scheduled_kind` / `setup_for_operation_id`；`WarehouseResource.setup_policy_id` / `initial_setup_class`；`PlanningSnapshot.coldchain` |
| `planning.py` | `WarehouseScheduleResult.coldchain`；新增 `ColdChainValidationRequest`（请求 + 完整候选结果 + `rule_version` + `Source`，并派生 `horizon_s()`） |
| `ports/coldchain.py`（新） | `OccupancyTimelineBuilder`、`ColdChainValidator`、`JointValidationDomainFunction` 三个端口签名 |
| `scripts/export_contracts.py` | 导出模块清单加入 `coldchain` |

## 3. 领域映射调用签名（冻结）

```python
class OccupancyTimelineBuilder(Protocol):
    def build(self, request: WarehouseScheduleRequest,
              result: WarehouseScheduleResult) -> tuple[ScheduledOccupancy, ...]: ...

class ColdChainValidator(Protocol):
    validator_version: str
    def validate(self, request: ColdChainValidationRequest) -> ValidationReport: ...

class JointValidationDomainFunction(Protocol):
    def __call__(self, payload: Mapping[str, Any]) -> Mapping[str, Any]: ...
```

- 适配器（乙方，`backend/app/adapters/warehouse/`）负责契约模型 ↔ 纯字典的映射。
- 领域层（甲方，`domain/coldchain_capacity.py`、`domain/joint_validation.py`）**只依赖标准库**，
  不得 import Pydantic/求解器；`check_project.py` 会拦住越界导入。
- `JointValidationDomainFunction` 的 `payload` 键冻结为：`snapshot`、`operations`、`handoffs`、
  `coldchain`、`rule_version`、`source`、`horizon_s`；返回键冻结为 `status`、
  `checked_rule_ids`、`violations`（每条含 `rule_id`/`object_ids`/`message`/可选 `evidence`）、
  `not_checked_rule_ids`。适配器不得增删规则。

## 4. 调用方与受影响文件

- 求解器 `backend/app/adapters/warehouse/cp_sat_scheduler.py`（乙方）：**本轮未改**。R05 约束接入是下一轮任务。
- 校验器 `backend/app/adapters/warehouse/validator.py`（乙方）：**本轮未改**，暂未填 `coldchain`/`not_checked_rule_ids`。
- 甲方待实现：`domain/coldchain_capacity.py`、`domain/joint_validation.py`、`tests/coldchain/`。
- 前端：只消费 OpenAPI。`generated.ts` 与 `contractVersion.ts` 由脚本重生成，**未手改**；本轮无页面改动。
- 场景导入 `scripts/import_preparation_bundle.py`（甲方）：尚未回填新字段，见 §6。

## 5. 兼容性与迁移

- 全部为**加法**：新字段均有默认值（集合默认 `()`、引用默认 `None`），旧快照 JSON、旧
  `WarehouseScheduleResult`、旧 `ValidationReport` 仍可反序列化并通过校验。
- 语义收紧两处，属**行为变化**，需在消费方确认：
  1. `ValidationReport(status='passed', not_checked_rule_ids=(...))` 现在被拒绝——有未校验规则就不是通过。
  2. `ValidationReport(status='failed', violations=())` 现在被拒绝——失败必须给出违规项。
  当前仓库内没有触发这两种写作的位置（`pytest` 277 passed 可证），但这是**协议收紧**，不是纯兼容。
- 旧数据缺字段时：`PlanningSnapshot.coldchain is None` → R05 规则必须报 `not_checked`，
  **禁止**用空数组或 0 时长伪装成“已支持”。
- `contracts/VERSION`、`schemas.json`、`openapi.json`、`generated.ts`、`contractVersion.ts`
  全部由脚本生成，禁止手改；两端漂移检查见 §8。

## 6. 甲方需要配合的回填（未完成）

1. `scripts/import_preparation_bundle.py`：把 `StorageLocation.capacity_*`、`WarehouseTask.requirements`、
   `setup_class`、`Dock.setup_duration_s`/`initial_setup_class`、Cargo `max_exposure_s`、
   `InitialStock`/`ExternalArrival` 映射进 `PlanningSnapshot.coldchain`，并**逐条消掉**
   `prep_import_report.json` 里对应的 losses。
2. 域规则实现与手算正反例：`20261022-dsh-r05.md` 的 10 行表格（峰值库容、同时释放、初始库存、
   多资源、换批、初始换批、预冷、累计暴露、暴露重叠、温区相容）转为 `backend/tests/coldchain/`。
3. 缺失数据口径：`PlanningSnapshot.coldchain is None`、`exposure_limits` 为空、
   `compatibility_class` 为空时，必须落到 `not_checked_rule_ids`，不得 passed。

## 7. 明确不在本次冻结范围

- CP-SAT 时变容量/多资源/换批/预冷/暴露约束的**建模与接入**（下一轮，乙方）。
- `soft_due_at_s`（软截止）、`fixed_cost_cents`、`rate_cents_per_km`（车辆成本）：属 R01/R09 口径，
  本轮未纳入，`prep_import_report.json` 中仍记为丢失。
- 运输段暴露（`scope='transport'`）的数据来源：路由结果目前不产出 exposure 段，
  joint validation 需从 `VehicleRoute` 自行推导；本冻结只固定 `ExposureScope` 枚举与并集语义。
- 版本化确认/哈希/替换语义（`20261022-dsh-confirmation.md`）：独立议题，未在本轮冻结。

## 8. 集成记录与验证

验证环境：Windows，Python 3.12.10（本工程 `.venv`）、Node 24.19.0 / npm 11.17.0，
`PYTHONUTF8=1`（本机默认 GBK，否则 `tests/test_r30b_reschedule.py` 等旧测试的
`read_text()` 会因编码报错，属环境问题，未改测试）。

| 命令 | 结果 |
| --- | --- |
| `.\.venv\Scripts\python.exe scripts/export_contracts.py` | `Exported contracts`（exit 0） |
| `.\.venv\Scripts\python.exe scripts/export_contracts.py --check` | `Contracts match source`（exit 0） |
| `npm run contracts:generate` | `Generated frontend contract types and version` |
| `npm run contracts:check` | `Frontend contract types match OpenAPI` |
| `npm run typecheck` | exit 0 |
| `npm test` | 10 组前端专项全 PASS（R15/R16/R23/R25/R26/R27/R28/R29/R30-A/R30-C） |
| `npm run build` | `✓ built in 2.17s`（exit 0） |
| `.\.venv\Scripts\python.exe -m pytest -q`（backend） | **277 passed**（基线 229 + 新增 48） |
| `.\.venv\Scripts\python.exe scripts/build_file_map.py` | `File map: 499 source files` |

冻结文件哈希（SHA256，随本提案提交）：

| 文件 | 字节 | SHA256 |
| --- | --- | --- |
| `contracts/VERSION` | 7 | `c58a749f70f5e1ba5394ebcdbfcfa02fa938c4a173d8e41e6c476a7c8b2acddd` |
| `contracts/schemas.json` | 687832 | `bf96416d4c3014763de92885ae7a649bc299ad48136419a8424a5fc3677905f6` |
| `contracts/openapi.json` | 118921 | `307a3fa664b5f41f850c6e5bb8518a23bff913afff9d931d95cf4f45292ebab8` |
| `frontend/src/client/generated.ts` | 65719 | `3fae5a99b6f379d8b06f6e364b6a5d1c9cc1eb7e41b2f018c78f880c01687c9f` |
| `frontend/src/client/contractVersion.ts` | 107 | `303e51ffa0448b729be9297a526ca5785641c5e296bba61c872c552aa192b764` |

契约层正反例（`backend/tests/test_r05_coldchain_contracts.py`，48 条）：发布样例可解析、
容量维度不可混、初始库存不得有入库工序、`fixed` 需求必须唯一资源、需求缺 `primary_requirement_id`
被拒、换批缺规则不得为 0、setup 工序必须指向被准备的工序、曝光区间必须正向、
禁混批对对称、`passed` 不得携带未校验规则、违规证据区间/单位成对。

## 9. 交付与恢复条件

- 乙方交付：契约源 + 版本 + 生成物 + 映射签名 + 样例 + 契约层正反例（本提案与同批提交）。
- 甲方复验后再实现域层；**在域层实现并跑出手算正反例之前，R05 不得称为已支持**。
- CP-SAT 接入、真实求解回归、`prep_import_report.json` 清零仍由乙方后续完成。
