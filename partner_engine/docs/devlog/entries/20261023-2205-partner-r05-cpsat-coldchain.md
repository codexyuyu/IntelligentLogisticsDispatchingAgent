# 20261023-2205 · PARTNER · R05 第二轮：CP-SAT 冷链约束接入与独立校验

- 角色 / 日期 / 基线提交：PARTNER（乙方）/ 2026-10-23 / 基线 `a9f923a`（R05 契约 0.2.0 冻结），分支 `partner/r05-cpsat-coldchain-20261023`
- 对应任务 ID / 状态：R05 求解器接入 → **adapter 层已实现并有真实 CP-SAT 回归**；域独立校验（甲方）与准备包回填仍未做
- 完成及修改文件：
  - 新增 `backend/app/adapters/warehouse/coldchain_model.py`（CP-SAT 侧 R05 约束建模：时变容量累加、多资源、换批、预冷、暴露上限）
  - 新增 `backend/app/adapters/warehouse/coldchain_timeline.py`（结果侧：占用区间、曝光分段、换批记录，实现 `ports/coldchain.py` 的 `OccupancyTimelineBuilder` 语义）
  - 新增 `backend/app/adapters/warehouse/coldchain_checks.py`（独立校验：8 条 `r05.*` 规则 + 未校验项）
  - 新增 `backend/tests/warehouse/test_r05_coldchain_scheduling.py`（17 条：4 条真实 CP-SAT 端到端 + 13 条独立校验负例）
  - 修改 `backend/app/adapters/warehouse/cp_sat_scheduler.py`（R05 分支建模、多资源分配、窗日历复用、结果挂 `coldchain`）
  - 修改 `backend/app/adapters/warehouse/validator.py`（接入 `r05.*` 规则与 `not_checked_rule_ids`，版本 `warehouse-validator-0.1 → 0.2`）
  - `DEV_LOG.md` 与 `FILE_MAP.md`（重建）
- 契约版本前后 / 变更提案：**0.2.0 不变**（本轮只改 adapter 与测试，未动共享契约与生成物；`export_contracts.py --check` 仍通过）
- 输入输出、单位、状态、URL 变化：
  - 无新字段、无新 endpoint。`WarehouseScheduleResult.coldchain` 此前恒为 `None`，现在在快照带 `coldchain` 时由 `ColdChainTimelineBuilder.plan()` 填充
  - 校验 `status` 新增取值场景：无违规但有未校验 R05 规则时为 `not_checked`（此前只会 passed/failed）
  - 容量维度、半开区间 `[start,end)`、`weight_g/volume_cm3/quantity_units` 口径沿用契约 0.2.0
- 实现要点（可复验）：
  1. **时变容量**：占用区间由 `NewIntervalVar(inbound_end, size, outbound_start)` 表达，按 `(location, unit)` 分组 `AddCumulative`；同一秒先释放后占用。
  2. **多资源**：主需求约束 `resource_id` 资源集；其余需求各自 `ExactlyOne` 可选区间并共用同一 start/duration，同时复用可用窗/不可用窗日历；结果逐需求输出 `resource_assignments`。
  3. **换批**：资源上两两互斥加方向性 setup 时长；`initial_setup_class` 对首项生效；未登记的类别对**不按 0 处理**——只允许已知方向，双向均未知则禁止共用该资源。
  4. **预冷**：预冷工序只允许落在 `eligible_resource_ids`，且各装载工序 `start >= precool.end`；`duration_s < min_duration_s` 在建模前直接判不可行。
  5. **暴露**：求解器只约束自己可决定的仓内停留（`in_warehouse`）与已知装载时长，`max_exposure_s - Σ装载时长` 作为仓内预算；等待/运输段由独立校验按并集核算，不猜。
- 验证命令、通过/失败原始结果（Windows，Python 3.12.10，`PYTHONUTF8=1`）：
  - `python -m pytest -q`（backend）→ **293 passed**（本轮新增 17，前一轮基线 277）
  - `python -m pytest -q tests/warehouse` → **17 passed**
  - `python scripts/export_contracts.py --check` → `Contracts match source`（契约未改）
  - `python scripts/build_file_map.py --check` → 通过
  - `python scripts/verify_delivery.py` → 11/12 项 exit 0，`architecture` exit 1（main 上既有 7 条 `application→adapters`）
- 未完成/已知限制/阻塞：
  - **域层属于甲方**：`domain/coldchain_capacity.py`、`domain/joint_validation.py`、`backend/tests/coldchain/` 仍未实现，本轮的 `r05.*` 是 adapter 侧校验，不能替代甲方独立重建
  - `scripts/import_preparation_bundle.py` 未回填，`prep_import_report.json` 的 losses 未清零，真实 B20/T1/A8 场景尚未带 R05 数据跑通
  - 暴露只覆盖 `in_warehouse` + `loading`；`transport` 段依赖 joint validation 从 `VehicleRoute` 推导，本轮未产出
  - 换批 `rendering='explicit_operation'` 只做“缺口 + 必须有 setup 工序”的校验，求解器**未生成** setup 工序实体（仍以 `gap` 渲染为主）
  - 预冷 `target_temperature_zone` 未与批次温区交叉校验（资源不携带温区字段）
  - 未知类别对的保守处理可能把本可排的方案判为不可行（已记录为 fail-closed 取舍）
  - `architecture` 既有 7 条告警未修（属组合根任务）
- 交给谁 / 对方下一步：
  - 甲方（DSH）：复验本分支；按 `contracts/changes/20261023-partner-r05-freeze.md` §6 实现域层并回填准备包；对“未校验不得 passed”的口径确认
  - 乙方（自己）：下一轮做 `import_preparation_bundle.py` 回填与真实场景回归（待甲方/用户授权，因该文件属甲方）
