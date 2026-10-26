# R28 · 单仓数据核对、业务闭环与 PostgreSQL 实库资料准备

## 本版修复的问题

R27 页面之前把**回放进度条当前时刻已发生的送达事件数**显示为“规划送达订单”。用户截图停在 `05:13:57 / 09:59:00`，当时显示 15 单并不能证明另外 5 单漏送。

R28 明确区分：

- **全程计划配送**：由后端对账计算，在任何进度条位置保持不变，统计已安排到 OR-Tools 路线的订单。
- **当前已回放配送**：截至当前时间轴的预测送达事件；拖到最后才能达到全程计划值。
- **求解未服务订单**：真正未安排到路线的订单；必须在同一求解范围内明确报告，不能通过 UI 进度推测。
- **订单级核对表**：每单仓储任务数、装车就绪、所属车辆、预计送达秒数和当前回放进度。

后端 `pg_r28_reconciliation.reconcile` 计算同一快照的范围、仓储排程、装车交接、车辆停靠、未服务、事件及发车时间，发现缺口/重复/先发车后装车/事件不符时直接拒绝。公式：`参与求解的订单 = 路线已规划订单 + 明确标记未服务订单`。回放事件数与计划订单逐项匹配。本版依旧是**只读规划预览，不代表实际签收**。

## Windows 启动（使用 R27 的冷链扩展表）

停止旧 R27 后端，解压 R28 到新文件夹。在 `backend` PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_pg_r28_local.ps1
```

在 `frontend` 的另一个 PowerShell：

```powershell
npm ci
npm run build
npm run dev
```

浏览器 `http://127.0.0.1:5173` → **智能调度 → R28 仓运业务闭环** → 单仓演示 → 运行预览。

验收：全程预计配送数量不随时间轴改变；运行到中途时“当前已回放配送”小于或等于全程数量；点击 **跳至回放结尾** 后两者相同；**R28 订单级业务对账**包含求解范围内每个订单及相应车辆。原 R26 3D 仓库、R25 四车回放保持兼容。

## PostgreSQL：先看缺口，再录事实，不能伪造数据

R28 新增：

```powershell
# R28/backend，另开一个 PowerShell；该脚本只读数据库，不再启动后端
powershell -ExecutionPolicy Bypass -File .\prepare_pg_r28_local.ps1

# 可选：将数据库已存在但缺 R24/R27 扩展详情的订单/车辆编号导出到新的空目录
powershell -ExecutionPolicy Bypass -File .\prepare_pg_r28_local.ps1 -OutputDirectory ..\r28_operator_templates
```

- 工具读取数据库，不执行 UPDATE/INSERT/DELETE、不会运行 R26 迁移。
- 报告 `warehouse.can_apply` 列出 `WH002` 的历史外键阻挡，绝不掩盖旧仓库数据。
- 输出 `orders.csv`、`vehicles.csv`、`handoffs.csv`、`work_operations.csv`，并输出仅含表头的 `zones.csv`、`lots.csv`、`resources.csv`。
- CSV **只填写来自数据库的订单或车辆编号**；业务工时、资源、体积、仓库归属、批次、时间、温区和库存事实均留空。导入器会拒绝未补齐的行。
- `work_operations.csv` 每个缺资料的订单仅一行**待填写提示**。实际业务可能需要多行 `pick`/`stage`/`load`，必须根据真实作业标准补齐 ID、资源、工时、先后关系。不要把空模板当成可用任务。
- `OutputDirectory` 必须是空目录。不会覆盖旧 CSV，避免误删已填的业务资料。

**重点：旧数据库目前由 WH001、WH002 组成，R28 不会偷偷改成单仓。** 只有做完备份并通过 R26 `check_single_warehouse_r26.ps1` 的安全预检，才能考虑显式迁移。只要存在历史路线、库存或其他依赖，就拒绝一键删除 `WH002`；这不是故障而是数据安全边界。若需要保留历史引用，后续必须设计经人工审查的逻辑退役/历史表归档迁移，不能用强行删表解决。

R28 **不创建真实业务字段，也不自动补录**。R24 和 R27 现有两种 `INSERT ONLY` 导入器可使用 CSV 经业务人员补齐的值进行事务式录入，失败即回滚。

## API（独立本机接口，不修改 /api/v1 公共契约）

- `GET /local-pg/pg-preview/r28/diagnostics`：单仓外键预检、R24/R27 各项缺口及真实编号，只读。需要本机后端与 PostgreSQL。
- `POST /local-pg/pg-preview/r27/workflow`：为兼容原 R27 页面保持旧路由，**R28 返回增加 `reconciliation`**（逐单计划明细及全程计数）；同时保留原 `events`、`snapshot`、`plan`、`database_mutated:false`。
- `GET /local-pg/pg-preview/r27/readiness`：仍保留旧检查接口。

没有配置 OSRM 时仍用示意道路。实库求解仅在 PostgreSQL 资料完备、单仓检查通过时才允许尝试；即使“齐全”，还需算法与完整业务规则再校验，并不保证一定可行。

## 现阶段不做的事

不强制删除 `WH002`、不自动改写业务订单/车辆归属、不自动扣减批次库存、不假造库存和叉车遥测、不生成客户签收证明、不自动发车、不重新进行耗时的算法规模实验。仍是可信的演示与只读计划预览，不是生产 WMS/TMS。

## 测试

`backend` 下：

```powershell
python -m pytest -q tests/test_r28_reconciliation.py tests/test_r27_workflow.py tests/test_r26_single_warehouse.py tests/test_pg_r24.py tests/test_pg_routing_preview.py tests/test_pg_simulation_archive.py tests/test_pg_r25_replay.py tests/test_contracts.py
```

`frontend` 下：

```powershell
node scripts/test-r27-flow.cjs
node scripts/test-r28-reconciliation.cjs
npm run build
```

Linux 开发环境可能没有 OR-Tools、SimPy、PostgreSQL/Node 包，需要 Windows 实机回归。不可将纯单元测试当成完整实库闭环的验收。
