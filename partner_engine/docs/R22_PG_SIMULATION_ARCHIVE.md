# R22 · 已验证模拟路线的独立归档、查询与示意地图

**版本定位**：R21 经用户 Windows 本机实测，`POST /local-pg/pg-preview/route` 返回 HTTP 200、`solver_raw_status=ROUTING_SOLUTION`、`independent_validation=passed`，预览结果 `unserved_orders=[]`。这**只证明该次明示假设下的运输模拟求解可行**，不是冷链现场的可执行联合调度。R22 不修改 B 的正式 RoutingSolver，也不改原有 `dispatch_plans/routes/route_stops` 表。

## 本轮真正新增的功能

- `POST /local-pg/pg-preview/saved`：**重新**从 PG 取实时订单/车辆/距离矩阵，调用原 R20 `OrToolsRoutingSolver` + 独立运输校验；**只有有解、无未服务订单、完整订单覆盖、校验通过、演示假设齐全**才写入独立演示表 `public.pg_simulation_previews`。请求体不接受用户传入的任意路线或求解结果。
- `GET /local-pg/pg-preview/saved`：最新模拟方案列表。
- `GET /local-pg/pg-preview/saved/{preview_code}`：根据编号查询保留了求解结果和演示假设的 JSON。
- `GET /local-pg/pg-preview/saved/{preview_code}/geojson`：从原 PostGIS 节点坐标输出**直线连线示意**，不是道路路由。
- `GET /local-pg/pg-preview/saved/{preview_code}/map`：只读 Leaflet/OSM 地图页面，需浏览器能访问 OSM/Leaflet CDN。

## Windows 最简验收（不做规模实验）

**不要覆盖原 R21 文件夹。** 完整解压本 ZIP 到新目录，进入其中 `backend` 文件夹，打开 PowerShell。确保 PostgreSQL 本机服务正在运行。

第一次只需：

```powershell
# 当前系统如已安装 R21 依赖可跳过
python -m pip install -r requirements.txt
# 显式建立一张 R22 独立演示表；既有业务表不会修改
powershell -ExecutionPolicy Bypass -File .\start_pg_r22_local.ps1 -CreateDemoTable
```

以后启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_pg_r22_local.ps1
```

启动后在浏览器打开 <http://127.0.0.1:8000/local-pg/docs>。先找到 `POST /pg-preview/saved` → `Try it out`，填写：

```json
{
  "warehouse_code": "WH001",
  "temperature_zone": "chilled",
  "speed_kmh": 30,
  "budget_ms": 5000,
  "max_orders": 20,
  "acknowledge_simulation_only": true,
  "acknowledge_store_simulation_only": true
}
```

点击 Execute。如方案满足条件，HTTP 200 应含 `preview_code`（形如 `SIMR22_...`）、`storage=public.pg_simulation_previews`、`business_plans_mutated=false`。**本次会写入一条独立演示记录**（与 R21 只读版不同），而不是正式 `dispatch_plans`。若返回 422，说明该组数据无可完整验证的解，不应强行写入；若返回 503，检查依赖、是否先运行 `-CreateDemoTable`、数据库权限。

再测试 `GET /pg-preview/saved`，确认出现编号。用 `GET /pg-preview/saved/{preview_code}` 查询详情；将编号替换进下面地址浏览示意地图：

```
http://127.0.0.1:8000/local-pg/pg-preview/saved/SIMR22_你的实际编号/map
```

**注意上方 `/map` 地址的 `SIMR22_...` 整个部分用实际返回编号替换，不要重复拼前缀。**

不需要重跑 R17~R20 性能实验，只验证一次保存、查询和地图即可。

## 强制安全边界

- 老业务表 `dispatch_plans`、`routes`、`route_stops`，原有两份历史方案，**绝不触碰**。
- 新表和业务规划表**无外键或状态机联动**；不能用于执行、确认、调度生效或声称真实道路 ETA。
- 仍然假设体积、保鲜期限、仓储 ready_at、班次、最近仓分配和速度；数值来自现有 PG，缺字段并未被神奇补齐。
- 首次建表需要明确命令；旧 `start_pg_local.ps1` 不启用保存操作；新启动脚本设置 `PG_PREVIEW_WRITE_ENABLED=1`，只监听 `127.0.0.1`。此本机演示接口**没有用户登录授权**，不能公开到网络。
- 自动保存接口采用数据库事务，一次写入；错误回滚。获取详情和列表仍使用 READ ONLY 事务，检索编号使用绑定参数。
- 部署生产使用独立、受限数据库角色，不能使用超级用户；当前演示脚本沿用历史本机 `postgres` 以方便验收。

## 测试口径

定向测试：`python -m pytest -q tests/test_pg_simulation_archive.py tests/test_pg_routing_preview.py tests/test_contracts.py`。本交付隔离环境无法连接用户 Windows PostgreSQL，且未安装 OR-Tools/psycopg；因此运行通过的是依赖隔离的 API/存储/约束测试，**不能视作 R22 真库写入已实测**。Windows 只需一个样例验证闭环。

后续 R23 才考虑正式业务 `PlanningSnapshot`、真实交通时长、仓储资源及事务 `PlanCommit`。R22 演示归档不会自动升级为正式调度方案。
