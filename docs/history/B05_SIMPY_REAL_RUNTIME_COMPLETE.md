# B-05 SimPy 真实运行版

本版本把 `/api/v1/simulations` 从 scaffold 接通为可运行的 SimPy 离散事件仿真。

## 完成内容

- `SimPySimulator` 使用真实 `simpy.Environment` 推进仿真时间。
- 事件按 `(occurred_at_s, event_id)` 稳定排序。
- 仿真先生成基线 B-03 CandidatePlan，再按时间顺序把事件桥接给 B-04 `handle_event`。
- 仿真使用独立 `sim_<id>_<base_snapshot_id>` 快照 ID，避免直接覆盖生产快照。
- `GET /api/v1/simulations/{simulation_id}` 可读取最终 SimulationResult。
- `POST /api/v1/simulations` 返回 `simulation_id + job_id`；失败原因通过 job 查询。
- `departure_delayed` 支持事件发生在原计划出发时间之后，适合 SimPy 事中异常注入。

## 当前 B-05 V1 边界

第一版重点验证“车辆延误 → B-04 局部重排”闭环。其他事件类型仍由 B-04 自身能力边界控制。

## Windows

建议安装 `simpy==4.1.1`，与本阶段工程锁定版本一致。
