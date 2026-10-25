# 冷链协同调度 MVP（第一阶段）

本版本以 `demo1` 为基础，完成“批次/订单/冷间 + 车辆/路线 → Spring Boot → FastAPI → 调度结果”的第一阶段链路。

## 1. 数据库

新库初始化：

`db/scheduling-mvp.sql`

如果你已经执行过旧版调度 SQL，只新增运输资源和分配字段：

`db/upgrade-transport-scheduling.sql`

数据库为 MySQL 8，默认库 `smart_warehouse`。原有仓储表保留，不需要删除。

## 2. FastAPI

进入 `algorithm-service`：

`pip install -r requirements.txt`

`uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

健康检查：`http://localhost:8000/api/health`

当前代码会优先保持同一套输入输出结构；本地未安装 OR-Tools 时使用确定性启发式回退，安装 `ortools==9.15.6755` 后可继续替换为正式 CP-SAT/VRP 求解实现。

## 3. Spring Boot

默认访问 `http://localhost:8080`，FastAPI 地址可通过：

`ALGORITHM_BASE_URL=http://localhost:8000`

覆盖。

新增接口：

- GET `/api/schedules/batches`
- GET `/api/schedules/orders`
- GET `/api/schedules/cold-rooms`
- GET `/api/schedules/vehicles`
- GET `/api/schedules/routes`
- POST `/api/schedules/solve`
- GET `/api/schedules/{id}`
- POST `/api/schedules/{id}/confirm`

## 4. 前端

“协同调度 → 调度中心”会优先请求真实后端；后端不可用时回退原演示数据。

最新调度结果现在展示：

`批次 → 冷间 → 时间 → 订单 → 车辆 → 路线`

## 5. 下一阶段

1. 把 FastAPI 的确定性启发式替换为 OR-Tools CP-SAT + 基础 VRP/时间窗模型。
2. 将确认后的调度结果联动入库/出库/运输任务。
3. 增加冷间故障、订单变化、运输延误下的局部重调度。
4. 再接入 Agent 做自然语言查询、工具调用和方案解释。
