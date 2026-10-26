# R27 · 单仓库冷链仓运业务闭环（开发交付说明）

## 目标与边界

R26 的仓库 3D 动画已经在 Windows 浏览器通过用户实机检查。R27 重心由视觉效果转向**一个仓库、同一批订单、同一条可以独立校验的业务时间线**：订单及库存资料 → CP-SAT 仓储作业（给出具体资源、开始结束时刻）→ 每单 `ready_at` → OR-Tools 车辆分配/路线/时间窗 → 配送与回仓事件 → 共用进度条的 3D 展示。

**这仍是只读、不可执行的计划预览**：不改变 `delivery_orders`、`vehicles`、库存、`dispatch_plans/routes/route_stops`、历史归档；不冒充叉车设备遥测或客户真实签收。没有 OSRM 时，路线仍是合成矩阵或 PostGIS 直线估计；不伪造真实道路或拥堵。

## 两种来源

**A. 单仓演示闭环（无需新的数据库补录）**

前端菜单 **智能调度 → R27 仓运业务闭环**，选择 **单仓演示** → **运行 R27 仓运一体化只读预览**。后端读取版本化的 `data/scenarios/single_warehouse_20_orders.json`（1 仓/20 单/4 车/批次/资源/作业），真调用 CP-SAT 与 OR-Tools，然后独立验证完整方案，生成 `warehouse_work_start/finished`、`loading_ready`、`vehicle_departure`、`order_delivered`、`vehicle_return` 事件。两个 3D 页面共用同一仿真时钟，一次只显示一幅 WebGL 场景，防止叠加渲染。车辆数由真实求解器决定，不强制凑四车。

**B. PostgreSQL 核验闭环（必须有实际录入的数据）**

必须满足：PostgreSQL 已经安全统一为唯一业务仓库 `WH001`，R24 六张表已增量创建且订单、车辆、仓温区、库存批次、可用资源、装卸交接等资料完整，另外手动录入 R27 仓储作业工时、资源及先后关系（见下文）。R27 单温区求解一次只处理一种温区，**不是跨冷藏/冷冻合并承运，不是正式业务落账**。

此模式的严格边界：

- 一个订单必须有作业资料，并且有且仅有一条 `load` 装车作业；此前该订单的每条 `pick`/`stage` 作业必须通过 `predecessor_code` 链路接到装车操作。
- 绑定的真实 R24 资源必须存在于同一仓库与温区；`pick`/`stage` 使用冷库/预冷资源，`load` 使用装卸月台；CP-SAT 在 R27 模式不允许私自将作业改派给其他资源。
- 每项操作的时长、释放与截止时刻全部来自 CSV/数据库，不用重量系数推测时长；超时、缺少先后关系、跨订单依赖、循环引用、温区冲突都会显式拒绝。
- R24 所录入的 lot/订单数量、温区、车辆班次、体积/重量/余额、月台可用时段等沿用 R24 桥接校验；生成的 `ready_at` 从实际排程结果计算，不使用 R24 假设值替换；出车时间不能越过既有月台装车截止。
- 求解使用 R24 只读 PostgreSQL 视图和 PostGIS 估计距离（可选 OSRM 但未部署）；不能用这套预览向车辆发车或标记库存已消耗。

## Windows 启动（不重新做 R24 实验）

保留 R26，R27 解压到新文件夹。先关闭 R26 后端，避免端口 8000 冲突：

```powershell
# R27/backend
powershell -ExecutionPolicy Bypass -File .\start_pg_r27_local.ps1

# R27/frontend，在另一个 PowerShell 窗口
npm ci
npm run build
npm run dev
```

浏览器 `http://127.0.0.1:5173` → **智能调度 → R27 仓运业务闭环**。先用 **单仓演示** 检查事件流、统一进度条、仓库 3D 和配送 3D。不需 OSRM，不需变更数据库。

## 实库模式增量表及 CSV（只有你选择才会写数据库）

**先备份 PostgreSQL**，并用 `pg_restore -l` 或 pgAdmin 检查备份。R26 的单仓迁移工具必须先只读预检；如现有历史路线/库存引用 WH002，则**拒绝一键合并，不要强制删除**。如果实库仍未统一，R27 实库模式会显示缺项并拒绝运行，演示闭环仍可用。

R27 仅需新增一张**独立扩展表** `pg_r27_work_operations`，原 R24 六张业务扩展表继续沿用；无自动演示种子，也不会修改旧业务表：

```powershell
# R27/backend；首次安装表（需要手动确认/备份，非必需）
powershell -ExecutionPolicy Bypass -File .\start_pg_r27_local.ps1 -CreateR27Tables
```

如果 R24 扩展表从未创建，可添加 `-CreateR24Tables`，但你之前已安装 R24，不需重复。初始化表后，页面会准确提示还有多少订单缺少作业信息。**空表不代表可直接做实库闭环。**

使用 `data/pg_r27_templates/work_operations.csv` 作为无数据模板，并从你的业务资料填写：

| 列 | 含义 |
|---|---|
| `operation_code` | 唯一作业编号，ASCII 字母数字连字符或下划线 |
| `order_code` | 现有订单号（如 ORD001） |
| `warehouse_code` | 必须为 WH001 |
| `resource_code` | 已手工录入的 R24 资源编号 |
| `operation_kind` | `pick` / `stage` / `load` |
| `duration_s` | 真实提供的正整数操作秒数 |
| `release_at`, `deadline_at` | 资源最早开工及最晚完工 ISO8601 时间，**必须带时区** |
| `predecessor_code` | 前置作业编号，无前置则留空；最后的装车作业要依赖此前所有作业 |
| `observed_at` | 数据观测时刻（带时区） |

```powershell
# R27/backend，先校验本地 CSV，完全不会连数据库
powershell -ExecutionPolicy Bypass -File .\import_pg_r27_local.ps1 -CsvPath ..\data\pg_r27_templates\work_operations.csv

# CSV 填写完整、旧业务和 R24 相关资料就绪、备份已验证后，才可以显式导入
powershell -ExecutionPolicy Bypass -File .\import_pg_r27_local.ps1 -CsvPath .\my_work_operations.csv -Apply -BackupVerified
```

导入为事务性 INSERT ONLY：有重复作业编号、无效外键或非法值就会整体失败；不能悄悄修改已存在的实库标准。CSV 必须是有实际记录的文件（空模板会拒绝）。

## 接口

- `GET /local-pg/pg-preview/r27/readiness`：只读检查单仓、R24 和 R27 资料缺口，并返回缺失订单编号；不判断所有业务约束已经正确。
- `POST /local-pg/pg-preview/r27/workflow`：显式 `{ "source":"single_warehouse_demo", "budget_ms":60000,"acknowledge_dry_run_only":true }`；或者 `{ "source":"verified_postgres", "temperature_zone":"chilled", "budget_ms":60000, "acknowledge_dry_run_only":true }`，要求资料齐全并再次执行约束校验。
- 返回 `snapshot`、`plan`、统一 `events`、来源、`database_mutated:false` 和 `business_plans_mutated:false`；没有任何 `save` 或 `confirm` 实库动作。

## 性能与测试边界

新页面**共用单一 R25 高精度 `useSimClock`，只挂载仓库或运输一个 3D 场景**。投射到仓库三辆叉车的动作仍是展示映射；真实仓储作业总数从 CP-SAT 返回，完整业务事件表不因叉车展示数量限制丢事件。该版本尚未接入真实库位、叉车定位和传感器、OSRM 路径几何、生产订单生命周期变更。

后端 `pytest -q tests/test_r27_workflow.py tests/test_r26_single_warehouse.py tests/test_pg_r24.py tests/test_pg_routing_preview.py tests/test_pg_simulation_archive.py tests/test_pg_r25_replay.py tests/test_contracts.py`；前端 `node scripts/test-r27-flow.cjs`、`npm run build`。由于本开发运行环境无法下载 OR-Tools 与完整 npm 依赖，**实际联合求解及完整 React 构建必须在你的 Windows 本机验证**，不能提前宣称已完成系统级验收。
