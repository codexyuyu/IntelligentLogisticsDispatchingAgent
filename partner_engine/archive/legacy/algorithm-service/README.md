# FastAPI 调度服务

启动：`uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

健康检查：`GET /api/health`
正常调度：`POST /api/schedule/solve`
异常重调度：`POST /api/schedule/reschedule`

`requirements.txt` 已声明 OR-Tools。当前离线开发环境无法联网安装依赖时，服务会自动使用可解释的约束启发式回退；联网部署后安装 OR-Tools 即可切换到正式求解实现。

## CP-SAT V1.2 update
- Batch-to-order allocation quantity is now an integer CP-SAT decision variable.
- Expected inbound is a hard lower bound for planned inbound.
- latestDelivery is enforced only when quantity is actually allocated to the order in B-01.
- Same-room cleaning/switching buffer remains a hard non-overlap constraint.
- Results are independently validated before being marked executable.
- `requireFullOrderFulfillment=true` can be supplied to require every positive-demand order to be fully satisfied; default is `false` so the model can report partial fulfillment.
- `plannedOutbound` means cold-room release time in B-01; transport delivery timing is reserved for B-02/B-03.
