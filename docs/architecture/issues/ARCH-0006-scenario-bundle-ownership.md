> 当前决定：2026-10-03 N01-R01 decided（完整设计待独立复核）；G00阻断尚未经N02解除。下文旧发现/旧N01结论保留为历史，本轮末尾决定优先。

# ARCH-0006 ScenarioBundle归属已裁定，字段未决

当前状态（2026-10-03）：decided；P02-04派发前blocking=yes。下文open描述为原发现历史，末尾N01决定替代旧决定。

- `id`：`ARCH-0006`
- `status`：`open`
- `discovered_by_task`：`P04-01`（`canonical-fixtures`），在按任务书核对 `generate_scenario(spec: ScenarioSpec, seed: int) -> ScenarioBundle` 的签名右侧类型来源时发现：`ScenarioSpec` 有明确归属，**`ScenarioBundle` 在任何冻结制品中都没有被指派给某个任务**。
- `title`：`ScenarioBundle` 出现在多处已冻结的接口签名中，但 `DATA_CONTRACTS.md` 只指派了 `ScenarioSpec` 的形状归属（P02-04），未指派 `ScenarioBundle`。
- `evidence`：
  - 需要它的签名：`docs/architecture/DATA_CONTRACTS.md:94`（`ScenarioEngine.load(ref:ScenarioRef)->ScenarioBundle`）、`docs/prompts/01-foundation/P04-01-canonical-fixtures.md:90`（`generate_scenario(spec: ScenarioSpec, seed: int) -> ScenarioBundle`）、`docs/api/API_CONTRACT.md:47`（`GET /scenarios/{id}` → `ScenarioBundle`）。
  - **明确指派了 `ScenarioSpec`**：`docs/architecture/DATA_CONTRACTS.md:81` —— “`ScenarioSpec`的纯数据形状也在**P02-04**定义，P04负责生成；`ScenarioEngine`的加载实现可在P12-04装配。”
  - **未指派 `ScenarioBundle` 的形状定义任务**：`DATA_CONTRACTS.md` 的具名 Schema 表（第 20–60 行区间）内**没有** `ScenarioBundle` 行；第 94 行的 Protocol 表只给出签名，没有形状归属。`docs/architecture/DOMAIN_CATALOG.md` 中 `Scenario` 相关条目只有 `Simulation`（第 39 行）与 `Experiment`（第 48 行）两个**实体**，均不是 `ScenarioBundle`。
  - 唯一提到它的“模型”清单是 `docs/prompts/07-simulation/P11-01-simulation-contract.md:69`（“Simulation、SimulationSnapshot、**ScenarioSpec**、TwinState、RngState”）——该处列的是 `ScenarioSpec`，**不是** `ScenarioBundle`；`ScenarioBundle` 只出现在同一文件的接口签名 `ScenarioEngine.load(...) -> ScenarioBundle`（第 88 行）。
  - 形状线索只存在于 `docs/architecture/IMPLEMENTATION_CONVENTIONS.md:33` 的**内部接口表**（该表描述的是 `ScenarioSpec / domain.runtime`：`id/version/seed/epoch_utc/horizon_s`、`size:ScenarioSize`、`generation_policy:GenerationPolicy`、`event_specs:tuple[ScenarioEventSpec]`），未覆盖 `ScenarioBundle`。
- `impact`：实现 `P04-01` 时，任务书 `Files` 白名单**不含**任何领域类型模块，但接口签名右侧要求返回 `ScenarioBundle`。若无归属，实现者要么在 `scripts/generate_scenario*.py` 里自带一份 `ScenarioBundle` 定义，要么返回未经定义的 `dict`——两者分别触犯 Architecture Constraint 6（“禁止重复定义 Domain Model”）与 Constraint 1（“跨边界不传未经定义 dict/Any”）。同类风险也存在于后续引用该返回类型的 `P04-02`（`ScenarioBundle、ImportReceipt`）、`P12-04`、`P16-04` 与 `P39-*`。
- `blocking`：**no**（当前 P04-01 因 `G03` 未签收而处于 BLOCKED，本 issue 不是其当前阻断原因；但它必须在 P04-01 重新下发**之前**有结论，否则重发必然触发上述两难）。
- `decision`：`open`。候选处理方式（本 issue 不单方面裁决，也不修改任何冻结制品）：
  - (a) 把 `ScenarioBundle` 的**纯数据形状**补入 `DATA_CONTRACTS.md` 具名 Schema 表，并归到 `P02-04`（与同段的 `ScenarioSpec` 一致 —— 该段已确立“被 P03/P04 引用的纯值类型必须由 P02 定义，不能等到后续阶段”的规则）；
  - (b) 若判定 `ScenarioBundle` 属于仿真域装配产物而非纯值类型，则在契约中显式写明其定义任务（例如 `P11-01`）并在 `TASK_MANIFEST.json` 的相应任务 `allowed_files` 中给出承载模块；
  - (c) 若判定 `P04-01` 就应是它的定义者，则必须同时把承载文件加入 `P04-01` 的 `files`/`allowed_files`（当前白名单不含领域模块），并说明与 Constraint 6 的一致性。
  无论选哪一项，都属于契约变更，须先写 `contracts/changes/` 说明，再按 domain → DTO → ports → 调用方 → 测试 → 生成物 顺序迁移，并重验受影响 Gate。
- `owner`：契约所有者（`docs/architecture/DATA_CONTRACTS.md` 的维护方）决定归属；落地由被指派的阶段任务执行。与 `P04-01` 的重新下发存在时序依赖。
- `links`：`docs/architecture/DATA_CONTRACTS.md`（第 81、94 行）、`docs/architecture/IMPLEMENTATION_CONVENTIONS.md`（第 33 行）、`docs/api/API_CONTRACT.md`（第 47 行）、`docs/prompts/01-foundation/P04-01-canonical-fixtures.md`（第 90 行）、`docs/prompts/01-foundation/P04-02-database-seed.md`（第 68 行）、`artifacts/handoffs/P04-01/dsh/evidence.json`（`frozen_interface_unreachable`）。

## 2026-10-03 N01决定

- status：decided（归属），字段未决。
- blocking：yes；P02-04及ScenarioBundle消费任务派发前必须解决形状。
- decision：选择早期纯值归属P02-04，完整路径为`packages/domain/src/logistics_domain/runtime.py`；边界映射为`packages/contracts/src/logistics_contracts/runtime.py`。依据DATA_CONTRACTS的早期纯值规则及P04首次使用顺序，不延至P11，不允许P04重复定义。
- owner：A契约治理决定字段；P02-04实施，P04/P12/P16复用。
- unresolved：bundle成员、ScenarioRef完整引用/版本/hash语义、fixture期望与正式输入隔离结构证据不足。N01未创建字段；A治理须在派发前提交具体契约、正反例、依赖与生成验证决定。
- changed：catalog/runtime任务规则和model、DATA_CONTRACTS归属段、生成manifest/prompts、类型审计/issue索引及changes说明。业务Schema未生成，旧冻结hash/reviewer不更新，N02独立复核决定后续冻结。
- links：[类型审计](../TYPE_DEFINITION_OWNERSHIP.md)、[迁移说明](../../../contracts/changes/N01-governance-1.0.1.md)。


## N01-R01 完整决定（替代字段未决/仅下游派发限制）

- status：decided（完整设计）；READY_FOR_INDEPENDENT_REVIEW，非closed/Gate通过。
- blocking：yes，N02已经裁定G00冻结阻断；本轮实施者不得自行解除。独立N02重审新候选后决定。
- decision：JobKind五类及optimization三mode唯一states；CalendarInterval/ResourceCalendar在P02-01 primitives，新增必需epoch；ScenarioSpec/Ref/Bundle及直接嵌套事件/资源/Actor、JobCommand/RequestRef完整引用闭包早期唯一定义，禁止未来DTO导入。期望旁文件与正式运行输入严格分离。相关CLI/配置/主数据边界具名投影也明确字段/失败/版本语义，不再下发“请自造类型”。
- evidence：每项完整字段、依赖图、例子在[DATA本轮决定](../DATA_CONTRACTS.md#n01-r01-本轮完整契约决定)及[机器规范附表](../../../contracts/changes/N01-R01-contract-decisions.json)；逐项定义任务/文件在[类型审计](../TYPE_DEFINITION_OWNERSHIP.md)。新增选择明确为本轮设计决定，不伪称原条款。
- owner：A契约治理实施N01-R01；类型/行为由原manifest任务实施；独立N02负责冻结裁定。
- migration：数据契约1.0.0→2.0.0、计划1.0.2→1.0.3；最小恢复条件是本轮具体决定与验证被N02独立认可，然后才按授权归档历史并恢复真实冻结/G00。没有更新冻结reviewer/hash或Gate。详见[迁移说明](../../../contracts/changes/N01-R01-contract-freeze-2.0.0.md)。
