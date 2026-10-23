# 数据与接口契约

这些是拟实施契约，不是已实现 API。边界使用 Pydantic 严格类型、范围和额外字段检查，随后执行实体存在性与业务规则检查；类型正确不能证明事实正确。[Pydantic 严格模式](https://pydantic.dev/docs/validation/latest/concepts/strict_mode/)

## 共同约定

- 标识：业务对象用不可变 ID 与 `version`；不得按模型编造名称隐式创建车辆或仓库。
- 单位：输入允许带单位；归一化后重量 kg、体积 L、时长 s、距离 m、金额分，温度用 0.1 摄氏度整数。所有舍入、缩放和最大范围明确记录。
- 时间：接口为带时区 ISO 8601；业务默认 Asia/Shanghai，数据库 UTC；求解用相对快照起点的非负整数秒。区间按 `[start,end)`，时窗明确约束到达、服务开始还是服务完成。系统时钟与仿真时钟分离。
- 继承状态：快照前已开始的库存/作业保留原历史时间；求解把剩余占用映射为从 0 起的剩余区间，同时继承已消耗保鲜时间、货物位置和在执行状态。“昨日入库、今日重排”不得重置保鲜计时或漏计库容。
- 矩阵：显式存 node_ids 顺序、距离和时间单位、来源、版本、更新时间和适用车型；不可达边单独标记，不填 0。允许非对称矩阵。
- 数值：缺失值不是 0；拒绝 NaN、无穷、负容量、倒置时间窗。缩放检查 64 位整数溢出；时长保守向上取整，容量按统一保守策略缩放。
- 来源：字段记录 `source_kind`、`source_ref`、`observed_at` 和 `rule_version`，区分用户、业务库、公开数据、仿真以及明确默认值。
- 时窗分别定义 `hard_service_window` 与可选 `preferred_finish_at`；前者不可违规，后者只影响准时指标与软延误成本。必服务与允许暂缓由业务策略明确指定，不能由模型自行切换。

## 主要对象

| 对象 | 必需信息 | 关键校验 |
| --- | --- | --- |
| Order / Batch | 起终点候选、重量体积、品类、温区、服务窗、服务时长、保鲜截止、是否必服务 | 起终点有效，不能未经授权拆批或降低温控 |
| Warehouse / Resource | 节点、类型、容量单位、温区能力、实际温区日历、班次、故障/清洁区间 | 任意时点占用不超可用量；模式变化有耗时 |
| StockLot | 批次、所在仓、可用/隔离/预留数量、有效期 | 预留与实物分开；隔离库存不可分配 |
| Vehicle | 起止节点、当前位置、剩余载荷、重量/体积容量、单温区配置、班次 | 已装货不可瞬移；配送不跨无数据的温区 |
| Operation | 入库/预冷/分拣/出库、前序、所需资源、开始结束、准备类别 | 先后、时窗、切换和资源容量一致 |
| Event | event_id、类型、事件时间、接收时间、对象、严重程度、来源与版本 | 幂等、乱序检查、去重；回放事件隔离 |
| Snapshot | 对象版本集合、初始状态、路网/规则版本、仿真时刻 | 只读；所有子求解引用同一版本 |
| DispatchRequest | 快照、订单集合、硬/软约束、来源、预算、求解范围 | 缺关键数据则 needs_clarification；禁止悄悄放松 |
| CandidatePlan | 仓选择、路线、作业、存储区间、未服务单、原始求解状态、预算消耗 | 未校验之前不能执行或占用正式库存 |
| ValidationReport | 总状态、规则逐项结果、违规对象、证据、校验器版本 | 覆盖所有选定规则；未支持规则不能视为通过 |
| Plan | 候选、校验报告、快照、确认人/策略、预留记录、状态、计划哈希 | 确认必须绑定同一哈希和当前版本 |
| EvidenceBundle | 调用轨迹、规则来源、计算指标、计划引用、缺失事项 | 解释中的事实能回溯到具体字段 |

## 状态必须分开

作业状态：queued、running、succeeded、failed、cancelled。`succeeded` 仅表示计算结束且产出结果，不代表结果可执行。

计划状态：draft → validated → confirmed → executing → completed；旁支包括 rejected、stale、superseded。事件到来可使 validated 计划转 stale；重排创建新版本，不覆盖旧方案。

作业执行状态另有 pending、running、paused、interrupted、completed、cancelled；故障中断保留已完成量、事件时刻和剩余量。计划可有部分任务暂停，不能把暂停标成完成或改写已发生记录。

求解结果统一包含 `raw_status`、`engine`、`engine_version`、`has_solution`、`proof_scope`、`solve_ms`，对外概括为：

| 结果 | 语义 | 可执行性 |
| --- | --- | --- |
| optimal | 对已声明模型/范围有最优性证明 | 还要联合校验与确认 |
| feasible | 有可行候选但未证明最优 | 还要联合校验与确认 |
| infeasible_proven | 对当前范围证明无解 | 不能执行；可能还需扩大候选范围 |
| no_solution_within_budget | 超时或受限搜索未找到解 | 不得写“无解”或拿空计划报成功 |
| invalid_input / model_invalid | 数据或建模有错 | 修复问题，不让模型解释成正常业务冲突 |
| needs_clarification / unsupported | 缺关键条件或功能未支持 | 补充/缩小范围 |
| stale / conflict | 版本失效或资源争用 | 重新规划或重新确认 |

CP-SAT 的 UNKNOWN 与 INFEASIBLE 语义不同，Routing 也有独立状态体系。不能按数字值共用枚举。[CP-SAT 状态](https://developers.google.com/optimization/cp/cp_solver) · [Routing 状态](https://developers.google.com/optimization/routing/routing_options)

## 第一版接口清单

| 拟定接口 | 用途 | 返回及约束 |
| --- | --- | --- |
| POST /api/v1/scenarios/import | 导入结构化场景 | 校验报告；不信任文件中的操作指令 |
| POST /api/v1/requests/parse | 需求抽取 | 草案、来源和待确认项；不直接启动执行 |
| POST /api/v1/planning-jobs | 提交规划 | 202 + job_id；幂等键必需 |
| GET /api/v1/jobs/{id} | 查看计算状态 | 作业状态与结果引用 |
| GET /api/v1/plans/{id} | 查看完整计划 | 路线、仓储、违规/未服务和证据 |
| POST /api/v1/plans/{id}/confirm | 确认方案 | expected_version + plan_hash；冲突返回 409 |
| POST /api/v1/events | 接收/注入事件 | 去重结果与新的影响/重排作业引用 |
| POST /api/v1/simulations | 从快照分支推演 | 独立 simulation_id；不能修改确认计划 |
| GET /api/v1/runs/{id}/evidence | 导出脱敏证据 | 指标、模型调用、求解与校验版本 |

查询订单和资源的普通接口在实现时补充，按域组织，使用分页。错误包含 code、message、field_errors、trace_id、retryable；不得返回数据库栈或凭据。普通管理页沿用经过验证的认证实现，不自行设计加密。

模型允许调用的工具先限定为读取快照摘要、预检约束、提交规划、查看结果、推演、解释证据。正式确认通过用户界面或明确授权的固定策略进入应用层，不能把任意写库、SQL 或 shell 暴露给模型。

## 事务与回放

持久化订单、批次、资源日历、事件、快照、规划作业、计划、预留和运行证据。普通查询用规范化表；快照/求解输入可存不可变 JSONB 以便复现，不以 JSONB 取代全部关系约束。

确认事务锁定本次涉及的资源/批次记录，复核版本和整个占用时间段，写预留与计划状态；失败全部回滚。相同幂等键返回已有结果。并发确认、重复事件、乱序事件、任务超时、进程重启都纳入验收。过期预留按状态和租约释放，不能释放执行中的实物占用。

重排确认需在同一事务内替换受影响且未执行的旧预留，保留未受影响预留与实物占用；锁定新旧方案涉及的资源后按净占用校验。失败恢复旧状态，不出现“先全释放、再另开事务抢资源”的间隙。旧计划标记 superseded 并引用新计划，同一订单重排后不得重复占库或扣库存。
