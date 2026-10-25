# 共享契约入口

先读根目录 DEV_LOG.md；当前版本见 VERSION。唯一手写类型在 backend/app/contracts；本目录 schemas.json、openapi.json、VERSION 都是生成物。

## B 的交付接口

| 接口 | 方法 | 输入 → 输出 | 实现文件 |
| --- | --- | --- | --- |
| RoutingSolver | solve | RoutingRequest → RoutingResult | backend/app/adapters/routing/ortools_solver.py |
| TravelMatrixProvider | get_matrix | matrix_id + expected_version → TravelMatrix | backend/app/adapters/matrix/fixed.py |
| Simulator | simulate | SimulationRequest → SimulationResult | backend/app/adapters/simulation/simpy_simulator.py |

AC 实现 WarehouseScheduler、PlanningSnapshotStore、PlanCommitStore、LanguageModelGateway。B 不直接访问 AC 的仓储/数据库/模型实现。前端只消费 HTTP OpenAPI，不调用 Python ports。

从 `examples/routing_request.json` 与 `examples/routing_result_not_implemented.json` 开始。后者表示功能未实现的契约形状，status=unsupported/has_solution=false，不能当算法测试的成功输出；真实 adapter 骨架直接抛 FeatureNotImplemented。

当前预留未来字段不等于已支持功能。未支持场景必须显式拒绝；修改必需字段/语义必须走 changes/ 提案及版本升级。HTTP 的九项业务 operation_id 从源码生成，不能手改 paths。

```powershell
python scripts/export_contracts.py
python scripts/export_contracts.py --check
```

再进入 frontend 运行 `npm run contracts:generate` / `npm run contracts:check`。CI 会检查两份派生产物未漂移。纯内部重构也需确保这些检查仍通过。
