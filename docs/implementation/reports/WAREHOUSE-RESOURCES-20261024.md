# WAREHOUSE-RESOURCES-20261024 · 多资源同时占用与换批准备

## 结论

仓储 CP-SAT 现在能表达一个任务同时占用 **月台 + 人员 + 设备**，并为不同 `setup_class`
的相邻任务插入显式的换批准备区间（时长、费用），再交给独立仓储校验。  
本轮不签 Gate，不把该专项测试当作“仓储完整排程”或仓运联合的最终验收。

## 实现

### 1. 多资源同时占用

- 每个 `WarehouseTask.requirements` 单独做 exactly-one 资源选择；
- 同一任务的所有 requirement 共享同一个 `start/end`；
- `OperationAssignment` 每个 requirement 一条，同一 task 可有多条；
- 月台/人员：`AddNoOverlap`；
- 设备：`AddCumulative`，按 `Equipment.quantity_capacity` 和 requirement `units` 计算并发占用；
- eligible id 必须在快照对应资源集合内，否则显式 infeasible。

### 2. 清洁换批/准备时间

- `SetupPolicy.transitions` 绑定主资源（第一 requirement）的 `from_class → to_class`；
- 对可能落在同一主资源的任务对建立 `same` 布尔量和方向布尔量；
- 只有一侧存在 transition 时强制该方向；两侧都存在时由模型选择方向；
- 任务间至少留出 `duration_s`，回写 `SetupOperation(start=left.end, end=left.end+duration)`；
- `cost_cents` 进入目标函数（service + setup）；
- 独立 validator 只对策略中显式声明的 transition 要求 setup，避免在人员/设备上伪造换批。

### 3. 候选聚合

`ScheduleService` 不再为多资源 assignment 重复生成同 `task_id` 的 ScheduleTask；
按 task 聚合为一条任务，`assigned_resource_ids` 保留全部资源，起止取并集。

## 测试

新增/扩展真实 PostgreSQL + 真实 CP-SAT + 生产 Worker 的仓储作业用例：

| 用例 | 断言 |
| --- | --- |
| 多资源作业 | 2 个任务各生成 3 条 assignment（dock/worker/equipment），同一任务 3 条同起止；validation valid |
| 换批准备 | 第一任务 `[0,10)`，setup `[10,17)`，第二任务 `[17,32)`；setup cost 250；objective 450 |
| 不可行资源 | 请求中不在快照的资源返回 infeasible，不产生 assignment |
| 不可行时间窗 | infeasible、空 assignments、diagnostics 非空、validation=null |
| 结果哈希/篡改 | 结果文件 SHA256 与 job ref 一致；篡改后 422 `unverified_solver_result` |

结果：

```text
tests/integration/test_warehouse_job_pipeline.py：5 passed in 7.54s
全量：307 passed in 133.30s，exit 0
architecture：118 modules，0 violations
schema --check：exit 0
```

## 明确未完成

- 准备作业的 `support_allocations`（额外人员/设备）尚未进入 CP-SAT 占用模型；
- 初始 setup 状态、资源日历可用窗尚未进入求解模型；
- `storage_allocations` 仍为空；
- warehouse from-job 自动候选/提交尚未实现；
- 仓运交接时序与联合求解未开始；
- 本轮未改前端，未改动运行中的 Docker 产品栈。

因此本轮只完成“多资源同时占用 + 相邻换批准备时间/费用”的求解与校验主干，
不能称为完整仓储排程完成。
