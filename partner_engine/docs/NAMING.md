# 命名与语义规范

## 名称和层次

Python 文件/函数、JSON 字段、HTTP operation_id 均用 snake_case。Python 类和 React 组件用 PascalCase；TS 内部局部变量可用 camelCase，但来自接口的字段原样保留 snake_case，不建 alias。URL 集合用复数 kebab-case，例如 `/api/v1/planning-jobs`。内部接口没有 HTTP 地址，不再为 B 建一套 `/routing/...` API。

ID 是带类型前缀的不透明字符串：`ord_`、`veh_`、`wh_`、`node_`、`batch_`、`res_`、`op_`、`snap_`、`matrix_`、`job_`、`plan_`、`event_`、`sim_`、`run_`、`req_`、`scenario_`。不可用数组序号替代 ID；矩阵索引只在 adapter 内映射。字段写 `order_id`/`vehicle_id`，不交替用 `id`/`orderId`/`truck_id`。

`version` 是正整数对象版本；`contract_version` 是 SemVer。`plan_hash` 是计划规范化内容的 SHA-256，算法待 AC 实现并写测试；不得用固定字符串作为实际确认哈希。`job` 仅指计算作业，仓内任务叫 `operation`，两者状态不混用。

## 单位和时间

重量整数 kg，体积整数 L，距离整数 m，时间偏移/时长整数 s，预算及实测耗时 ms；字段必须带 `_kg/_l/_m/_s/_ms`。首月不表达不足 1 kg/L 的量，不能悄悄四舍五入；将来精度变更走契约升级。温区用 chilled/frozen，具体阈值来自场景规则；将来数值温度用 0.1℃整数。数量 `quantity_units` 是该批次一致的最小计数单位，不与 kg 混用。

`origin_at`/`observed_at`/`received_at`/`expires_at` 是带时区 ISO 8601。其他 `*_at_s` 及 `start_s/end_s` 是相对 snapshot.origin_at 的非负秒；当前仿真时刻 `simulation_time_s` 不能当 Unix 时间戳。存储统一 UTC，业务展示可转 Asia/Shanghai。

TimeWindow 用在订单时表示**服务开始**可在闭区间 `[start_s,end_s]` 内；车辆 shift_window 限制整趟行程；资源 available/unavailable_windows 与 ScheduledOperation 用半开区间 `[start_s,end_s)`，相邻端点不冲突。窗口对象相同，字段上下文决定语义；不要将服务开始截止当服务结束截止。保鲜截止另外检查，不能用服务窗代替。

Vehicle.remaining_* 是事件时刻剩余可装容量；路线 stop.load_* 是完成该站操作后的车上载荷。首月一车一趟，出仓加载、配送减载；在途重排必须保留当前位置及已装货。WarehouseHandoff.ready_at_s 是货物完成装车准备的最早时刻；车辆须满足所载每单就绪条件和装货窗口，不能各自独立任取最早时刻。

矩阵 node_ids 给出唯一索引顺序，None 表示不可达，0 仅代表合法零成本/对角线；不允许用 None→0 填空。矩阵、道路、场景规则均带来源和版本。

## 状态、错误、边界

状态只使用 domain/states.py。计算 succeeded 不等于计划 confirmed。optimal 只对声明的求解范围成立；no_solution_within_budget 不代表已证明无解。无兼容车、未知实体、缺参数分别返回明确原因。

所有错误使用 `{code,message,field_errors,trace_id,retryable}`，不再包一层 `{detail:...}`。HTTP：未实现 501，输入格式 422，版本/资源冲突 409；成功码由 OpenAPI 定义。所有有副作用的 POST 除纯解析外要求 Idempotency-Key；重复键与内容冲突的处理由 AC 实现，骨架目前仅检查 header 存在。

候选计划不预占正式库存。确认须同时检查 plan_hash、计划版本、快照/资源版本、独立校验报告；重排在同一事务替换未执行预留。模型不直接确认计划。共享 DTO 只校验声明的结构与基本范围，实体引用、全链库存与时序必须由独立业务校验完成。
