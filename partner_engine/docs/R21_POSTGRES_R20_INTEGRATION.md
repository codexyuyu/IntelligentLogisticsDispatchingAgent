# R21 · PostgreSQL → R20 后端读数与正式运输求解器模拟预览

**交付范围**：已实现新增的数据库只读 API，以及把数据库真实字段映射为 R20 共享 `RoutingRequest` 后调用**原有** `OrToolsRoutingSolver.solve()` 的演示路径。只读，不向数据库写任何方案，不替代仓储协同/正式计划/真实道路优化。此版本没有修改 B 拥有的求解器。

## Windows 一次启动

1. 另解压本包，不覆盖 R20。打开新文件夹下 `backend`，在资源管理器地址栏输入 `powershell`。
2. 如本机新环境缺少依赖，先运行一次：`python -m pip install -r requirements.txt`（需联网；Python 建议使用原 R20 已成功运行的环境）。
3. 运行：`powershell -ExecutionPolicy Bypass -File .\start_pg_local.ps1`。输入 PostgreSQL 密码，保持窗口运行。该脚本仅绑定 `127.0.0.1`。
4. 浏览器打开 http://127.0.0.1:8000/local-pg/docs ，查看 **PostgreSQL demo (read-only)** 分组，分别尝试：
   - `GET /local-pg/pg-preview/summary`：实时数据库订单、车辆、节点及距离矩阵记录数。
   - `GET /local-pg/pg-preview/orders`：读取真实订单视图（保留原重量、温区、时间窗、卸货分钟）。
   - `GET /local-pg/pg-preview/vehicles`：读取真实车辆视图（原容量、温度、归属仓库）。
   - `POST /local-pg/pg-preview/route`：调用 **R20 真正的 OR-Tools 求解器**，生成不落库的模拟运输预览。

## 实际演示调用

先在 `/summary` 查看 `warehouses` 值，以下假设含 `WH001`。Swagger 中点击 POST /route → Try it out，发送：

```json
{
  "warehouse_code": "WH001",
  "temperature_zone": "chilled",
  "speed_kmh": 30,
  "budget_ms": 5000,
  "max_orders": 20,
  "acknowledge_simulation_only": true
}
```

此调用**只读数据库**，不调用任何 `INSERT`/`UPDATE`/`DELETE`。会返回实际解的车辆—订单—停靠顺序、起止秒和距离，以及原算法状态、独立规则校验结果，或明确的无解/不兼容错误。

## 为什么这是“运输预览”而不是正式联合调度

R20 的共享合同严格要求：体积、数量、批次、仓运 ready_at、车辆班次、实时时刻、道路时间、保鲜截止与版本。你目前 PG 有真实的订单/车辆/温度/时间窗及 **直线距离**，但缺上述生产来源。因此本功能需要明确输入 `acknowledge_simulation_only=true`，输出 `simulation_preview_not_executable` 和全部 `assumptions`，在模拟部分强制标注 `source_kind=simulation`。

- 订单分仓：按仓库到客户的**直线距离最近**归属，仅限本次预览；不是业务真实分仓。
- 行驶时长：用 `distance_m*3.6/speed_kmh` 向上取整估算秒数；不能称真实道路时长。距离也仅是直线。
- 体积：为保持 R20 强类型契约，明确假设 1 kg = 1 L；不能称真实体积、运力与成本。
- 仓储交接：模拟时所有订单已就绪；尚未对接冷库、库存和仓内 CP-SAT。
- 保鲜截止：暂以配送窗口末端+卸货时间模拟；不宣称真实保质期。
- 温区：输入 `chilled`/`frozen`；订单全负温为 frozen，非负温为 chilled，跨零边界需要人工策略并拒绝猜测。候选车辆须覆盖**所有本次选中订单的整个数值温度范围**；保守过滤可能遗漏可行的分车解。
- 班次：模拟车辆从所属仓库首次出发，班次长度按订单窗口增加演示缓冲，不是司机工作时间或实时车辆位置。
- R20 路由仅支持单仓单趟、单车固定温区。不同仓库/温区的预览**不能直接合并**成一份可执行调度方案。
- 数据库的重量/车辆容量为 `numeric`：当前按契约只接受正整数 kg；如果存在小数将明确拒绝，**绝不静默取整**。
- 最多取当前仓库/温区前 20 条订单，不会把省略的订单误报为已服务。`omitted_due_to_limit`、`selected_orders` 可核对。

**安全限制**：`PG_DEMO_ENABLED=1` 才开放新 API，且只允许本机请求；数据库连接以 `SET TRANSACTION ... READ ONLY` 执行。原来的两个历史计划保留，不触发正式 `confirm_plan`。示例为了兼容旧本机 PostgreSQL 用户使用 `postgres`，实际部署应设最小权限的专用只读账号；新路由未加入业务身份认证，不得对公网开放。

## 测试与未完成项

使用已有 R20 `backend/app/contracts/`、`backend/app/adapters/routing/ortools_solver.py`、`backend/app/domain/transport_rules.py`。测试：

```powershell
cd backend
python -m pytest -q tests/test_pg_routing_preview.py
python -m pytest -q tests/test_contracts.py
```

本交付环境无 PostgreSQL 访问权限，也无法下载 OR-Tools/psycopg，因此仅能完成假数据库字段/ORM 映射与求解器注入的自动化测试；**实际数据库+真实 OR-Tools 的端到端运行必须由 Windows 本机按上述操作验证**。真实运行中若温区、分仓或时间窗导致无解，请保留错误文字反馈，不要把无解误说成程序正常产出了可执行方案。

后续 AC 任务：接入真正的仓储资源、体积、车辆班次及道路时长来源；然后才可实施正式 PlanningSnapshotStore、联合协调、受事务保护的计划写入。无需先做大量规模实验。

### OpenAPI 治理

新增接口以**同一 FastAPI 进程中的隔离本机子应用**挂载到 `/local-pg/`，其 Swagger 在 `/local-pg/docs`；保留既有 `/api/v1` 共享 OpenAPI 与前端自动生成 TS **逐字不变**，无需在没有 npm 依赖的交付环境手改 `frontend/src/client/generated.ts`。正式业务 API 仍按原九项操作治理，待正式合同/数据齐全时才提出变更。
