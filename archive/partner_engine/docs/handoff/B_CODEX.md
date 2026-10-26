# 给 B 的 Codex

你负责 B，先读根 AGENTS.md、DEV_LOG.md 开头、OWNERSHIP.json、contracts/README.md、docs/NAMING.md。不要开始重搭全栈。

## 你的文件

拥有 adapters/routing、adapters/matrix、adapters/simulation、domain/transport_rules.py、tests/transport、tests/simulation、data/transport、data/simulation、benchmarks/transport、benchmarks/simulation。代码位于 backend/app 下。可新增本域私有文件，更新 FILE_MAP；公共 ports/contracts 由 AC 集成维护。

## 实现顺序与交付

1. B01：固定矩阵 provider，实现 get_matrix(matrix_id, expected_version)，检查索引顺序/单位/版本/不可达；输入错误明确失败。
2. B02：实现 OrToolsRoutingSolver.solve(RoutingRequest) -> RoutingResult。严格遵守快照、仓库就绪与装货窗、双容量、温区、服务时长、车辆班次、必服务和冻结路线。无解/预算耗尽分开报告。第一阶段固定所属仓，一车一趟。
3. B03：实现独立运输校验。它不能调用 OR-Tools 或复用求解器约束构造判断。将普通数据映射到纯领域输入，不把 Pydantic 对象依赖引入 domain。
4. B04：SimPySimulator.simulate，固定种子，生成隔离分支。首月出发延误/月台故障在作业边界触发；C 决定事件去重、影响集和何时重排。Simulator 不修改正式确认计划和数据库。
5. B05：补规模/异常反例与运行说明。每次交代码、输入、测试输出和限制；在 AC 的机器可复现才算交付。

前置输入：contracts/examples/routing_request.json、data/scenarios/two_warehouses_20_orders.json。样例只是类型基线，必须独立验证其业务可行性。参考 archive/reference_demos/transport.py 的方法，不原样复制它的分钟/索引数据契约。

## 边界

- 不编辑前端、仓储排程、协调器、确认事务、模型入口。
- 不重新定义 DTO，不创建 truck/routeId 等别名；输出 routes 中节点是 node_id 字符串。
- 不在回调里请求矩阵，不悄悄丢必服务订单或自动放松硬时间窗。
- OR-Tools 9.15 的 SetAllowedVehiclesForIndex 在已测 Windows 包有绑定问题；可用 VehicleVar 排除不兼容值并写回归，详见 archive/reference_demos/README.md。
- 需要公共字段时提交 contracts/changes/yyyyMMdd-b-topic.md；AC 合并契约、生成产物及双方适配后再依赖。别在自己的副本私自发明协议。
- 未实现骨架会抛 FeatureNotImplemented，禁止删测试或返回空成功掩盖它。

完成每个 Bxx 后新增 docs/devlog/entries/ 时间戳日志，列出契约是否改变。运行骨架检查和相关 B 测试，给 AC 一个可合并提交或限定文件补丁；不要让 AC 覆盖整目录。
