# 指标与实验口径 · definition_version=1.0.0

所有指标带scope_id、source(planned/simulation/actual)、window_start/end、definition_version、单位、样本数、分子/分母及缺失原因。场景明确的有效需求集E由观察窗开始的基线订单及窗内新增订单构成，剔除**在服务发生前合法取消**的订单；已交付历史不可取消。未完成、失败、超时订单仍计入E。订单不可拆分；需求满足率按订单数，同时保留quantity-weighted辅助值，不能混称。无分母返回null和ZERO_DENOMINATOR，不返回0或100%。

| 必需指标 | 精确定义 / 单位 | 零值与边界 |
| --- | --- | --- |
| 需求满足率 | 已完整交付订单数 / \|E\|，ratio | 取消在途需处置仍有实物任务，但合法取消交付需求从E剔除并另报cancelled_count |
| 订单准时率 | E中completion_s<=soft_due_at_s的完整交付订单数 / \|E\| | 若soft_due缺失，以服务开始硬窗latest+service作为交付期限并标来源；未交付计不准时 |
| 平均延误 | 已交付订单的sum(max(0,completion_s-due_s)) / 已交付订单数，秒 | 保留全部已交付订单含零延误；未交付另报open_overdue_s，不能用此均值掩盖满足率 |
| 运输总距离 | 窗内实际已行路段距离和；planned为所有计划弧距离，米 | 部分在途段按位置进度计，source不混合 |
| 运输总成本 | distance+fixed_vehicle+transport_service+transport_overtime，分 | 不含未服务惩罚；冷链/仓储setup费用另列system_total_cost |
| 车辆利用率 | 各车busy秒总和 / 各车可用秒总和；busy为行车+服务+任务导致的等待区间并集 | 排除故障不可用段；分子分母裁剪到同窗口；载荷利用率另列分段重量率 |
| 仓储利用率 | 温区已占用体积×时长之和 / 可用体积容量×时长之和 | 温区、库位不重复相加；以温区汇总为主，库位作明细 |
| 月台利用率 | 月台实际占用（含必要清洁）秒 / 月台可用秒 | 每资源区间先求并集，非相邻重叠不重复计 |
| 设备利用率 | 设备使用units×秒 / 可用units×秒 | sorting/handling可分组，池与具名设备不重复汇总 |
| 求解时间 | 引擎调用前后monotonic_ns之差，毫秒 | build/queue/validate/persist分别报告，不混称求解时间 |
| 异常检测时间 | detected_at_utc - received_at_utc，毫秒 | 另报event_ingestion_lag=received-occurred；不能混用仿真秒与墙钟 |
| 重调度时间 | 影响分析启动到最终候选完整验证结束的墙钟差，毫秒 | 包括全部候选/扩展轮次，不含用户确认等待；API端到端另列 |
| 被修改任务数量 | 基版本未来可变任务集合F与候选按稳定task_id比较，added/removed/资源/时间/顺序变化的唯一ID数量 | 同任务多字段变只计1；完成事实必须零变化 |
| 方案扰动程度 | 0.4*assignment_change_ratio+0.3*time_shift_ratio+0.2*order_change_ratio+0.1*membership_change_ratio | 各项0..1，下方定义；无F且无新增时0；权重随policy version保存 |

F为事件时刻尚未完成的基版本任务，A为新增任务ID，归一分母N=max(1,|F union A|)。assignment_change_ratio为资源集合变化任务数/N；time_shift_ratio为sum(min(1,abs(new_start-old_start)/shift_scale_s))/N，默认shift_scale_s=3600，新增/删除不参与time项；order_change_ratio为路线前驱task_id变化数/N（新增/删除只在membership计）；membership_change_ratio=|added union removed|/N。changed_tasks单独计唯一任务数，不用扰动权重隐藏变化。

ScheduleDiff.added_cost=candidate.system_total_cost-base.system_total_cost，允许负数；delay_difference=candidate总soft_delay_s-base总soft_delay_s；resource_changes按task_id列before/after；affected_orders为所有变化任务触达订单并集；constraint_results包含前后报告及新增/解除违规。比较必须同source/窗口/定义，否则返回INCOMPARABLE_METRICS。

手算验收：E=5，交付4，按时3，交付延误[0,0,0,40]秒→满足率0.8、准时率0.6、平均延误10秒；车辆busy[60,30]、availability[100,100]→0.45；仓储体积占用100*10，可用200*10→0.5；月台无可用时长→null。4个未来任务中仅1个改派且时间/顺序/成员不变→changed_tasks=1、disturbance=0.4*(1/4)=0.1。

实验至少比较规则基线、solver-only、LLM+solver；异常比较local与all_unexecuted，冻结同一已发生前缀。规则基线只生成隔离实验候选，不直接发布；如正式采用必须先经OR-Tools固定赋值可行性检查，再通过独立validator。公平耗时比较需记录并同样计入各策略的验证耗时；不创建LLM直接生成计划基线。所有策略相同数据、可用资源、预算、规则、硬件，配对seed至少10次；LLM效果另测意图准确率/约束精确率召回率/工具合法率，不把接口自然语言能力错误归因于求解目标更优。

保留失败原始结果，报告成功率、中位数、p95（注明插值方法）、配对差和bootstrap区间（有放回配对采样，seed固定）。10次仅是最低工程复现实验，不足以泛化真实行业收益；论文结论以实际样本支持范围为准。单次演示耗时不作为性能承诺。
