# AI Agent 与候选调度、异常处置联动（2026-10-31）

## 本轮范围

保留队友的仓库三维建模，以及原有 OR-Tools/CP-SAT 联合调度、车辆重规划、人工审批和数字孪生。
本轮**不增加**真实车辆控制权或自动审批权。AI 的模型调用状态真实可见。

### 1. 调度指令

- 原 `POST /agents/dispatch-tasks`：配置有效的 DeepSeek key 时调用函数 `parse_dispatch_intent`；未配置时走受限规则解析。页面明确展示 `deepseek_tool_call` 或 `rule_based`。
- 候选 `ready` 后（真实 worker 求解校验完成）自动通过新增接口加载或生成 AI 解释；在候选卡片内展示 DeepSeek 回答、已核对的工具与数据来源、模型状态和追问入口。
- AI 只能解释已校验的求解结果与原约束。当前不支持的“指定车辆送指定订单／新地址／任意自定义优先级”依旧会被拒绝，不可冒称求解器执行了这些约束。

### 2. 异常处置

- 在已有模拟延误 `incident` 登记后，根据服务器持久化的 `impact`、`comparison`、`local_solver` 等证据自动生成一次 AI 解读；显示模型状态和服务端业务规则判断。
- 方案是否可行、是否较简单顺延改善由后端证据和确定性规则决定，**不是 DeepSeek 随意判定**。如果没有客观收益，展示“不建议因优化收益而批准”；遇到约束失败或缺失对照同样如实提示。
- 支持针对当前异常追问；每次回答的证据仍绑定当前 `run_id` + `incident_id`。模型不会创建新的异常、不会批准或拒绝候选。

### 3. 统一审计

新建 `agent_decision_analyses` 表，独立存放任务/异常对象、scope、actor、真实运行 ID、问题、证据、服务端工具读取记录、模型名、成功或失败状态和真实回答。通过 GET 接口恢复最近一次分析，刷新页面不必再次调用模型。

- `GET/POST /api/v1/agents/dispatch-tasks/{task_id}/ai-analysis`
- `GET/POST /api/v1/agents/runs/{run_id}/incidents/{incident_id}/ai-analysis`
- POST body: `{ "question": "" }` 进行初次解读；非空问题用于继续追问。
- 只读证据查询由**后端服务端**执行，记录为“后端核对的业务工具”，不谎称 DeepSeek 自主调用了它们。DeepSeek 解析指令使用实际 function-call；求解结果解读使用真实模型 completion。
- 模型未配置／调用失败则数据库分别记录 `model_unavailable`／`model_failed`，回答字符串为空，页面不会伪造 AI 文本。不会把供应商异常细节或密钥写入审计表。

### 4. 数据与执行边界

- 需要 Alembic 迁移 `0013_agent_dispatch_tasks` 与新增 `0014_agent_decision_analyses`；请只在**获得用户明确授权**的隔离数据库迁移。
- 不连接 5433/5434、不修改库存与真实派车、不推送 Git、不操作任何模型真实 API（当前环境未配有效 Key）。
- 正常使用要求后端启动时 `DEEPSEEK_API_KEY` 为真实非占位密钥。修改 env 后需要重启服务。API Key 不能放在前端或提交到 Git。
- AI 提供文字解释，金额、距离、订单数量和时效量化以表格和后端证据为准。任何反事实收益必须重新求解，不允许模型主观估计。

### 5. 已做的轻量验证

- `npx --no-install tsc --noEmit --pretty false`：通过。
- Python `py_compile`：新增服务、API、迁移、Bootstrap：通过。
- `pytest -q tests/unit/test_decision_analysis.py`：4 passed，包含：建议规则、真实模型回复成功（mock）、缺 Key 不伪造、模型异常不泄露敏感异常。
- 未访问真实 DeepSeek/DB，**未运行数据库迁移、端到端联调、浏览器演示、全部测试**。不能据此声称实环境已验收。
