# 后端统一实现与兼容边界

本说明对应 `apps/backend` 与 `packages` 当前实现。不是 Gate 签收记录，不更新历史验收状态。

## 运行入口

根 `docker-compose.yml` 的 backend 与 worker 使用同一镜像和 `bootstrap.compose()`。
`pyproject.toml` 的运行工作区为 `packages/*` 和 `apps/backend`。
根 `backend/` 是历史设计说明；`merged/` 不在工作区或镜像中；`archive/partner_engine/`、
`demo/`、`demos/` 不参与正式运行。不要向这些历史目录同步正式实现。

## 统一执行链

`API → application/submission.py → JobService → JobRepository → Worker → handler → ResultArtifactStore`。

- 运输、仓储、联合求解和仿真复用同一持久任务基础设施。
- 幂等身份由 scope、actor、操作类型、调用方 key 和稳定业务输入组成，不含服务器生成的 UUID 或截止时间。
- 同一幂等键串行准备输入；重试返回首次回执，不重新捕获快照。输入、任务、回执在同一事务中写入。
- 原始低层 `POST /jobs` 仍支持显式 RequestRef；其幂等摘要继续包含调用者提供的完整命令。
- 已有旧提交记录不会重写。升级前后内部操作命名不同；部署时排空旧请求重试，历史任务仍可查询。
- 预算由 `application/budgets.py` 统一限制；普通求解上限 5 秒，联合求解上限 12 秒，均不超过任务截止时间。
- 结果查询按持久任务中的 kind/mode 分派，不靠捕获解析异常猜测类型。

联合接口保持 `POST /api/v1/integration/runs` 默认等待并返回原业务结果；计算在独立 Worker 中执行。
`?wait=false` 立即返回包含 `job_id` 和 `run_id` 的回执。客户端可查询通用 job 接口或 integration run。
兼容等待最多 56 秒，该端点的 HTTP 外层限制为 60 秒；其他 API 仍使用原 10 秒限制。
没有 Worker 时不会退回 HTTP 内联求解；任务保留在队列中，可使用同一 key 重试查询。

集成运行保留原来的 scope 级 key 语义，并将运行记录与任务提交放在同一事务内。
完成结果首次通过集成查询读取时缓存进运行记录；后续撤销更新的是该业务记录，原始任务结果保留不变。
旧的完成记录没有 job_id，仍按原格式读取和撤销。

## 候选计划

`application/candidates.py` 是共同组装器：

- 同时投影运输、仓储任务，运输任务聚合所有相关站点的起止时间。
- 纯运输候选的空仓储成本为零，避免将运输成本累计两次。
- 明确实际创建人、资源集合、任务排序、成本及候选内容哈希。
- 拒绝未知路线与仓储/运输任务 ID 冲突。
- 独立校验器仍保留；组装成功不代表方案有效，更不代表已提交版本。

## 协商角色

唯一协调协议是 `contract_net.py`。`negotiation_roles.py` 将当前领域证据转换为报价；
`windows.py` 维护共享的容量日历选窗、报价登记和确认规则。
`contract_net_roles.py` 仅保留旧构造函数的事实适配，异常角色委托当前实现；不再无条件确认报价。
旧接口缺少完整领域证据，不应替代 `negotiation_link.py` 的方案校验入口。

## 指标口径 1.1.0

`values.py` 统一指标构造、比例、版本和可比性检查；`complete.py` 处理有观察窗口和订单证据的 14 项指标，
`metrics.py` 保留旧聚合输入的适配接口，`paired.py` 复用同一可比性规则。

- 旧运输接口的“总订单减未分配订单”命名为 `planned_assignment_rate`。
- 没有完成时间/观察窗口的运输输入，`delivery_rate` 返回 null、`missing_data`，不再伪装成配送完成率。
- 比较必须具有相同指标集合、单位、来源和定义版本；完整报告还必须有相同 scope 和观察窗口。
- 历史指标 1.0.0 不自动改版；与新 1.1.0 混合比较会被拒绝，需从原始证据重新计算。
- 负数、重复订单和超出总数的完成数量会被拒绝，API 映射为输入错误。

## 验证范围

相关回归位于 `tests/unit/test_backend_consolidation.py`、`tests/integration/test_submission_consolidation.py`、
`tests/integration/test_joint_job_api.py`，并复用原角色、指标、冷链、仓储和集成用例。
数据库检查使用独立 `TEST_DATABASE_URL`；任务输入历史保持只增不改。没有运行全阶段 Gate，
没有生成签名、签收记录或修改前端。
