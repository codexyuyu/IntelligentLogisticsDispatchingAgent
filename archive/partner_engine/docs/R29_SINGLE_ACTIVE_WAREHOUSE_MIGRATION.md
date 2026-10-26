# R29：PostgreSQL 单现役仓库安全迁移与历史路线保留

## 目标与从实库确认的事实

用户实际执行 R28 的只读检查后确认：`WH001`、`WH002` 两座仓库记录；V001/V002 属于 WH001，V003/V004 属于 WH002；**4 条历史 `public.routes.start_warehouse_id` 引用 WH002**；R24 仓储扩展表对 WH002 的引用计数为 0；旧物理删除方案因外键阻挡 `can_apply=false`。

R29 的安全策略是**一个现役配送中心 + 一条历史仓库外键锚点**。统一 V003/V004 的所属仓库，保留原始 4 条 `routes`、其 `route_stops`、`dispatch_plans` 及 R22 模拟归档不变。不能把历史 WH002 路线偷偷改写为 WH001，也不能为了删除 WH002 抹掉真实外键历史。

- **新调度层面：** 唯一活跃仓库 WH001；4 辆车都归属 WH001；读取 `v_dispatch_nodes` 和 `v_dispatch_distance_matrix` 时，在后端内存中排除历史节点 `WH:WH002`，调度输入从 22 节点/484 对变为 **21 节点/441 对**。原始 PostgreSQL 视图依旧可以看到历史 WH002，这不属于物理单仓删除。
- **历史表层面：** WH002 仍作为历史 FK 参照保留。因此 `public.warehouses` 的记录数仍为 **2**；这不是“已经物理删除第二仓”。如后续要真正删除第二仓，必须先设计完整、可查询、经审核的历史归档并处理所有历史 FK；本阶段不冒险执行。
- **安全与追溯：** 新建 `public.pg_r29_retired_warehouses` 和 `public.pg_r29_active_warehouse_audit`，记录原仓库、两辆车迁移前的字段快照与四条历史路线快照；数据库行写入守卫阻止向退役仓库分配新车辆、新正式路线以及 R24/R27 扩展业务行（存在对应表时）。所有修改处于**单个数据库事务**；预检失败则拒绝执行，失败会回滚。
- **操作边界：** 仅适用于报告中确认的这份单仓演示数据库；预期历史路线数 = 4，车辆总数 = 4、V003/V004 归属 WH002、R24/R27 的 WH002 依赖为 0。若数据变化，先停止并重新审查，不应该为了强行通过而盲目修改预期数量。

## Windows 操作：由你执行，不需要手写 SQL

先将 R29 ZIP 解压到**新目录**，保留 R28 不动。建议在迁移期间**暂停旧后端、前端以及其他可能写数据库的业务进程**；不要同时运行两个 FastAPI 后端，以免 8000 端口冲突。

所有命令均在 R29 的 `backend` 目录执行。

### 1. 只读预检（必做，不写数据库）

```powershell
powershell -ExecutionPolicy Bypass -File .\migrate_pg_r29_local.ps1
```

正常输出：`can_apply_logical: true`，`historical_route_count: 4`，`vehicles_to_move: 2`。旧 R26 的 `can_apply` 仍为 `false` 是因为它尝试**物理删除** WH002；R29 采用新的逻辑退役方式，所以两个值不冲突。任何意外的非空外键依赖都将拒绝迁移。

### 2. 先备份并核查备份文件（必做）

```powershell
powershell -ExecutionPolicy Bypass -File .\backup_pg_r29_local.ps1
```

脚本调用 `pg_dump -Fc` 产生带时间戳的 `.dump` 文件，调用 `pg_restore --list` 检查文件目录可读取并输出 SHA256。**这不等于实际恢复演练**；有条件时在另一个数据库恢复核验。如果 PowerShell 找不到 `pg_dump`/`pg_restore`，把 PostgreSQL 的 `bin` 路径添加到当前 PowerShell `PATH`，或通过 pgAdmin 生成 Custom 格式备份并核验。禁止继续迁移直到存在可信备份。备份在本地保存，不要发送到聊天。

### 3. 显式执行单仓统一（这一步写数据库）

备份已经核对，且预检通过，才执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\migrate_pg_r29_local.ps1 -Apply -BackupVerified
```

按提示输入数据库密码和确认码 `WH001`。脚本再次在事务内部重新预检，若历史路线已不是 4 条、出现其他依赖、车辆数不符则直接拒绝。成功输出包含 `database_mutated=true`、`vehicles_moved=2`、`historical_routes_preserved=4`、`physical_warehouse_rows=2`、`active_warehouse_codes=["WH001"]`。执行成功之后**无需重复 `-Apply`**。

### 4. 再次只读核对

```powershell
powershell -ExecutionPolicy Bypass -File .\migrate_pg_r29_local.ps1
```

期望 `already_applied=true`、`state_valid=true`，车辆列表都为 WH001；4 条历史路线依然引用 WH002。

### 5. 启动 R29 并检查前端

在 backend 新窗口运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_pg_r29_local.ps1
```

在 frontend 新窗口运行：

```powershell
npm ci
npm run build
npm run dev
```

打开 <http://127.0.0.1:5173> → **PostgreSQL 实库调度** → **刷新实库数据**。预期：20 单、4 车、21 节点、441 条距离记录；全部车辆 WH001；提示 R29 单现役仓库已生效、WH002 保留为历史外键。订单和车辆仍受原温控/时间窗约束，原 R27/R28 3D 不变。

## 回退与未完成事项

- 如果 **尚未提交迁移**，PostgreSQL 事务会自行回滚，不会出现半迁移。若完成后需要撤回，从已验证的 `pg_dump` 在**隔离数据库**中先演练恢复，再制定数据恢复方案；不要直接覆盖现役 `coldchain_db`。审计表保存迁移前记录，不能替代完整备份。
- R29 仅解决**现役单仓统一**，不伪造订单体积、车辆容积、库存批次、装车时间、作业工时；R24/R27 的真实业务数据仍需独立补录。
- OSRM 仍是可选服务，未配置时使用清楚标注的直线模拟。R25–R28 的演示回放保持不变。
- 当前没有连接用户 Windows PostgreSQL 的权限；本次的结果是**代码和离线测试通过**，不是远程执行迁移成功。迁移必须在用户本机显式进行。

## 开发侧测试

```powershell
cd backend
python -m pytest -q tests/test_r29_active_warehouse.py tests/test_r28_reconciliation.py tests/test_r27_workflow.py tests/test_r26_single_warehouse.py tests/test_pg_r24.py tests/test_pg_routing_preview.py tests/test_pg_simulation_archive.py tests/test_pg_r25_replay.py tests/test_contracts.py
cd ..\frontend
node scripts/test-r29-active.cjs
```
