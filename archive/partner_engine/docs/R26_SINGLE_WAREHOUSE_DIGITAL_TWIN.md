# R26 · 单仓库冷链数字孪生与仓储作业演示

## 设计约束

**本项目只允许一个有效配送中心。** R26 默认演示快照为 `wh_1`（PostgreSQL 业务编号 `WH001`），20 条订单、4 辆车、2 个仓内装卸资源、20 个库存批次全部指向同一仓库。冷藏、冷冻、收货等区域只是**同一座建筑内的功能分区**，不是独立仓库。

历史 `two_warehouses_20_orders.json` 及 R17–R25 证据文件保留供追溯，不再作为新界面自动导入的默认场景。真实 PostgreSQL 初始数据和原历史方案不会在启动时自动改动。

## 开发内容

1. `data/scenarios/single_warehouse_20_orders.json`、`frontend/public/scenarios/single_warehouse_20_orders.json`：从旧合成快照派生的单仓场景；原客户间矩阵不变，移除 `node_wh2` 行/列并统一业务归属。此场景仍为**合成演示数据**，不是 PostgreSQL 真实订单。
2. 新增菜单 **仓储管理 → 3D 单仓数字孪生**。驾驶舱也提供直达入口，可点击 3D 配送大屏中的仓库进入。
3. 8 个仓内功能区：收货、质检、冷藏、冷冻、分拣、暂存、装卸月台、叉车充电区；24 组 3 层 × 3 货位货架，托盘、货箱、冷藏冷冻色标、装车区。
4. 3 辆叉车各自执行取货、举升、转运、卸货、返回任务；插值依据仿真时间，支持停止、拖动、倍速和不同相机视角。箱体/托盘使用 InstancedMesh，动画直接读取 R25 高精度时钟以避免组件每帧重建 WebGL。
5. **完整演示**与**按 CP-SAT 时间映射**两种模式：前者全部是合成作业；后者只继承当前方案的作业时间，叉车分配、货架坐标、批次/订单关联仍是展示映射，绝不称为实测数据。不连接真实 RFID、WMS 库位、温度传感、AGV 控制或真实出库落账。
6. PostgreSQL 新增单仓只读预检 + 人工确认的事务型迁移工具（见下文）。R24 冷链扩展数据已安装的状态不影响它的使用。

## Windows 运行

建议保留 R25 目录作为可回退版本。在新目录解压 R26，关闭原 R25 后端以释放 8000 端口：

```powershell
# R26/backend 目录
powershell -ExecutionPolicy Bypass -File .\start_pg_r26_local.ps1

# 另开 PowerShell，进入 R26/frontend
npm ci
npm run build
npm run dev
```

浏览器打开 <http://127.0.0.1:5173>，进入 **3D 单仓数字孪生** → **完整演示** → **播放**，依次检查 3 辆叉车、货架点击详情、装卸月台、剖切/垂直俯视、进度条。也可从 **数字孪生驾驶舱** 右上方的大型入口进入。若需要按真实 CP-SAT 时间展示，先在 **联合调度** 生成方案，再回到该页选 **按 CP-SAT 时间映射**。

## PostgreSQL WH002 -> WH001：独立显式迁移，不自动执行

R26 的新默认演示快照是单仓；**你的 PostgreSQL 实库原先有 `WH001/WH002`，启动新版本不会自行把数据库变成单仓**。新 PostgreSQL 调度台会显示 `R26 单仓业务检查` 状态，确保这一差别不会隐藏。

先用 pgAdmin 或 PostgreSQL 提供的 `pg_dump` 完整备份，并用 `pg_restore -l` 验证文件可读取。需要数据库密码；后端必须停机以避免新写入竞争。示例：

```powershell
# 用 PostgreSQL 安装目录中的 pg_dump.exe，若已添加 PATH 可直接使用
pg_dump -h 127.0.0.1 -U postgres -d coldchain_db -F c -f .\r26_before_single.backup
pg_restore -l .\r26_before_single.backup

# R26/backend 目录；只读预检
powershell -ExecutionPolicy Bypass -File .\check_single_warehouse_r26.ps1
```

请认真查看预检 JSON：`can_apply=true` 才允许执行受保护的合并。预检会查找所有指向 `warehouses` 的外键，尤其历史 `routes.start_warehouse_id` 和 R24 冷链扩展表。**如果 WH002 已有历史路线、库存批次、冷库资源、装车作业或其他业务引用，工具拒绝迁移**；这是防止丢数据的安全措施，必须评估迁移映射，不得强行删除或跳过检查。

确认备份后，如果预检允许且你确实希望更改实库：

```powershell
# R26/backend 目录；需两项显式开关，并输入 WH001 二次确认
powershell -ExecutionPolicy Bypass -File .\check_single_warehouse_r26.ps1 -Apply -BackupVerified
```

执行内容（**会修改实库**）：事务中先记录 WH002 信息及原车辆仓库归属到 `pg_r26_single_warehouse_audit`，把 WH002 名下车辆统一归属 WH001，然后删除无其他业务引用的 WH002 主记录。这样 `v_dispatch_nodes` 从 22→21，直线矩阵由 484→441 条，`v_dispatch_vehicles` 则应显示 4 辆车均归属 WH001。**不能通过这个脚本自动把仓储库存、历史规划或订单业务事实改写成另一个仓库**，它遇到关联记录必须停止等待人工确认。

事务失败将回滚；需要反向恢复则使用迁移前的完整 `pg_dump` 备份，并核对 `pg_r26_single_warehouse_audit`，不建议直接覆盖正在运行的数据库。迁移过程中不变更 R22 独立模拟归档表的历史条目。

完成后重启后端，浏览器在 PostgreSQL 调度台点 **刷新实库数据**，看到 `R26 单仓业务检查：已统一` 即为数据库单仓检查通过。R24 订单体积等元数据若仍未录入，会继续提示资料不全，两种状态相互独立。

## 测试与限制

- `python -m pytest -q backend/tests/test_r26_single_warehouse.py backend/tests/test_pg_r24.py backend/tests/test_pg_routing_preview.py backend/tests/test_pg_simulation_archive.py backend/tests/test_pg_r25_replay.py backend/tests/test_contracts.py`
- `node frontend/scripts/test-r26-warehouse.cjs`
- `node frontend/scripts/test-r25-replay.cjs`
- `npm run build`（必须由有依赖的 Windows 环境执行；本次环境 npm 安装网络超时）

R26 不包含 OSRM 服务部署，不声称冷链车沿真实道路行驶，也不声称浏览器性能已在你电脑上验证。R25 原有城市回放、PostgreSQL 路线预览及历史实验保留。
