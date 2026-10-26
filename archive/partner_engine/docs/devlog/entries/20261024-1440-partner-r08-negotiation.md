# 20261024-1440 · PARTNER · R08 四角色合同网协商

- 角色 / 日期 / 基线提交：PARTNER（乙方）/ 2026-10-24 / 基线 `bebadc0`（R05 第二轮 head，= PR #2），分支 `partner/r08-negotiation-20261024`
- 对应任务 ID / 状态：R08 四角色协商 → **application 层已实现并有 25 条测试**；未接入 HTTP/前端，未与真实求解器联动做端到端演示
- 完成及修改文件：
  - 重写 `backend/app/application/contract_net.py`（371 B 脚手架 → 完整实现，约 560 行）
  - 新增 `backend/tests/negotiation/test_contract_net.py`（25 条）
  - `DEV_LOG.md`、`FILE_MAP.md`（重建）
- 契约版本前后 / 变更提案：**0.2.0 不变**。本轮未新增共享契约字段（协商报文属 application 内部结构，不跨层、不走 HTTP），`export_contracts.py --check` 仍通过
- 输入输出、单位、状态、URL 变化：
  - 无新 endpoint、无 DTO 变更
  - 协商状态取值：`confirmed` / `partial` / `infeasible` / `exhausted` / `expired` / `revoked` / `already_awarded`
  - 时间一律为调用方传入的模拟秒（`now_s`），模块内**不读系统时钟**，同输入同输出
- 实现要点：
  1. **四角色**：协调者（本模块）+ 仓储 `WarehouseWindowRole` + 运输 `TransportWindowRole` + 异常 `ExceptionRecoveryRole`。三个业务角色只拿 CFP 里的有界公开信息（任务窗、仓库、数量、互斥资源），只回一个报价，不交换库存明细或价格表。
  2. **报价校验**：CFP 轮次、任务、过期时刻、窗口落在任务窗内、非负成本；被拒报价仍写进 transcript 并标注原因码（`bid_expired`、`bid_outside_task_window`、`stale_round` 等）。
  3. **冲突处理**：按 `(cost, window_start, role_order, task_id)` 全序排名贪心选取；跨任务共享互斥资源且窗口重叠 → 记 `Conflict` 并通知落选方；同一任务的多个报价属正常竞争，不计冲突。
  4. **终止机制**：全部确认 → `confirmed`；达到 `max_rounds` → `exhausted`；超出 `deadline_s` → `expired`；本轮零报价或全部不可用 → `infeasible`（不再空转重复同一轮）。
  5. **确认与撤销**：中选角色必须 `confirm`，拒绝则发 `revoke` 并进入下一轮重谈；外部可 `revoke(task_id)` 释放已确认授标；同一 `task_id` 二次谈判返回 `already_awarded` 而不是重复授标。
  6. **结果追踪**：单调 `seq` 的 transcript（cfp/bid/conflict/award/confirm/revoke/close），`task_outcomes` 逐任务结论，`digest` 为 transcript 的 SHA-256；同一 idempotency key 重放返回**完全相同**的结果且不追加报文。
- 验证命令、通过/失败原始结果（Windows，Python 3.12.10，`PYTHONUTF8=1`）：
  - `python -m pytest -q tests/negotiation` → **25 passed**（0.14 s）
  - `python -m pytest -q`（backend 全量）→ **318 passed**（基线 293 + 新增 25）
  - `python scripts/export_contracts.py --check` → `Contracts match source`
  - `python scripts/build_file_map.py --check` → 通过
  - `python scripts/verify_delivery.py` → 11/12 exit 0，`architecture` exit 1（既有 7 条 `application→adapters`，本分支未新增）
- 未完成/已知限制/阻塞：
  - **未接 HTTP/前端**：R08 目前是 application 层能力，没有 `/api/v1` 端点；要上界面需共享契约新增报文 DTO 并升版本，属契约任务
  - **未与 CP-SAT/Routing 求解结果联动**：三个业务角色的报价来自资源日历/班次/恢复时长的解析式，不是调用求解器；"报价=真实可行解"的连接需在 coordinator 层接入（现有 `coordinator.py` 属甲方）
  - 多任务冲突只做**一轮贪心**，未实现跨轮竞价/退让（bid withdrawal）协议
  - `WarehouseWindowRole` 只处理单资源单工序的窗口，不考虑换批/预冷（R05 约束仅在 CP-SAT 侧）
  - 事务性/持久化：transcript 只在内存，未落库，未接 `PlanCommitStore`
  - `architecture` 既有 7 条告警未修（属组合根任务）
- 交给谁 / 对方下一步：
  - 甲方（DSH）：确认协商报文是否需要进入共享契约（若上 HTTP/前端，需我方先提契约提案）；`coordinator.py` 若要调用协商，请用 `ContractNet.negotiate(...)` 并注入角色实现
  - 乙方（自己）：下一轮若获授权，可将协商结果接入 `coordinator`/计划链路并补持久化
