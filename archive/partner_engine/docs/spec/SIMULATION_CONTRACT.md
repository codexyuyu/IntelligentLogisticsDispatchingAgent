# 仿真、事件与回放契约

DigitalTwinEngine为纯状态投影；SimulationEngine调度SimPy时间；EventEngine校验并排序事件；ScenarioEngine加载有版本场景。运行模型均属于simulation_id分支，正式业务表不被仿真更新。API与worker间使用typed控制命令，React动画由仿真视图驱动。

MVP使用非实时`Environment`，整数秒精度，不将UI播放倍速当物理时间精度。SimPy `run(until=t)`的数值停止边界不应被假设为自动处理t时刻所有事件；本项目的`advance_to(t)`另定义为处理所有<=t事件，再在同一时刻事件批次排空后允许快照。实际实现按[SimPy environments 文档](https://simpy.readthedocs.io/en/latest/topical_guides/environments.html)验证边界。

事件总排序键`(effective_at_s, priority, insertion_seq)`，priority固定：故障/取消0，完成1，派发2，观测3。源事件`occurred_at`/`received_at`分开存；相同事件ID去重；乱序未来事件可重排待执行队列，迟到事实进入reprojection_required并新建投影快照，不原地覆盖已审计历史。故障与完成同秒先处理故障；后续完成事件根据当前状态判定失效或合法，规则一致。

车辆执行过程显式跟踪位置（at_node / on_arc with from/to/start/end/progress）、载荷、已服务订单、班次剩余与货物位置。仓储执行跟踪资源等待/占用、前驱完成、清洁、初始库存与出入库账。多资源申请由统一admission一次验证和授予，资源ID排序避免部分占有死锁。故障中断显式记录executed_s、remaining_s和货物状态；不能延续已不可能实现的旧结束时刻。

随机性：每个分支显式seed及多个独立随机流（travel/service/fault）；共同随机数按(scenario_seed,stream,task_id,event_kind,occurrence_index)寻址，避免一种策略多调用一次随机数使全轨迹错位。保存生成器算法/版本和状态，不依赖模块全局random。无随机扰动时同版本同输入必须轨迹一致；有扰动时同环境/seed/输入保持一致，跨版本比较需重建基准。

快照包含TwinState、完整待执行事件及payload、RNG状态、剩余作业、资源队列/占用、处理游标、plan_hash、matrix版本、schema_version。只在安全边界存储。恢复通过这些数据重建新的Environment与domain进程，不pickle运行中的generator或宣称SimPy原生支持任意进程序列化。恢复点在行车中时保存剩余路段时长和载荷，在作业中时保存剩余时间与占用资源。

反事实分支复制快照的不可变数据，分配新simulation_id，替换指定事件/策略；主分支结果不变。对比记录同seed策略、分支点、矩阵版本、观察窗口和指标定义。观测数据source明确simulation；不得把合成示意图和阈值温控当真实传感器或高精度数字孪生。

进度控制：pause等待当前安全边界；step指定advance_to_s且不得倒退；control_seq单调，重复返回同回执；cancel使未执行事件终止并保存最终快照；resume从持久状态恢复。作业进程崩溃由租约重领，结果按simulation/control_seq幂等保存。完成/失败/取消均保留原始事件日志和state hash。

验收：T1无扰动终态t1020；t400快照恢复与连续执行相同；t10故障/完成排序一致；两分支资源互不污染；重复事件只记一次状态变化；零长度step不得重复处理事实；事件总数/同刻递归生成需上限，超限SIMULATION_EVENT_LIMIT并留下诊断。
