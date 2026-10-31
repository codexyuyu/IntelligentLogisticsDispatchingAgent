# AI Agent 自然语言调度闭环 — 2026-10-31

## 基线和保留内容

基于 `coldchain_merged_teammate_warehouse3d_20261031.zip`，只新增自然语言调度模块与 `调度助手` 界面。队友的单仓三维建模、原有运输数字孪生、重调度、审批、驾驶舱、联合调度、对照实验等全部保留。未操作任何 PostgreSQL 数据库。

## 功能

- 输入正常业务指令，经 DeepSeek `parse_dispatch_intent` 工具调用提取结构化意图；未设置密钥时采用受限规则解析并在页面明确说明。LLM 不得生成实际车辆路径或写入业务状态。
- 仅允许两种真实业务路径：
  1. **现有 checked 场景重新联合求解**：提交 OR-Tools/CP-SAT 的真实 joint 作业，在得到 `checked` 与 `joint_validation.valid=true` 之后进入人工审批；批准后调用既有 `integration_simulation.start` 幂等生成模拟版本 v0，回放可读取。求解仍然使用**原场景既有订单、温控、车辆、时间窗和目标权重**，不是按自然语言私自改变优化目标。
  2. **已有模拟的途中车辆延误重规划**：从模拟轨迹选择真实车辆和合法途中时刻，使用现有 `project_delay` 计算只读候选、路线停靠与简单顺延对照。确认后通过原有 `incident` 和 `decide` 服务登记并批准，生效模拟版本 v1。
- 两者均从 `agent_dispatch_tasks` 读取历史任务、状态、解析方式、候选证据、批准记录。新表迁移是 `0013_agent_dispatch_tasks`。使用 optimistic `row_version` 防止同一任务被过期页面重复审批。新候选 run 用 task UUID 派生的固定幂等键。
- 仅允许 operator 角色创建、预览、审批；列表/查看按 scope 读取。
- 有模型时采用真实 DeepSeek tool-call 解析。模型或规则解析无法映射的请求会拒绝；不能虚构“指定车去新地址”“优先某个订单”的执行结果。
- 人工审批**只生效于模拟版本**，不是向真实车辆发指令；不修改实际库存、真实司机任务或运营排程。

## 交互

`调度助手 → 调度指令 → 解析任务 → 生成并校验候选 → 读取实际求解结果／候选重规划 → 人工批准或拒绝 → 仿真回放`。

历史任务可恢复。联合求解任务调用 Worker 异步执行，前端只在 `solving` 状态轮询。延误指令从当前模拟的真实车辆中填入 UUID 与可行进路段时间（不保证必有优化收益）。

## 本地部署（由使用者在**明确授权的隔离环境**中执行）

此版本**新增迁移**，需要先在被允许的 PostgreSQL 实例应用 migration 0013 后才可调用新任务接口。不要执行默认 Docker compose（原配置会占用本机 5433）。已知项目本地运行方式为前端 localhost:5199、后端 8100、隔离库 5434；本次未启动环境、未运行迁移，也未连接 5433/5434。

新接口：

- `POST /api/v1/agents/dispatch-tasks`：解析并登记草稿。
- `GET /api/v1/agents/dispatch-tasks`：历史任务。
- `GET /api/v1/agents/dispatch-tasks/{task_id}`：查询状态；对已提交的联合求解任务读取真实 Solver 作业结果。
- `POST /api/v1/agents/dispatch-tasks/{task_id}/preview`：生成候选；需 `{ "expected_row_version": n }`。
- `POST /api/v1/agents/dispatch-tasks/{task_id}/approve|reject`：人工决策；需同样的版本字段。

## 边界与注意

- 不支持任意地址派车、新订单导入、指定特定车辆必选、修改目标权重、跨车辆的实时重分配；这种输入应提示当前不支持，不会伪造方案。
- 不保证重新求解必然比原方案更好，也不保证延误重规划一定找到正收益；比较来自当前模拟实际路线、时间窗和里程成本。
- 任务记录审计是 PostgreSQL JSONB+版本字段；运行求解仍需现有后台 Worker 和结果 artifact 路径正常。
- 对同一模拟只有一个异常的既有业务限制保持不变；生成下一任务需新运行。
- 新增迁移、DeepSeek 和真实端到端批准流程**未验收**，按用户约定留待全部功能补齐后做一次统一验收。只进行了静态检查及必要的纯逻辑检查。
