# 20261024-1530 · PARTNER · R09 乙方侧集成：业务观测 + R08 组合根装配

- 角色 / 日期 / 基线提交：PARTNER（乙方）/ 2026-10-24 / 基线 `44e98f2`（PR #4 head），分支 `partner/r09-observations-integration-20261024`
- 对应任务 ID / 状态：R09 乙方可独立部分（"提供实际业务观测与工具接线"）→ **观测器已实现**；14 项指标本身属甲方，未实现
- 完成及修改文件：
  - 新增 `backend/app/application/plan_observations.py`（R09 业务观测，纯函数，无指标公式）
  - 新增 `backend/tests/test_r09_observations.py`（12 条）
  - `backend/app/bootstrap.py`：新增 `build_negotiator(snapshot, ...)`，把 R08 三角色按快照真实对象装配
  - `backend/app/application/contract_net.py`：`ExceptionRecoveryRole.disruption_at_s` 改为可空——未声明扰动时**不报价**，不再伪造零成本恢复窗
  - `DEV_LOG.md`、`FILE_MAP.md`（重建）
- 契约版本前后 / 变更提案：**0.2.0 不变**（未新增 DTO；`build_negotiator` 与观测器都是 application 内部能力）
- 输入输出、单位、状态、URL 变化：
  - 无新 endpoint；`observe_plan(plan, requested_order_ids, negotiation=None) -> PlanObservations` 为纯函数
  - 字段：订单覆盖（请求/已服务/未服务含 reason_code）、逐单 `handoff_wait_s`（发车 − ready_at）、仓库 makespan、
    总里程/总时长、`coldchain_evidence` 布尔、按 (location, unit) 的容量峰值（含半开区间）、按批次的暴露并集、
    换批次数与总时长、三段求解状态、协商状态/授标数/冲突数/digest
- 关键取舍（反"假观测"）：
  - 快照/计划**没有**冷链证据时 `coldchain_evidence=False`，peak/exposure 为空元组，**不填 0**；R09 因此能区分"未测量"和"测到 0"
  - 容量峰值按半开区间扫描：`[0,100)` 与 `[100,200)` 不叠加
  - 暴露按批次取并集：`[0,80)`+`[60,100)`+`[100,120)` = 120，不按 140 求和
  - 观测器**不算**指标（覆盖率、均值、对照差值仍留给 `backend/app/evaluation/`，属甲方）
- R08 与组合根的集成：
  - `build_negotiator(snapshot, policy=None, warehouse_resource_id=None, vehicle_id=None, disruption_at_s=None, recovery_s=0)`
  - 仓储角色绑定所选 `WarehouseResource` 日历；运输角色绑定所选 `Vehicle` 班次；
    未声明扰动时异常角色 `disruption_at_s=None` → 不报价（不抢占任务）；声明后才按恢复窗竞价
  - 资源/车辆不存在时显式 `ValueError('unknown_warehouse_resource:...')` / `('unknown_vehicle:...')`
- 验证命令、通过/失败原始结果（Windows，Python 3.12.10，`PYTHONUTF8=1`）：
  - `python -m pytest -q tests/test_r09_observations.py` → **12 passed**
  - `python -m pytest -q`（backend 全量）→ **340 passed**（基线 328 + 12）
  - `python scripts/check_project.py` → PASS（exit 0）
  - `python scripts/export_contracts.py --check` → `Contracts match source`
  - `python scripts/verify_delivery.py` → 12/12 exit 0
- 未完成/已知限制/阻塞（其中需甲方配合的见下）：
  - **14 项指标、覆盖率定义、对照实验与记录**：`backend/app/evaluation/`、`backend/tests/evaluation/` 属甲方，本轮未触碰
  - **独立冷链校验的域重建**：`domain/coldchain_capacity.py`、`domain/joint_validation.py`、`tests/coldchain/` 属甲方，未实现
  - **持久化**：`PlanningSnapshotStore` / `PlanCommitStore` 无实现类，未进 `Services`，观测器不落库
  - 观测器只读 `CandidatePlan`；`handoff_wait_s` 用 depot_start 的发车时刻，若某订单无对应路线则回退为 0（已在字段说明中标注）
  - `api/routes/agent_demo.py`、`postgres_demo.py` 仍直连 adapters（上一轮已钉住名单），未在 AI 工具调用链路上接线观测器
- 交给谁 / 对方下一步（交接清单）：
  1. 甲方可用 `observe_plan(plan, requested_order_ids, negotiation=...)` 作为 14 项指标的输入，不必自己重算覆盖/等待/峰值
  2. 需要 `exposure_limits` 对比（是否超限）时，用 `ExposureTotal.union_s` 对 `PlanningSnapshot.coldchain.exposure_limits`，
     不得把"没有段"当成 0 秒已测
  3. 持久化实现类就绪后，我把它们加入 `Services`；观测器可按需落库（需新增端口，属共享改动，先提案）
