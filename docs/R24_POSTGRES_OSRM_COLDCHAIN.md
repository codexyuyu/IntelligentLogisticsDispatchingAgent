# R24 — PostgreSQL 冷链业务字段、OSRM 道路路由、仓运交接适配

## 交付内容

- 保留 R23 全部已在用户 Windows 机运行成功的 PostgreSQL 读数、模拟预览、独立校验、R22 单表归档、React/Leaflet 地图。
- `backend/app/adapters/matrix/osrm.py`：可选 OSRM `table/v1/driving` 距离/时长矩阵，与 `route/v1/driving` 实际路网线型。矩阵用于 **原 R20 `OrToolsRoutingSolver`** 的运距与时间窗约束；路线几何用于 R22 存档地图。**是 OSRM 驾驶配置估计，不是实时拥堵、道路管制、冷链运输保障，也不自动计算温控能耗。** 网络错误、不可达、坐标缺失则报错，绝不静默回退到直线模式。
- `backend/migrations/R24_pg_coldchain_additive.sql`：在现有 7 张业务表之外增量添加 6 张 R24 扩展表（仓库温区、库存批次、订单详情、车辆详情、仓储资源、装车作业）。旧 `dispatch_plans / routes / route_stops` 等 7 张表**不删除、不 ALTER、不写入**。无自动填值，不会把演示体积变成事实。
- `verified_r24`：只有 R24 表已建、对应订单/车辆/批次/装车作业字段齐备且满足校验时，才采用真实录入的体积、批次、件数、所属仓库、保鲜截止、车次班次/剩余容量、装车 `ready_at`。同时检查批次容量、资源时窗等必要条件。路径求解仍是单仓单温区、单趟；**不等于已把 B-01 CP-SAT 仓储排程/复杂冷间占用写入数据库，也不产生可执行生产方案**。
- 新增 `GET /local-pg/pg-preview/readiness`，React 页可查看扩展数据有无与缺漏计数。新增 `travel_mode` 和 `business_mode`，默认沿用 R23 行为，旧 R22 已存档资料仍可查询。
- `backend/tools/r24_import_csv.py`：六种 CSV 字段模板，默认仅校验，有且仅有明确 `--apply` 才在事务里新增扩展表记录。重复编码触发错误回滚；原业务表不写入。

## Windows 最少启动步骤

1. **先备份 `coldchain_db`**（pgAdmin 4 → 右键数据库 → Backup），保留 R23 文件夹作为回退，不要覆盖。
2. 解压 R24 ZIP 到新文件夹；先关闭 R23 后端。进入新工程 `backend` 目录打开 PowerShell。
3. 缺依赖时运行 `python -m pip install -r requirements.txt`。首次、**你明确愿意新增六张空表**后运行：

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\start_pg_r24_local.ps1 -CreateR24Tables
   ```

   此命令只有首次需要 `-CreateR24Tables`。数据库密码仅在本机提示输入，旧模拟表及旧业务表不修改。以后启动：

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\start_pg_r24_local.ps1
   ```

4. OSRM 模式是可选的：先自行启动或配置可访问的 OSRM driving 服务（含与你的数据覆盖区域相匹配的 OSM 道路数据），再启动后端：

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\start_pg_r24_local.ps1 -OsrmBaseUrl 'http://127.0.0.1:5000'
   ```

   **不要求用户先安装 OSRM 才能运行旧 R23 功能**。服务不可用时在网页选“PostGIS 直线模拟”即可；选 OSRM 会得到可诊断错误，不能假装已取得道路路由。请不要将真实敏感坐标交给未经审查的第三方 OSRM 服务。OSRM 输出不含实时拥堵。
5. 在 R24 `frontend` 文件夹另开 PowerShell，第一次 `npm ci`，然后 `npm run build` 和 `npm run dev`，打开 `http://127.0.0.1:5173` → PostgreSQL 调度台。

## R24 业务字段补录（数据不能由代码编造）

`docs/r24_csv_templates/` 含六张**只有表头**的 CSV（推荐 Excel 按 UTF-8 CSV 保存）：

- `zones.csv`：仓库温区及容量；
- `lots.csv`：真实库存批次、保质期、件数、仓库、温区；
- `orders.csv`：业务订单所属仓库、批次、件数、体积、保鲜截止、温区；
- `vehicles.csv`：车辆体积容量、剩余载重/体积、班次、可用时刻、当前节点；
- `resources.csv`：冷间/月台/预冷资源、温区、容量、可用时段；
- `handoffs.csv`：订单装车任务的月台、作业状态、ready_at、允许装车截止。

编号必须已存在于基础表（仓库代码如 `WH001`、订单号如 `ORD001`、车辆编号如 `V001`），批次代码必须对应 `lots.csv`，作业资源代码对应 `resources.csv`，作业仓库与订单归属一致。时间必须 ISO 8601 且带时区偏移，例如 `2026-10-18T08:00:00+08:00` **仅为格式示例，不是应该填写的业务值**。件数/容量为整数，填写真实来源与数据。`current_node_key` 用 `WH:WH001` 这类现有节点键；R24 的已验证模式目前只支持**未出车、起点在所属仓库**的车辆。每个订单仅一条装车作业与一个批次，不能表述复杂多批次场景。

在项目 `backend` 目录 PowerShell，以下命令先做干运行校验（不要将空模板直接导入）：

```powershell
python -m tools.r24_import_csv --zones ..\docs\r24_csv_templates\zones.csv --lots ..\docs\r24_csv_templates\lots.csv --orders ..\docs\r24_csv_templates\orders.csv --vehicles ..\docs\r24_csv_templates\vehicles.csv --resources ..\docs\r24_csv_templates\resources.csv --handoffs ..\docs\r24_csv_templates\handoffs.csv
```

确认所有内容真实且已备份数据库后，在后面加 `--apply` 执行一笔事务，任何主外键冲突或重复记录都会回滚。已有 R24 记录不是以覆盖方式更新；后续修订应单独审批和加版本。**当前并未替你编造或录入任何缺失业务值**，所以第一次打开界面显示 `资料尚未齐全` 是正常的；补齐后才可选择 `verified_r24`。

## 两个独立的模式

- **路线来源**：`straight_line_simulation`（默认旧行为）或 `osrm_road_estimate`（需可用 OSRM 服务）。
- **业务参数来源**：`legacy_simulation`（原演示假设）或 `verified_r24`（要求真实补录，缺任何必需字段即报错）。

两者可交叉组合。无论组合如何，输出都是 `simulation_preview_not_executable`，只归档到 `pg_simulation_previews`，**不提交到** `dispatch_plans/routes/route_stops`。R24 OSRM 模式保存的 GeoJSON 是 OSRM 道路线型；旧归档仍保留其原有直线 GeoJSON。

## 本轮最小验收

- 打开 React 页面，确认原 R23 订单、车辆、旧归档与地图仍正常。
- 点 `GET /local-pg/pg-preview/readiness` 应能反馈空表/缺数据；没有业务录入时不应强行开启 `verified_r24`。
- OSRM 服务可用时选择 OSRM 道路估计跑一次，确认矩阵和地图标注为 `OSRM_road_network_estimate`；失败就先核对 OSRM 服务及地图区域，不用重跑基准实验。
- 真实资料齐全后选择 `verified_r24` 跑一次，确认使用补录体积、批次、班次和装车窗口；缺资料应明确失败。

## 未完成与适用边界

- 未在用户本机 PostgreSQL/OSRM 上实测新分支（隔离环境无该服务、无 OR-Tools wheel）；历史 R23 本机实际验收与新增 R24 新功能的本机验收是两回事。
- 没有推断/自动生成任何订单体积、冷间容量、库存批次和班次；需要用户提供真实业务值（或单独标注的测试数据）。
- 未做生产级路网缓存、鉴权隔离、实时拥堵、库存占用竞争校验、完整 CP-SAT 仓储排程持久化、复杂多批次拼车、真正可执行计划提交。R24 的 `ready_at` 来源是**已录入的装车作业表**，不是自动求解所有仓储作业。
- OSRM driving profile 不一定含所有道路禁行规则或货车限制；使用前需确保实际车型与路线服务配置匹配。
