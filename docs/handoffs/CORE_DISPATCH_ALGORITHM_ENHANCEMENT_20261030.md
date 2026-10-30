# 核心调度算法增强：实现与集中验收说明

**基础**：DSH 验收 ZIP `coldchain_agent_acceptance_20261030.zip`，基于 Stage A/B + Agent 整合版。
**性质**：完整源码交付的待隔离环境验收版本；不是已经通过 OR-Tools / PostgreSQL / 浏览器端到端验收的正式版本。

## 一、本轮已经修改的内容

1. `OrToolsTransportSolver`：在 Routing 求解阶段约束货物温区与 `allowed_cargo_types`，允许送货-only 的 *onboard continuation*，从非零车载量建立重量/体积维度；优化中加入车辆固定费用、按车辆里程费率折算的弧成本（分/弧四舍五入）、配送软到期惩罚和可配置时间跨度惩罚，保留原独立后置校验。车辆总距离仍从原始矩阵取值，不把收费单位当成距离。
2. `validation/transport.py`：补充车辆货类独立硬校验。
3. `midroad_reroute.py`（新增）：在途延误的**保守接续**：保留事发前已执行路段和停靠点；原地等待；必须沿当前路段行至下一服务节点并完成该站服务；从该节点按已在车载荷重新求解**剩余站点**；对剩余停靠点及其节点集合、时间窗、车载量、运输弧、车辆可用窗口、所有订单交付事件进行检查。任何不可用候选明确 `not_resolved`。
4. `IntegrationSimulationService.project_delay`：Agent 只读预演与异常登记复用同一投影算法。局部路线可行且通过额外检查后写入**模拟候选轨迹与候选事件**，等待人批准；否则继续使用原来经过验证的 `hold_and_shift`。没有真实派车、库存和运营排程写入。
5. `state_at` 统一返回**实际生效版本**，不因查看未经批准的 candidate 就声称 active_version=1；`get()` 的回放时间上限覆盖候选结束时间。
6. 现有前端“异常处置”和“仿真回放”复用原页面，显示策略与局部求解状态；candidate/approved 选择候选轨迹绘图，显示服务端位置的路段进度；示意图**不代表 GPS**。
7. 增补两个定向测试位置（`tests/unit/test_midroad_reroute.py` 和原 Stage A 轨迹测试），更新 Stage A PostgreSQL 验收断言以适应新策略。

## 二、严格限制

- 只支持模拟车辆运输中**两个节点之间的延误**，且下一个服务节点之后还有待办站点。不支持途中横跨到另一条道路、不支持真实 GPS、不支持已服务节点回滚、多车辆跨车转单、连续异常；非适用场景回退 hold/resume。
- 局部求解并非强制改变访问顺序：`simulated_local_reroute` 才表示顺序改变；`simulated_local_retimed` 表示重求解但顺序不变；`simulated_hold_resume` 表示无可批准的优化路线或没有优于安全保底方案。必须分别准确演示。
- 每次模拟仍最多登记一次延误；审批保留原人工批准/拒绝和幂等性；实际库存、运营排程不应变动。
- 搜索目标采用单弧成本的整数分近似；不要宣称证明全局最优或实现实时道路动态导航。
- 修改了运输求解目标，既有场景的距离、费用和车辆排程可能发生变化，必须以**本轮重新跑出的数据**为准，而不是引用上轮验收截图的数值。
- 没有新迁移，也没有调用任何数据库。本轮没有修改 Git 历史、没有推送远端。

## 三、已在本环境实际执行的检查

- `python -m compileall -q apps packages tests`：通过。
- 使用全局 TypeScript 编译器对 `api.ts`、`Incident.tsx`、`Replay.tsx` 单文件语法解析：3/3 通过，**非**项目级 TypeScript 类型检查或 Vite 构建。
- `pytest -q tests/unit/test_midroad_reroute.py`：收集失败，原因是环境**未安装 OR-Tools**。尝试安装时网络 DNS 不可用。**不能声称算法回归已经通过**。
- 未执行 PostgreSQL 5434 或 5433 操作；未执行端到端浏览器测试。

## 四、交给 DSH 的集中总验收（只需一轮）

1. 从本 ZIP 导出至全新工作副本，保存已验收版作为回滚基线；核对 Python 3.12、项目锁文件、Node 版本，依项目规范安装 OR-Tools/SimPy/前端依赖。
2. **先在完全无数据库的环境**运行：`pytest -q tests/unit/test_midroad_reroute.py tests/unit/test_integration_simulation_tracks.py tests/unit/test_vehicle_delay_reschedule.py tests/unit/test_vehicle_delay_merge.py`，再运行其它 solver/validation 测试。
3. 运行 `npm run --workspace @logistics/frontend build` 与 `npm run --workspace @logistics/frontend test`。
4. 获得明确授权后只在隔离 5434 库运行 `tests/integration/test_integration_simulation.py` 和一次浏览器端到端，确认原方案 v0、候选策略、批准 v1、拒绝 v0、模拟时间轴、订单送达数、剩余路线变化、无位置跳跃、未受影响车辆不变、库存及运营排程不变。**绝不触碰 5433**；不要使用默认映射 5433 的 compose。
5. 增加一组能触发**实际不同停靠顺序**的明确合成场景：必须在截图/原始响应中看到 `route_changed=true`、`strategy=simulated_local_reroute`，并证明剩余路径改动与 before/after ETA 一致。若不能产生此场景，就应客观记为“局部求解接续框架已实现，改线能力未验收”，不能宣称全部成功。
6. 集中处理测试失败，必要时做定向回归，再一次性交付完整源码、测试记录和回放证据。全量 `pytest -q` 的历史环境失败另列，不要合并计入已通过。

## 五、验收红线

**没有实际 OR-Tools 运行证据、没有完整配送覆盖证据、没有经人工审批的 v1 轨迹证据，不得把改线能力宣布为已正式验收。**
