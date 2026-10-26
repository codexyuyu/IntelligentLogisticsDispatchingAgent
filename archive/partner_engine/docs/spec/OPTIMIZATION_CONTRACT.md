# 确定性优化与校验设计

本项目“确定性”指使用显式约束、受控求解器和可重复检查决定方案有效性，不表示所有启发式搜索在任意硬件/版本/限时下输出同一条路线。固定版本、排序、配置、单worker、seed可提高可复现性；业务Gate主要比较硬约束、目标值及容许区间，只有小型手算例要求指定路线。算法仍可能超时或在有限搜索内找不到已有可行解。

## 运输模型（P06–P07）

变量：`next_i` 下一节点，`vehicle_i` 分配车辆，`active_i` 是否服务，`T_i` 服务开始秒，`W_i/V_i` 货物重量/容积，`used_k` 车辆启用。每车有明确起点终点，必需节点恰好一次，选择节点的路径形成对应车辆路线。RoutingModel处理路径连通；业务ID与求解内部index严格映射。

约束：对弧i→j，`T_j >= T_i + service_i + travel_ij`，slack表示等待；`earliest_i <= T_i <= hard_latest_i`；班次、回场、最大驾驶/工作时长显式限制。累计Time代表服务开始，结果另重建arrival/departure；不可达弧移除，禁止0距离兜底。距离/时间为预载不可变矩阵，天气改变产生新版本，求解回调无网络/数据库访问。[Routing dimensions 官方说明](https://developers.google.com/optimization/routing/dimensions) 支持时间与载荷维度及等待量的建模基础。

重量和容积分别沿路径满足`0 <= load_before/after <= capacity`；起始配送货物载荷等于该车分配的仓内货物之和，不能fix start=0再把出库配送减成负载。提货增加、送货减少；提送同车且先后。车辆起点已有实物载荷来自ExecutionSnapshot，不能重置。MVP单车单趟、不拆订单；重载回仓二次出发属于后续增强，输入此类请求返回UNSUPPORTED。

冷链：每车固定单车厢setpoint；所有承运Cargo要求`min_temp <= setpoint <= max_temp`，资格与货物类型形成可用车辆集合。禁混装优先保守整趟不共车，记录能力限制；多车厢、多温动态切换不在MVP。最大脱冷暴露时长由仓运交接/等候链累计校验；没有暴露区段数据时必需规则unsupported，不能声称温控通过。冷链推演是简化阈值/时长模型，不声称高精度热力学仿真。

目标：`objective_cents = business_cost_cents + optional_unserved_penalty + soft_late_penalty + disturbance_penalty(仅重排)`；business_cost按每弧整数分四舍五入，加车辆启用/服务/加班/准备费用。罚分与真实运输成本分开显示，不把未服务惩罚称已花费运输费。必服务订单无丢弃罚分通道。任何“大权重”须先证明费用上界及int64安全，否则拒绝；不承诺加权和等于严格词典序最优。

配置：默认first solution `PARALLEL_CHEAPEST_INSERTION`，local search `GUIDED_LOCAL_SEARCH`，wall budget 5000ms，测试固定节点排序，seed在锁定引擎支持时明确配置；不能给不支持seed字段的版本编造属性。worker外壳硬截止。保留引擎状态；Routing普通fail映射UNKNOWN，不映射已证明INFEASIBLE；超时无incumbent映射TIMEOUT；有有效incumbent可返回FEASIBLE并注明time_limit。非空assignment才提取。参考[Routing options](https://developers.google.com/optimization/routing/routing_options)。

提取与验证：返回车—订单—route—stop—arrival—service_start—service_duration—departure—load—cost完整结构。独立validator不读取assignment、callbacks或求解变量，重新核对覆盖、连通、矩阵距离、时间递推、物理载荷、温控、司机与费用；相同输入hash/规则版本匹配报告才有效。

## 仓储模型（P08–P09）

变量：每工序start/end整数，duration正整数；候选资源分配presence布尔及optional interval；资源相邻弧`x_ij`；存储区间长度由入出库端点决定。必需任务恰选一个资格合格资源；receive/unload/sort/dispatch/load加派生setup均具名。

约束：`end=start+duration`，前驱end+lag<=后继start；独占月台/设备NoOverlap；人员、设备池、温区重量/容积Cumulative。可变资源能力通过固定blocker占用“基准容量-当前可用容量”表达，重复不可用区间先归一化，不能双重扣减。库位占用从入库完成到出库开始，初始库存从horizon起点计入，未出库货物到horizon末；数量守恒、固定温控点与库存不得为负。

相邻准备使用每资源单一circuit、dummy起终节点、可选任务未选自环、弧与presence关联。选中i→j才强制`start_j>=end_i+setup(i,j)`；dummy起始切换包含资源初始状态；不得对所有非相邻配对重复扣准备。需要人/设备的清洁产生显式interval并占资源；月台、温区、分拣类别切换均来自版本化SetupPolicy，不藏在备注中。NoOverlap本身不添加这些准备时长。

目标：软延误分+加班分+准备分+makespan权重，所有项清楚记账。配置默认`num_search_workers=1, random_seed=42, max_time_in_seconds=5`，实际字段依锁定OR-Tools API核验。CP-SAT使用整数，分别处理OPTIMAL/FEASIBLE/INFEASIBLE/MODEL_INVALID/UNKNOWN，不把UNKNOWN当无解。[CP-SAT 官方文档](https://developers.google.com/optimization/cp/cp_solver) 说明整数建模和状态区别。

只提取presence=true区间；独立按时间排序检查NoOverlap/capacity/前驱/setup/库存/冷链/成本，不把solver内部“无违规”直接复制成验证报告。小规模W1手算及枚举oracle仅在tests使用。

## 仓运联合（P16-02）

目标是找到经完整验证的可执行联合方案，不承诺分解法全局最优。候选仓过滤考虑库存、温区、设备与作业窗，每单最多2仓；仓储报价ready窗口→运输产生到达/离开→仓储按真实时间再排→冲突反馈收紧窗口或替代仓。最多3轮、15秒共享预算；重复候选hash停止，保留每轮诊断。禁止通过无限等待或扩大硬订单窗口隐藏冲突。

完整验证：装车end<=departure；车辆arrival<=卸货start；后续入库/分拣/出库顺序；货物数量、位置与库容守恒；路线、车辆、人员、月台全局占用。报价是候选信息，只有ScheduleService提交才预留。若候选仓限制导致无候选，诊断必须限定搜索范围；可按显式策略扩仓后重新求解，不断言全局不可行。

## 局部重调度（P14–P15）

严格流程：事件识别→影响分析→受影响任务→候选调整→局部求解→硬约束验证→方案比较→建议→处置记录。

影响从订单/车/路段/仓储资源沿任务依赖、实物链、共享资源重叠闭包扩展，每条变化有原因路径。冻结completed、已消耗库存和不可逆装载事实；正常不可抢占在执行任务保留，故障中断保存已完成部分与剩余工作。未来未受影响任务的资源、时间、顺序固定；它们的占用仍作为子问题边界约束。

车辆在途以event_time真实/模拟位置建virtual_start，剩余货物/驾驶时长/班次真实继承。故障载货换车必须有救援车辆到达、交接地点、时长、容量、温控暴露校验；缺数据MANUAL_REQUIRED。取消在途单生成返仓/已验证处置任务，不能使货物消失。

决策变量只对mutable集合重建运输/仓储变量，冻结任务以等式或固定interval锁住。候选策略最多3个；搜索范围local→expanded→all_unexecuted最多3层，共用15秒；扩大范围不放宽硬约束。合并后运行完整validator。失败时新事实下重验旧计划，只允许仍安全部分继续，失效任务输出暂停建议；建议尚未提交不能改变正式状态。

比较排序键为`(optional_unserved, soft_delay_s, business_cost_cents, disturbance)`；仅在已验证候选中选择，不宣称词典序全局最优。扰动及差异公式见[指标契约](METRICS_CONTRACT.md)。新版本parent指向旧版本，历史内容不覆盖。

## 提交与并发（P03、P16）

服务先验权限和确认对象、读取新事实并跑validator，再开启短事务按稳定资源ID顺序锁资源和Schedule行，复核snapshot revision向量与active版本。校验和提交之间任何数据变化使事务返回409；不得边长时间求解边持锁。版本、预留、库存承诺、幂等receipt、审计和outbox原子提交；失败全部回滚。锁粒度和死锁处理以实际PostgreSQL集成测试验证，依据[PostgreSQL 显式锁文档](https://www.postgresql.org/docs/current/explicit-locking.html)选择行锁与重试策略。

## 独立校验硬规则代码

ORDER_COVERAGE、ROUTE_CONNECTIVITY、UNREACHABLE_ARC、WEIGHT_CAPACITY、VOLUME_CAPACITY、PICKUP_DELIVERY_ORDER、HARD_TIME_WINDOW、SERVICE_DURATION、VEHICLE_AVAILABILITY、DRIVER_SHIFT、TEMPERATURE_COMPATIBILITY、CARGO_COMPATIBILITY、COLD_EXPOSURE_LIMIT、RESOURCE_NO_OVERLAP、RESOURCE_CAPACITY、RESOURCE_CALENDAR、TASK_PRECEDENCE、SETUP_VIOLATION、STORAGE_CAPACITY、INVENTORY_CONSERVATION、HANDOFF_VIOLATION、FROZEN_PREFIX_CHANGED、COST_OR_DISTANCE_MISMATCH、UNKNOWN_REQUIRED_CONSTRAINT。每条规则需要required/checked/unsupported覆盖记录及至少一个单点破坏反例。
