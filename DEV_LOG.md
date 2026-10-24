## 2026-10-24 · PARTNER · bootstrap 组合根与依赖装配（架构告警清零）

`backend/app/bootstrap.py` 由脚手架改为唯一组合根：`Services`（routing / warehouse_scheduler / warehouse_validator / simulator）+ `build_services()`（lru_cache 单例，只装真实 adapter）+ `describe_services()`。`application` 三个模块删除全部 adapter 导入，改为参数注入；`api/dependencies.py` 提供 `get_services` / `ServicesDep`，planning、events、simulations 三条路由透传。adapter 导入放在 `build_services()` 函数体内，因为 `simpy_simulator` 反向 import `coordinator`/`handle_event`，模块级会成环。

**`scripts/check_project.py` 从 exit 1（7 条 `application → adapters`）变为 PASS**；`verify_delivery.py` 首次 **12/12 全通过（exit 0）**。测试：`tests/test_bootstrap.py` 10 条；backend 全量 **328 passed**（基线 318 + 10）。契约 0.2.0 未变。

遗留：`api/routes/agent_demo.py`、`postgres_demo.py` 仍直连 adapters（本地 PG/Agent 演示子应用，已在测试中钉住名单）；持久化端口与 R08 协商未纳入组合根。详见[本轮增量日志](docs/devlog/entries/20261024-1500-partner-bootstrap-composition-root.md)。

## 2026-10-24 · PARTNER · R08 四角色合同网协商

`backend/app/application/contract_net.py` 由脚手架改为实现：协调者 + 仓储/运输/异常三个有界角色，CFP → 报价 → 冲突消解 → 授标 → 确认/撤销 → 关闭。报价须落在任务窗内且未过期；跨任务共享互斥资源的重叠报价记 `Conflict` 并通知落选方；全部确认 `confirmed`、达上限 `exhausted`、超时 `expired`、零可用报价 `infeasible`；外部可 `revoke` 释放授标；同 idempotency key 重放返回完全相同结果且不追加报文。transcript 带单调 `seq` 与 SHA-256 `digest`，全部时间由调用方传入模拟秒，模块不读系统时钟。**契约 0.2.0 未变**（协商报文不跨层、未上 HTTP）。

验证：`tests/negotiation` **25 passed**；backend **318 passed**（基线 293 + 25）；`export_contracts --check` 通过；`verify_delivery` 除既有 7 条 `application→adapters` 外全通过。

限制：未接 HTTP/前端与持久化；三个业务角色的报价来自资源日历/班次/恢复时长的解析式，未调用 CP-SAT/Routing；冲突消解为单轮贪心，无跨轮竞价。详见[本轮增量日志](docs/devlog/entries/20261024-1440-partner-r08-negotiation.md)。

## 2026-10-23 · PARTNER · R05 第二轮：CP-SAT 冷链约束接入

在契约 0.2.0 上接入真实求解约束（契约源与生成物**未改动**）：时变容量用 `(location, unit)` 分组 `AddCumulative`（半开区间、同秒先释放后占用）；多资源需求各自 `ExactlyOne` 并共用同一执行区间与资源日历；换批按方向性 setup 互斥，未登记类别对不按 0 处理；预冷限制可执行资源并强制早于装载；暴露只约束求解器可决定的仓内停留，其余交给独立校验按并集核算。

新增 `adapters/warehouse/coldchain_model.py`、`coldchain_timeline.py`、`coldchain_checks.py`，修改 `cp_sat_scheduler.py` 与 `validator.py`（`warehouse-validator-0.1 → 0.2`，新增 8 条 `r05.*` 规则与 `not_checked_rule_ids`）。校验状态在“无违规但存在未校验 R05 规则”时为 `not_checked`，不再冒充 passed。

验证：backend **293 passed**（新增 17：4 条真实 CP-SAT 端到端 + 13 条独立校验负例）；`export_contracts --check` 通过；`verify_delivery` 除既有 7 条 `application→adapters` 外全通过。

限制：甲方域层 `domain/coldchain_capacity.py`、`domain/joint_validation.py` 与 `tests/coldchain/` 未实现；准备包未回填、`prep_import_report.json` 未清零；`transport` 暴露段未产出；`explicit_operation` 换批只校验不生成。详见[本轮增量日志](docs/devlog/entries/20261023-2205-partner-r05-cpsat-coldchain.md)。

## 2026-10-23 · PARTNER · R05 冷链公共契约冻结（0.1.0 → 0.2.0）

契约版本升到 **0.2.0**：新增 `backend/app/contracts/coldchain.py`（容量维度、存储位置/占用、多资源需求与分配、换批策略、预冷、曝光、批次相容）与 `backend/app/ports/coldchain.py` 三个端口签名；`PlanningSnapshot.coldchain` 与 `WarehouseScheduleResult.coldchain` 均可空，`None` 表示不做 R05 声明，R05 规则须记为未校验。`ValidationReport` 增加 `not_checked_rule_ids` 并收紧两处：`passed` 不得携带未校验规则、`failed` 必须有违规项。生成物（VERSION/schemas/openapi/generated.ts/contractVersion.ts）全部由脚本重生成。

验证：`export_contracts --check` 通过、`contracts:check` 通过、`typecheck` exit 0、前端 10 组专项全 PASS、`npm run build` 2.17s、backend **277 passed**（基线 229 + 新增 48）、`build_file_map` 499 源文件。

范围限制：CP-SAT 接入、`import_preparation_bundle.py` 回填、`prep_import_report.json` 清零、域规则与 `tests/coldchain/` 均未做；R05 尚不可称为已支持。详见[本轮增量日志](docs/devlog/entries/20261023-2135-partner-r05-contract-freeze.md)与[契约冻结提案](contracts/changes/20261023-partner-r05-freeze.md)。

## 2026-10-22 · Git协作复制命令

新增 [Git协作手册](docs/GIT_COLLABORATION.md)，验证范围见 [增量日志](docs/devlog/entries/20261022-dsh-git-guide.md)。真实工程仍未初始化Git或推送。

## 2026-10-22 · DSH 可独立任务交接

快照 PostgreSQL 实测通过；指标/实验模块、手算正反例及T1真实重复实验已交付；历史断链已说明。范围与剩余契约阻塞见 [本轮交接](docs/devlog/entries/20261022-dsh-available-work.md)。版本化确认与完整R05/R09未签收，不沿用旧通过结论。

## 2026-10-22 · INTEGRATION-20261022 · 双人对接与前端

当前以 [协议 v2](COLLABORATION_SPLIT_20261021.md)、[构建规范](docs/DEVELOPMENT.md) 和 OWNERSHIP.json 为准。当前变更及验证见 [增量日志](docs/devlog/entries/20261022-dsh-integration.md)。下方 AC/B/C 分工与阶段状态为历史，不覆盖新协议。

## 2026-10-20 · R30-D · 仓储协同后端增强
- 继承 R30-C，新增 read-only 业务规则审计、仓运 handoff 时间独立校验和 DeepSeek 细节摘要。
- 不修改共有协议及数据库结构、不写正式数据、不重构原有 CP-SAT / Routing / 3D。
- PG 实时库存预留/隔离余额缺失，冷间长期占用、预冷和换批不予假称通过。
- 新增测试及 Windows 验收说明见 `docs/R30_STAGE_D_WAREHOUSE_BUSINESS_ENHANCEMENT.md` 与 `docs/devlog/entries/20261020-r30d-warehouse-enhancement.md`。

## 2026-10-20 · R30-C · DeepSeek AI Agent 组会 Demo
- 直接继承 R30-B 全部工程/数据/回放，新增本地隔离的 `/local-pg/pg-preview/r30c` status/chat/quick 接口；DeepSeek 官方 chat completions Function Calling，通过 httpx （已有依赖）访问，仅后端读取密钥、默认 `deepseek-flash`，HTTPS 官方域名白名单。无 SDK 锁定，无 SQL/Shell/提交工具。
- 三个受控操作绑定现有 R27 算法、PostgreSQL 只读摘要、R30-B 异常后缀：保持 R28 独立对账、只读校验、事件发生时间和车载货物约束。新增 React AI 对话界面、工具核验记录、快捷降级与 3D 回放会话内一次性交接，不重写旧求解算法。
- 新增 PowerShell `backend/start_pg_r30c_local.ps1`：可选择 `-DemoOnly`，交互密钥/数据库密码不会保存入工程。用户需本机填写自己的 DeepSeek Key，本交付无密钥。
- 验证：新增 pytest、现有 R30B/R27 定向测试执行结果记录在交付文档；该环境未能连 DeepSeek/PostgreSQL/OR-Tools，Node 依赖包含缺失包，无法完成真实 Windows/Vite 全量验收。
- 使用手册：`docs/R30_STAGE_C_DEEPSEEK_DEMO.md`。本阶段禁止夸大模型推理或实际派车与实路导航。

## 2026-10-20 · R30-B · 单仓异常后缀重调度
- 全栈继承 R30-A，增加 `POST /local-pg/pg-preview/r30b/reschedule`（本机开关+明确 dry_run 承认）；服务端重新读取/求解 R30A 原始来源，先做 R28 独立核验，不接受浏览器伪造方案，不向数据库执行写操作；新启动脚本禁用可写预览开关。
- 车辆途中故障：已完成事实冻结、在途车辆位置以路段而非 GPS 表示、车载货物仅在确认真实转运条件后才能重分配（R30B 暂不具备该模型，显式未服务）；可用仓库车辆运行原 OR-Tools。配送延误重新推算后续停靠时间窗/班次，不可行显式待处置。
- 仓储资源故障：固定原已开始事实，停止受影响未完成任务，调用已有 CP-SAT 求后续；订单温区、有效期、批次与运输装车约束相互作用。库存批次隔离中断相关未完成操作，阻止未合规货物继续配送；从 R24 严格校验的 PG 业务资料构造原先缺失的 Snapshot.StockLot（R24 仍无实时预占/质检数据）。
- React 新增独立异常面板及异动逐单对照、原始/重排 3D 共享回放、异常时车辆冻结、全量 JSON 一键导出。原 R27/R28、WH001/WH002 历史、3D 仓/四车仿真不删除，回放投影明确 `not_checked` 非可执行计划。
- 环境依赖未包含 OR-Tools/psycopg，不能完成 Windows 真库+真实优化器验收。Linux Node 依赖缺 Rollup 原生组件，完整 Vite build 未完成；TypeScript 检查通过。参考 `docs/R30_STAGE_B_EXCEPTION_RESCHEDULE.md` 的 Windows 验收清单。

## 2026-10-19 · R28 · 逐单对账 + 实库资料预检
- 纠正 R27 进度条中途“15 单规划送达”的统计误读：原计数是截至当前时刻的事件而非全程计划量，R28 页面分离两者并提供订单级核对表。
- 新增只读 `pg_r28_reconciliation`，核对计划范围、装车交接、路线、漏单/重单、发车先后、回放事件；不一致时拒绝 `validated` 方案。
- PostgreSQL 新增只读诊断与工作清单导出工具，报出 WH002 关联阻挡、R24/R27 缺项，并生成只有真实订单/车辆编号的 CSV，不写 DB、不伪造事实。
- R27 3D 场景、R22 归档、历史证据文件与公共契约保留。实机集成和完整前端构建仍由 Windows 验收。详见 `docs/R28_DATA_RECONCILIATION.md`。

## R26 · 单仓库 + 精细仓储数字孪生

- 新增单仓合成场景、3D 仓内分区、24 组货架、3 辆独立叉车任务回放、场景点选、CP-SAT 时间映射。
- 默认导入单仓场景；历史双仓场景作为旧测试/证据保留。
- PostgreSQL 明确显示单仓业务状态，独立只读预检和有备份确认的事务迁移。
- 选定后端回归 50 passed，R26/R25/R23 Node 前端专项检查通过；npm 依赖下载阻断完整构建，需 Windows 实机验证。

## 2026-10-18 · R25 · 流畅数字孪生 / 四车演示 / OSRM 3D 回放
- 用户授权跨全栈改 R25；React 仿真时钟解耦逐帧渲染与低频 UI 更新，3D WebGL 不因时间、仓库新数组、选车反复重建。四辆真实存在的快照车辆可单独错时沿示意道路演示，但不伪报最优路径。
- PostgreSQL OSRM GeoJSON 路线增加站点坐标用于 3D 轨迹映射，原数据/业务表/求解器/证据不动；另修 Windows PowerShell 脚本 UTF-8 BOM。
- 定向测试 46 passed、R25 Node 动画专项 PASS、R23 UI 测试 PASS；隔离环境缺 npm 依赖完整构建，需用户 Windows 验收。见 `docs/R25_TWIN_REPLAY_FLEET.md` 和本轮增量日志。

## 2026-10-17 · A/B/C 全栈授权 · R24 PostgreSQL 冷链字段 + OSRM + 仓储交接
- 用户允许跨 A/B/C/前后端直接修改，主要目标是赶功能、不反复做性能实验。
- 新增 OSRM 道路时长/距离/线型；保持旧直线模拟并用独立标注区分来源。增加六类扩展表及显式迁移、CSV 补录；仅有完整数据才由 R20 Routing 使用真实 volume/lot/shift/ready_at。已在 React 接入相关参数与缺口状态。
- 旧七张业务表、历史 R22 已存方案、R17～R20 算法证据不改；新提交仍仅限演示归档。详细代码/操作及未完成事项见 `docs/R24_POSTGRES_OSRM_COLDCHAIN.md` 与 `docs/devlog/entries/20261017-ac-b-c-r24-road-coldchain.md`。

# DEV LOG

## 2026-10-17 · CODEX_FRONTEND / AC · R23 实库 React 调度台
- 用户已提供 R22 保存成功响应及实际显示正常的地图；据授权开发 R23，不再重跑规模实验。
- React 新增 PostgreSQL 实库调度台 + 原订单和车辆页实库只读摘要；直接调用原 R21/R22 本机 API，实现预览、用户确认的模拟归档、列表和嵌入地图。原有 R20/B 算法、主接口契约和冻结证据未改。
- 33 项后端接口/契约选定测试通过、7 个 TS/TSX 改动文件语法解析通过、Node 接线冒烟检查通过。当前环境 npm 依赖不齐，**完整前端构建尚未验证通过**，需 Windows 安装依赖后验收。详见 `docs/R23_POSTGRESQL_REACT_INTEGRATION.md`、`docs/devlog/entries/20261017-ac-r23-pg-react-console.md`。

## 2026-10-17 · AC · R22 PostgreSQL 只归档模拟路线
- 用户上传 R21 本机 POST /route 返回截图：HTTP 200、`ROUTING_SOLUTION`、独立校验 `passed`、`unserved_orders=[]`；未把模拟求解误认成正式业务计划。
- 实现独立 `public.pg_simulation_previews` 演示归档；后端每次自行重新求解并校验，检查无漏单、订单覆盖、车辆重复及标注模拟假设后才允许事务单条写入。增加按编号查询、列表、GeoJSON 和简易只读地图。原 `dispatch_plans/routes/route_stops` 不变，用户需通过 `-CreateDemoTable` 显式建立演示表。
- B 求解器、公共合同、主 OpenAPI、前端、冻结实验数据保持不变；新增本机子应用操作默认关闭，且没有外网授权能力。R21 原只读启动方式保持不变。
- 本轮定向测试 38 passed；Contracts match source；仅余既有 7 条架构告警。测试范围及 Windows 使用步骤详见 `docs/R22_PG_SIMULATION_ARCHIVE.md`、`docs/devlog/entries/20261017-ac-r22-pg-simulation-archive.md`；当前隔离环境不能声称真库实际写入已验证。


## 2026-10-17 · AC · R21 PostgreSQL 真实读数及 R20 路由模拟预览
- 用户明确要求停止重复实验、尽快完成数据库接入与真实功能。交付：AC 新增只读 PostgreSQL 数据读取 adapter，实用订单、车辆、节点和距离视图；新增本机隔离 FastAPI 子应用 `/local-pg/`，含 summary/orders/vehicles/route API；Windows 启动脚本。
- `POST /local-pg/pg-preview/route` 在明确确认 `acknowledge_simulation_only` 后，映射为**唯一共享** RoutingRequest，调用 B 提供的**真实** `OrToolsRoutingSolver.solve()`，有解时另调用已有独立 `validate_transport`。不改 B 算法、不改仓储协调器、不写数据库。数据库读取事务严格 `REPEATABLE READ, READ ONLY`；新 API 需本机和 `PG_DEMO_ENABLED=1`，默认拒绝。
- 生产字段缺口（道路行驶时长、仓库归属、体积、仓运交接、班次、库存）以显式 `simulation_preview_not_executable` 报告模拟设定，绝不称为真实路况/可执行计划。只单仓/单温区/单趟，数值重量 kg 严格正整数；拒绝无法证明匹配的温区及不完整矩阵。禁止订单/车辆/方案写回；两个旧方案不受影响。
- OpenAPI：保留原九业务操作与共享 schema。新增子应用有自己 `/local-pg/openapi.json` 和 `/local-pg/docs`，不会污染原 `/api/v1` 派生 TS；B 路由实现、现有合同、前端 generated.ts、已冻结 R17 数据与 R20 基线逐字节匹配。
- 验证：新增脚本针对模拟字段及安全/缺数据反例，定向 `backend/tests/test_pg_routing_preview.py` + `backend/tests/test_contracts.py` → **23 passed**；`compileall` 通过；`export_contracts --check` 通过；`check_project` 仍 7 条既有架构告警。隔离环境无 PostgreSQL 访问/OR-Tools/psycopg 可下载，**无法声称已经在用户数据库上端到端运行；必须由用户 Windows 本机实际运行验收**。
- 未完成：正式仓运联合调度数据建模、实路网时长、持久化/事务写回、React 页面业务接入。当前本地数据只读预览不得作为正式计划确认。指南：`docs/R21_POSTGRES_R20_INTEGRATION.md`。

## 2026-10-16 · 工程顶层目录整理（不改正式调度业务）
- 将旧代码归档至 `archive/legacy/`，旧教学样例至 `archive/reference_demos/`，旧发行包至 `archive/releases/`；部署与平台预留合并至 `infra/`。
- `backend/`、`frontend/`、`contracts/`、`data/`、`benchmarks/` 路径与业务文件保持原样；修正工程路径引用、OWNERSHIP、源文件清单和打包脚本，增加 `--include-archive` 打包完整历史交付选项。
- 不携带可重建的依赖/构建/缓存：node_modules、dist、target、__pycache__、.pytest_cache；原历史源码和冻结实验保留。
- 验证与范围见 `docs/PROJECT_LAYOUT_R20.md`；旧版日志内容不追溯修改。


## 2026-09-10 B02 Routing V1.1
- Owner: B
- Scope: RoutingRequest → matrix adapter → OR-Tools RoutingModel → vehicle assignment → stop sequence → arrival time → distance/duration → independent validation → RoutingResult.
- Implemented: versioned fixed matrix provider, one-warehouse/one-trip RoutingModel, weight/volume capacity, temperature compatibility, vehicle shift/availability, warehouse handoff window, order service windows, freshness deadline, frozen route constraints, independent transport validation.
- Important correction: order service duration is part of the OR-Tools time dimension; it is no longer added only when serializing the result.
- Contract change: none.
- Cost: kept as a B-owned sidecar metric because shared RoutingResult currently has no transport-cost field; no private contract mutation.
- Tests: backend 26 passed; Python compileall passed.

## 2026-09-11 B02 runtime compatibility fix
- Fixed `backend/app/adapters/routing/ortools_solver.py` to stop assigning `random_seed` to `RoutingSearchParameters`.
- OR-Tools 9.15 `RoutingSearchParameters` in the Windows runtime does not expose a `random_seed` field, which caused real `/api/v1/planning-jobs` execution to fail after snapshot import.
- Routing remains otherwise unchanged; the shared request budget still controls `time_limit`.


## 2026-10-12 B03 R17 双向仓运协同（用户明确优先指派）
- 基于 R16_SPEED 单轮保底，增加 opt-in `coordination_mode=deep`，CP-SAT 接收真实运输发车软目标，最多三轮共享总预算反馈，重新 Routing 并逐级独立验证。
- 严格字典序挑选不差的候选，避免因更长距离换取更短装车等待；反馈失败保留合法初始解。
- `planning.py` 以可选字段添加 WarehouseDepartureTarget、CoordinationReport、CoordinationRound，不改变已有字段定义；导出 OpenAPI/JSON schema。
- 更正前端交接窗口判断，增加模式选择、逐轮证据、JSON 导出；提供独立等预算脚本 `python -m tools.r17_joint_ablation`。
- 防虚假结论：不同预算非公平对照，合成场景与真实道路不同；本机环境没有 OR-Tools 实算可用库。
- 验证：47 passed、1 skipped；R15 evidence/R16 speed Node 测试通过；前端 TSX 语法检查通过；独立方案验证负例。完整前端构建/真实 OR-Tools 在用户 Windows 验证。
- 原有架构静态检查器（application→adapters）报历史直接引用，本版本未扩散改造 AC 组合根。

## 2026-10-14 成员 B · R18 B-06 多场景公平对照证据升级
- 以 R17 已验收证据（原始 JSON、场景 SHA256 与全候选解）为历史基线，**没有重新运行 R17 正式实验**。独立核算 20 单交接等待和距离：4500/2400 秒、56/56 km；原验证器的 passed 仅作原始记录。
- 新增生成 12/16/20 单的 5 个预注册不同 Seed 场景的后端多场景成对工具；单轮/deep 都复用 R17 `run_comparison/coordinate`，每组等预算，逐组保存原始 CandidatePlan/失败和 CSV/JSON/Markdown 汇总。
- 对输出另做订单覆盖、交接等待、距离、轮次/校验完整性检查；距离不同不披露等待改善率；样本不够不输出平均收益。
- 前端 B-06 新增 R17 已验收历史证据展示/下载，顶部 R16 版号改 R18；旧 B-06 评测不修改。
- 接口变动：无。部署/生产数据库变动：无。真实新多场景求解：**未执行**（交付环境缺 OR-Tools、SimPy、完整 npm 依赖且无联网）。
- 本机测试详情以 R18 指南及实际验收记录为准；保留历史 R17 工程作为回退。

## 2026-10-14（补）成员 B · R18 收尾验收：证据冻结、缺陷修复与交付
- 上一条记录的“真实新多场景求解：未执行”属于更早的交付环境；用户在 Windows 机已真实跑完 R18 五组（5/5 有效、等距离、描述性平均改善 40.13%），本条为收尾验收增量，不改写历史条目。
- 冻结归档：新增 `backend/tools/r18_acceptance_freeze.py`，把 `benchmarks/b03/r18_runs/run_20261014_212550_205783` 逐字节冻结到 `benchmarks/b03/r18_accepted/`（14 个证据文件 487201 字节），并生成逐文件 SHA256 清单 `r18_accepted_manifest.json` 与独立复算 `r18_multiscene_audit.json`（5 组全部与运行 summary 一致，`s20_seed66` 与 R17 档案交叉核对 match）。原运行目录保留不动。
- 字节还原：`benchmarks/b03/r17_accepted/r17_arithmetic_audit.json` 恢复为交付包原始字节 `f70edfc7…`（1061 字节），上一轮重跑产生的 `060fd844…` 作废。
- 缺陷修复：`requirements.txt` 补 simpy、`requirements-lock.txt` 补 ortools/simpy 及其依赖（P0-1/2）；README 与 R18 两份文档的版本与“未执行”口径按“保留历史正文、追加实测段落”处理（P0-3/4）；三个证据工具的 `write_text` 加 `newline='\n'` 消除 Windows CRLF 哈希漂移（P1-5）；`generated.ts` 用锁定工具链重生成并登记 `70a82f17…`（与重生成前逐字节相同，P1-6）；打包排除 `r18_runs/**` 与 `*.err`（P1-7）；按用户授权把 `handle_event.py` 函数内 import 提到模块顶部（P1-8）；新增 `.gitignore`（P2-13）；删除 3 个临时日志。
- 接口变动：无（`contracts/VERSION`、`contracts/openapi.json` 未变，`export_contracts.py --check` 通过）。部署/数据库变动：无。
- 验证（Windows 实机原始结果）：`python -m pytest -q tests` → 62 passed（3.20s）；`compileall` → exit 0；`export_contracts.py --check` → Contracts match source；`check_project.py` → 仅 7 条既有 `application→adapters` 告警（P1-9 未处理）；前端 `contracts:check`/`test:evidence`/`test:speed` 全 PASS；`npm run build` → exit 0，`✓ built in 2.06s`。
- 未完成：P1-9 架构告警、R18 结果上网页（未授权）、场景扰动增强与“深协同代价”汇总维度（应作为 R19 协议 1.1，不回改已冻结证据）、OWNERSHIP.json 中 `backend/tools/` 与 `benchmarks/b03/` 仍按默认解析为 AC（待用户确认后再同步）。
- 交付：`artifacts/R18_B06_MULTI_SCENE_EVIDENCE_20261014.zip`（第一层仅 `R18_B06_MULTI_SCENE_EVIDENCE/`，236 个条目；权威大小与 SHA256 见包外同名 `.sha256` 文件）；`FILE_MAP.md` 重建（235 个源文件，`--check` 通过）；`scripts/package_demo.py` 新增 `--top-level`（默认 `demo` 不变）并校验单一顶层文件夹；根 `PACKAGE_MANIFEST.json` 已同步为新包清单。
- 详见 `docs/devlog/entries/20261014-2330-b-r18-acceptance-freeze.md`。

## 2026-10-15 成员 B · R19 B-04 异常重调度三策略对照（真实跑完）
- 用户明确指派「直接写代码实跑」。实现 `backend/tools/r19_reschedule_ablation.py`：预注册协议 `r19-b04-reschedule-strategies-1.0`，3 场景 × 2 场景族 × 4 档延误 = 24 组等预算对照，三臂为不重调度 / 全量重调度（重跑 CP-SAT+Routing）/ 局部重调度（现有 `handle_event`）。
- 真实运行：`--case-count 3 --budget-ms 60000` → `benchmarks/b04/r19_runs/run_20261014_235140_246501/`；冻结到 `benchmarks/b04/r19_accepted/`（16 文件 5 003 952 字节，`r19_acceptance_freeze.py` 逐组重算 **24 组 mismatches=0**）。
- 结果：完整三臂对照 15/24；各臂校验通过 不重调度 15、全量 21、局部 15。`stress` 族 14 400/28 800 s 档三场景一致：不重调度 3–4 单迟到且双重违约；全量重调度全部准时、校验通过、距离不变、3–4 单改派备用车、交接等待 96 570→50 490 s 与 133 110→77 310 s；局部重调度 **失败**（`ROUTING_NO_SOLUTION`，2–136 ms）。`base` 族 28 800 s 档两个求解臂快速失败（每温区仅一辆车，结构上不可恢复），求解器拒绝输出违约方案。SimPy 回放两次摘要完全一致。
- **实验确证 B-04 缺陷**：局部重排冻结所有未受影响路线，含空闲备用车的空路线；`_apply_frozen_routes` 对空冻结路线 `NextVar(start)=end`，禁止该车装载。隔离诊断（`tools.r19_frozen_spare_diagnostic`）：含空闲车冻结 → 无解、服务 0 单；排除空闲车 → 有解、服务 6 单（`veh_2` 3 单 + `veh_1b` 3 单）。**未修**（跨 application/adapters，待授权）。
- 另一实测事实：运输弧成本只有距离，等待/延误不进目标函数，因此原车仍可用时改派备用车无成本收益——这解释了多数档位三臂完全相同。
- 方法学披露：延误梯度与 `stress` 族在若干次降预算冒烟运行（1 场景、15 s、临时目录、不入证据）之后才定稿，已在日志与指南中声明。
- 接口变动：无（`export_contracts.py --check` 通过）。部署/数据库变动：无。均值未发布（15/24 未全完成，按纪律不出平均）。
- 未完成：B-04 冻结缺陷未修（需授权后重跑才能得到完整网格）、R19 结果未上网页、P1-9 静态告警。
- 详见 `docs/devlog/entries/20261015-0030-b-r19-three-strategy-ablation.md` 与 `docs/R19_B04_RESCHEDULE_GUIDE.md`。

## 2026-10-15（补）成员 B · 修复 B-04 冻结空闲备用车缺陷并重跑 R19（v2，当前结论）
- 用户明确授权"先帮我修"。修复 `app/adapters/routing/ortools_solver.py::_apply_frozen_routes`：**没有配送停靠的冻结路线直接跳过**，不再对空闲备用车执行 `NextVar(start)=end` 并固定首末时刻。非空冻结路线行为不变，契约与 API 未动。
- 新增回归测试 `backend/tests/transport/test_frozen_empty_route.py`（真实调用求解器断言空闲备用车仍可派单 + 源码保留保护分支）。
- 复验：`tools.r19_frozen_spare_diagnostic` 含空闲车冻结一行由"无解/服务 0 单"变为"有解/服务 6 单（`veh_2` 3 单 + `veh_1b` 3 单）"。
- v2 重跑 `run_20261015_004322_357508`，冻结 `benchmarks/b04/r19_accepted_v2/`（16 文件 5 470 200 字节，24 组复算 mismatches=0；归档清单新增记录求解器与 `handle_event.py` 的实现哈希）。v1 归档原样保留不覆盖。
- 结果变化：完整三臂对照 15/24 → **21/24**；局部重调度校验通过 15 → **21**（与全量持平）；`stress` 族 **12/12** 完成并发布族均值：不重调度平均累计迟到 24 015 s、全量/局部均为 **0**；距离增量均为 0；平均耗时 全量 50 630 ms、**局部 22 510 ms**（省 55.5%）。全网格均值仍不发布（`base` 族 9/12，其 28 800 s 档属结构性不可行）。
- 分析规则修订（已披露）：v2 前加入"族内全部完成即发布族均值"；属已知 v1 结果后的修订，不影响任何数值，理由与声明写在增量日志中。
- 验证（原始结果）：`pytest` → **81 passed**（新增 3 条）；`compileall` exit 0；`export_contracts --check` → Contracts match source；`check_project` → 仍 7 条既有告警（未新增）；`build_file_map` → 280 文件且 `--check` 通过；前端三测 PASS、`npm run build` → `✓ built in 3.04s`。
- 未完成：R19 结果上网页（未授权）、P1-9 架构告警、`base` 族结构性不可行（需 R20 场景设计）。
- 详见 `docs/devlog/entries/20261015-0130-b-r19-b04-fix-and-v2.md`。

## 2026-10-15（补 2）成员 B · R20 目标函数尝试 + B-04 异常类型扩充
- 目标函数（用户选定"等待进目标"）：`ortools_solver.py` 新增 `waiting_s` 维度与软上界，代价恰为 `发车 − ready_at`（插桩验证）。**实测未生效**：系数提到 100 000 仍选等待重的方案 → 该搜索配置不优化软上界代价；已写 `KNOWN LIMITATION` 并用测试钉住当前行为，避免被误读为已优化。
- 过程中**修复一个真实缺陷**：`VehicleVar == (v+1)*active − 1` 使局部搜索从不激活另一辆车的订单副本；改为原生定域 `VehicleVar.SetValues([v, -1])` 后，构造实例距离由 3100 m 降到 2200 m。真实场景 A/B：R19 v2 六份基线距离**全部 0 变化** → 冻结证据不受影响、仍可比。
- 协调层择优（用户后续选定）：`_solve_pair` 增 `seed`、深协同每轮换种子且取消"候选未变好即退出"。实测与冻结 R17 证据**逐轮完全相同**（sequential 4500 s / deep 2400 s）→ 该指标已达当前架构不动点，建议停止投入。
- B-04 异常类型扩充：新增 `dock_unavailable`（月台封锁 → 装车窗口起点抬到重开时刻、`ready_at` 不变、赶不上的订单记入未服务）与 `cargo_quarantined`（订单移出重排并记录原因）。求解器补上 `start ≥ loading_window.start_s`（此前仅校验器把关）。**未改公共契约**。
- 真实求解器实测（20 单双仓）：月台封锁 3600 s → wh_1 两车发车 480/600 → 3600，20/20 单仍服务、校验通过；隔离 2 单 → 18 单照常、2 单以 `cargo_quarantined` 记录。
- 验证：`pytest` → **94 passed**；`compileall` exit 0；探针 `tools.b04_event_probe` 两种事件均 OK。
- 未完成：`weather_changed`（缺矩阵提供方）、`demand_changed`（缺契约字段）、月台粒度是仓库非装卸口、新事件未接入 SimPy 事件流；本轮与上一轮改动**均未打包**。
- 详见 `docs/devlog/entries/20261015-0230-b-r20-routing-objective-attempt.md`、`20261015-0330-b-r20-b04-event-types.md` 与 `docs/B04_EVENT_TYPES_R20.md`。

## 2026-10-15（补 3）成员 B · R20 三种异常接入 B-05 仿真事件流
- `simpy_simulator.py` 新增 `baseline_order_ids()`：**只有 `departure_delayed` 的 `affected_order_ids` 可用作基线缩小范围**；月台/隔离若沿用旧提示逻辑，基线方案里根本不会有事件要处理的订单。
- 新增两类显式失败：`simulation_unsupported_event_types:<types>`（在花基线预算之前校验）与 `simulation_horizon_cut_event_stream:<ids>`（此前 horizon 不足会**静默丢掉尾部事件**，产出看起来正常的残缺结果）。
- 失败语义文档化：任一事件处置失败即中止整场仿真并向上抛，HTTP 层记为失败作业；`emitted_events` 只含真正回放成功的事件。
- 新增 `backend/tools/b05_event_stream_probe.py`（真实求解器、跑两次做确定性对比、打印最终方案）与 3 条测试（`tests/test_b05_simulation_contract.py` → 5 passed）。
- 实测（20 单双仓，预算 12 s）：0 s 延误 900 s → 1200 s wh_1 月台封锁至 3600 s → 3600 s 隔离 ord_001/ord_002，**3/3 事件应用**，最终快照 v4；`veh_1`/`veh_2` 推到 3600 s、wh_2 保持 600/540；18 单服务、2 单记为 `cargo_quarantined`；同种子两次快照摘要**完全一致**。
- 契约未改动（未新增字段，无需重生成 OpenAPI/前端类型）。
- 未完成：`weather_changed`（缺矩阵提供方）、`demand_changed`（缺契约字段）、事件流仍是预置列表而非状态触发、月台粒度为仓库。
- 详见 `docs/devlog/entries/20261015-0430-b-r20-b05-event-stream.md` 与 `docs/B04_EVENT_TYPES_R20.md`。

## 2026-10-15（补 4）成员 B · 交接整理：去重与归档（用户选定 B/D/E）
- 用户要求清理冗余以便交接，选定：删重复运行目录、历史 md 归入 `docs/history/`、修复"被引用但没打包"的指南；明确**不**动 `node_modules`/`dist`/缓存、旧 ZIP、Spring Boot 编译产物。
- **先证后删**：三份冻结归档与其来源运行目录逐文件比对 SHA256（14+16+16 个文件），**0 处不符**；唯一未归档的 R18 dry-run manifest 与归档版只差 `status` 字段（`not_started` vs `complete_validated_pair`），判定冗余。
- 删除 `benchmarks/b03/r18_runs/`（20 文件 0.67 MB）与 `benchmarks/b04/r19_runs/`（32 文件 9.99 MB）；移动 13 个零引用历史文档 → `docs/history/`，4 个现行指南（R15/R16/R17/WINDOWS_SETUP）→ `docs/`。
- 修复 6 处断链（README 的 R17 指南链接 + `docs/history/` 内 5 处），复扫确认所有引用指向存在的路径；3 份归档 README 与 3 处指南说明同步更新（归档 README 不在哈希清单内，改动不影响完整性声明）。
- **顺带修好真问题**：`R15/R16/R17` 指南与 `WINDOWS_SETUP.md` 原在根目录、不在 `project_files.py` 的根文件白名单 → **历次交付 ZIP 里这几个链接是断的**；移入 `docs/` 后随包交付（源文件数 289 → 308，已核对 `IN`）。
- 新增 `benchmarks/README.md`（证据 vs 过程输出、归档校验方式、重跑命令）与 `docs/history/README.md`；README 增加阅读顺序第 6/7 条与目录说明。
- 验证：`build_file_map.py` → 308 源文件、`--check` 通过；`export_contracts.py --check` → Contracts match source；`check_project.py` → 仍既有 7 条（未新增）；`pytest` → **97 passed**。目录 162.27 MB/7420 文件 → **151.61 MB/7368 文件**；根目录文件数 25 → **9**。
- 未改动任何业务代码、契约或证据内容。历史增量日志与 DEV_LOG 既有条目未改写。
- 详见 `docs/devlog/entries/20261015-0530-b-handover-cleanup.md`。

## R27 · 单仓库业务闭环（2026-10-18）
- 新增 PG R27 作业资料增量表、只读资料完整性接口、事务型 CSV 插入工具；没有默认假数据和自动迁移。
- 新增 R27 同一快照 CP-SAT 仓储调度 → OR-Tools 路线调度 → 交接/出发/送达/回仓校验后事件投射接口。
- 独立 React 一体化演示页面，单时间轴切换单个可见 3D 场景，支持真实补录与合成场景两种有明确来源的模式。
- 限制：没有 OSRM、没有真实 WMS/AGV 遥测，不能宣称数据库已迁移或业务库存已自动修改。

## R29（2026-10-19）单现役仓库受保护迁移
- 根据 Windows 只读实库预检：WH002 2 辆车及 4 条历史 routes 引用，R24 资源/库存等引用计数为 0。新增显式事务迁移与历史保留审计、现役写入守卫。
- PostgreSQL 原历史 routes/route_stops/dispatch_plans 不改不删。WH002 保留历史外键，R29 实库预览只读过滤 WH002 节点与矩阵距离；目前不做物理删除。
- Windows PowerShell 5.1 兼容 UTF-8 BOM，提供 pg_dump 备份与可读性检查和显式迁移脚本。

## R30-A · 数据驱动仓运联调（2026-10-19）
- 保留 R29 WH001 单现役仓库迁移标识与所有历史路线，不改基础业务表；既有演示场景/3D 页面保留。
- 新增 `pg_r30a_bundle.py`：基于只读基础表生成七份明确标记为合成演示的扩展 CSV；先通过 R27 PostgreSQL PlanningSnapshot 桥接进行可验证的数据形状与约束预检。
- 显式备份和二次确认后，在一笔事务里只新增 R24/R27 扩展资料及 `pg_r30a_data_provenance`，拒绝覆盖已有扩展数据、基础数据漂移与不支持的车辆温控能力。
- R27 方案保留真实 CP-SAT/OR-Tools 算法调用和 R28 逐单对账；来源标记传播到后端 Source、结果和前端页面，禁止把生成数据称为实测。
- 新增 `r30a_data_local.ps1`、`backup_pg_r30a_local.ps1`、`start_pg_r30a_local.ps1` 和 Windows 使用指南；默认无数据库写入。
- R30 阶段 B（异常与重调度）/C（Agent）未在此版本实施。
