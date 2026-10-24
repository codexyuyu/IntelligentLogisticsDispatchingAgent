# 仓储资源及准备契约增量

原因：现有 OperationAssignment 每条只带一种资源，校验器却禁止同任务多条；
WarehouseProblem 缺 SetupPolicy。无法表达申请书的多资源与清洁换批。

决定（限本任务）：
- OperationAssignment 表示 task/resource 占用；同任务可有多条，必须同起止时间，
  每种 requirement 单独满足精确 units。worker/dock 每个容量1，equipment 容量取实体数量。
  每任务 requirement 的 eligible_ids 不得交叉，避免同一资源同时抵扣多个需求。
- SetupPolicy(version, transitions, initial_states)；SetupTransition 指定资源、
  from/to、duration_s、cost_cents、额外人员/设备 ResourceRequirement。
  默认空策略只适用于同类任务；类变化必须给显式转换（零时长且零费用允许）。
  initial_states 未列资源表示初始可直接接受第一作业；需初始清洁时必须显式列出状态。
- SetupOperation 新增可选 support_allocations: ResourceAllocation(resource_id,units)[]；
  与主资源共享同一准备区间，独立占用其容量/日历。默认空数组兼容旧输入。
- 每主资源用 circuit 选真实相邻弧；不对非相邻任务叠加准备费用。带序列状态的主资源
  须为单容量资源；多容量设备池需先拆分具名设备，不能猜测每条并行通道的初始状态。
- 可用日历区间外容量为0；任务和准备都受日历约束。窗口按既有契约为服务开始闭区间，
  结束另受 scope horizon 限制；修正旧独立校验将 latest_s 错当完成上限的问题。
- DTO 增加可选 setup_policy，默认空策略；旧单资源/同类请求可继续使用。
  JSON schema_version 保持2.0.0，策略版本单独绑定输入hash；旧extra=forbid消费者
  不会接受新增字段，调用方必须按生成Schema更新。前端本轮不生成/修改。
- 候选 ScheduleTask 将同任务资源合并，WarehousePlan 保留各资源units与准备占用。
  自动 warehouse from-job / 提交资源预留的完善不属于此契约变更的完成声明。

受影响旧求解结果/校验证据必须重跑；不重算旧通过记录。生成源为Python DTO，
使用 scripts/export_contracts.py 生成两个根级JSON。新功能不能用旧 smoke 证明。
