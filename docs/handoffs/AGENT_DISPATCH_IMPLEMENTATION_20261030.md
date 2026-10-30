# 调度 Agent 集中开发交接说明（基于 bec4c5b）

日期：2026-10-30。交付形式：保留完整 Stage A / Stage B 前后端项目的源码 ZIP（不含 `.git`），在此基础上新增调度 Agent 功能。未改变原有联合求解、仓储、模拟审批、运输路线算法；未执行数据库迁移，未连接 PostgreSQL 5433。

## 已实现范围

- `POST /api/v1/agents/dispatch`：接收 `run_id` 和自然语言，服务端绑定已校验的 checked 联合运行；调用已有 `AgentChatService.run_with_tools`，限定至多四轮、十二次工具请求。
- `GET /api/v1/agents/dispatch/{agent_run_id}`：在调用者的 scope 内重取已保存的回答及工具证据。
- 五个**只读工具**：`get_current_run`、`get_dispatch_metrics`、`get_warehouse_progress`、`get_vehicle_states`、`preview_vehicle_delay`。工具参数由服务端校验。模型不能自行改动 run_id，也不具备登记异常或批准的工具。
- `preview_vehicle_delay`：复用现有模拟轨迹与 `delay_impact` 校验，返回原地等待顺延方案的影响及可行性。不调用 `incident()`、`decide()` 或实际库存服务；不是动态重新寻路。
- 将一次 Agent 分析及所有已执行工具证据写入现有 `agent_runs`、`tool_calls` 表（无需迁移）；未取得有效工具证据、达到循环上限的回答不能标记为已验证结果。
- 前端调度助手复用现有页面，支持读取最近 checked run、运行工具、展示结果证据、刷新后读取上次记录，以及将延误预分析参数带入已有异常处置页面。登记仍需要人工二次确认，审批仍在原有页面。
- 保留原 `/agents/chat` 与 Stage A/B 已有 API，不重复开发业务页面。

## 接口示例

`POST /api/v1/agents/dispatch`

```json
{"schema_version":"2.0.0", "run_id":"替换为真实checked运行UUID", "message":"请读取本次运行的真实调度指标"}
```

成功返回 `agent_run_id`、`run_id`、`reply`、`model`、`trace_id`、`stopped_reason` 和工具执行证据 `tools`。只有 `stopped_reason=final_answer` 且存在成功的工具读取时才算具备证据；业务结论仍需人工判断。

## 集中验收记录（在当前离线容器）

**完成的验证：**

- `pytest -q tests/unit/test_dispatch_agent_orchestration.py tests/unit/test_agent_tool_loop.py tests/unit/test_new_api_services.py`：**24 passed**。
- Python `compileall`：本次修改的后端及其关联模块静态编译成功。
- 新测试覆盖：模型调用真实校验数据、运行绑定、非法参数阻止执行、无工具证据回答不被采信、只读延误预演、禁止模型自批。

**没有完成 / 不得写成已通过：**

- 当前环境 Python 3.13，而项目要求 Python 3.12；尚未在规定 Python 版本复验。
- 缺少 `ortools`，无法导入完整 `bootstrap`、执行需要求解器的测试以及生成完整 OpenAPI。原有 `test_vehicle_delay_tool.py` 在收集阶段报 `ModuleNotFoundError: ortools`，不能判作本次逻辑回归失败。
- `npm ci` 安装前端依赖超时；无法进行 TypeScript、Vite、Vitest 或浏览器端到端验收。
- 没有连接 PostgreSQL、没有实际执行 Alembic、没有执行真实 DeepSeek API 调用，也没有验证真实数据中的多轮工具调用与持久化恢复。

## 在授权隔离环境进行一次正式总验收

1. 使用 Python 3.12、项目锁定版本的 Node，以及经过确认的 PostgreSQL **隔离测试数据库**。不要使用现有 `docker-compose.yml` 的默认 `5433` 端口映射；该配置还会在后端启动时执行数据库迁移。任何目标数据库迁移都必须经过用户单独授权。
2. 按现有项目运行手册准备后端依赖、隔离数据库和环境变量 `DEEPSEEK_API_KEY`；先确认原 Stage A/B 能读取 checked run 并有模拟数据。
3. 在前端 `apps/frontend` 安装依赖，运行 `npm run build`、`npm test`。在仓库根运行相关 Python 自动化测试及完整回归。
4. 在同一已校验运行测试：查询真实指标→查询时间轴车辆/仓储→预分析在途车辆的 60 秒延误→转异常处置（检查参数预填）→人工登记→人工批准/拒绝→仿真回放。
5. 测试模型服务断开、非法 UUID、工具参数超限、未启动模拟、重复异常、跨 scope、刷新恢复和模型请求自批等拒绝路径；确认真实库存/实际排程未修改。

## 已知限制

- 当前 Agent 通过最长 60 秒同步 HTTP 请求工作。模型高延迟或多轮调用可触发超时；完整**持久化异步任务队列**没有在本次开发范围内实现。超时后可能不存在可恢复的最终 Agent 结果，应查询运行记录，不要自动重试带写操作（本次 Agent 本身不提供写工具）。
- 模型最终解释仍可能出现措辞误差，工具证据是事实依据；强制要求至少一次成功工具执行只是最低保护，不等于对每个自然语言结论进行了形式化验证。
- 只支持模拟车辆延误的只读预分析，没有引入真实地图、实时 GPS 或中途重新选路。
- 真实浏览器和隔离数据库尚未重新验收，不能把历史 Stage A/B 验收作为本次 Agent 新功能通过的证据。
- 原工程的 OpenAPI 代码生成问题、其他历史缺陷和 GitHub CI 状态未在本次范围内修复。

## Git 状态

上传压缩包不包含 `.git` 历史，因此本交付不是 `bec4c5b` 之后的 Git 提交。不要把这个 ZIP 的存在当成分支已 push / merge；请在保留原仓库历史的工作副本里审查并提交本次增量。
