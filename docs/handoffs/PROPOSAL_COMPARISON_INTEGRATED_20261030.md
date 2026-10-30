# 运输延误审批前的真实方案比较与时效场景集成

## 本次范围

- 在原始「联合调度 → 数据库模拟 → 异常处置 → 人工审批 → 回放」主流程中加入**真实候选方案评估**。
- 不修改调度核心算法、运营排程和仓储库存，不引入新数据库迁移。
- 新增合成的 `coldchain_chain_10_priority_delay.json`：三种配送位置和不同软时效截止，沿用原项目距离/时间矩阵。其订单、货物、仓库任务采用独立确定性标识，支持从现有联合调度页面显式导入。
- 新增只读的「分析可优化路段」：针对当前已校验运行的途中可接续时刻，以**真实局部 OR-Tools 求解与服务端指标比较**筛选可改善综合费用的方案；如果找不到正收益，明确返回没有推荐结果，不把独立三站基准数字挪用到当前运行。

## 使用路径

1. 联合调度 → 场景管理与高级设置 → **准备时效约束场景**。这是用户主动执行的数据库导入；请确保当前后端指向有写入授权的隔离环境，严禁连接 5433 演示库。
2. 选择新场景 → 计算并协商，等待 `checked`，正常启动数据库模拟。
3. 异常处置 → **分析可优化路段**，只读检索至多 8 个中途可接续位置；如果有正收益，点击「选用」，再「触发模拟延误并分析」。如果没有，可改变延误时长或场景，不应宣称已有优化收益。
4. 登记之后，在「人工批准模拟方案」按钮**上方**查看原计划 / 简单顺延 / 候选方案的配送距离、里程费、软时效迟到单数、累计迟到秒数和估算综合费用，以及每单交付时间和序列；需要看三维变化时点「预览三维候选轨迹」。
5. 人工批准或拒绝后进入回放，同样能展开路线和评估指标。已发生行程不可修改，审批只切换模拟版本。

## 数据口径与审计边界

- 三组指标取自**同一个 checked run 的 `transport_problem`、已落库模拟 `tracks`、`events` 及候选投影**。
- 由于 `track.distance_m` 在重排后可能仍是原路线值，距离由道路矩阵逐段求和，途中冻结路段按起止比例计算；因此属于**矩阵估算里程**，并非 GPS 实测。
- 费用 = 该车辆全程行驶里程估算费 + 车辆固定费 + 软时效交付完成超期罚金。软时效口径使用交付完成时间（不是求解器服务开始时刻）；它是**业务评估指标**，不冒充 OR-Tools 完整目标函数。
- 未配置订单软时效时，不宣称软时效优化；综合费用没下降时，明确显示「无改善」或「增加」。
- 只比较本次延误车辆，不声称对所有车辆或所有订单的全局改善。
- 原三站独立精确枚举基准仍留在对照实验页面，**与此次真实入库模拟指标完全分开**。
- 新时效场景已由 `ScenarioImport` 和 `prepare_scenario` **在无数据库连接条件下**完成结构校验；因本环境没有 OR-Tools、用户决定集中后验，本轮**没有执行该场景的真实联合求解与数据库端到端验收**，因此正收益仍需最终一次验收确认。

## 关键文件

- `apps/backend/src/logistics_backend/application/simulation_comparison.py`：实际运行的三策略矩阵/事件对比。
- `apps/backend/src/logistics_backend/application/integration_simulation.py`：生成异常投影时一并保存对比结果；只读机会筛选。
- `apps/backend/src/logistics_backend/api/integration.py`：只读场景获取、机会筛选接口。
- `apps/frontend/src/features/stageB/ProposalComparison.tsx`：审批前和回放的透明方案对比。
- `apps/frontend/src/features/stageB/Incident.tsx`：在途时刻预选、可优化路段分析、评估与审批。
- `apps/frontend/src/features/integration/Page.tsx`：新场景导入入口（高级设置）。
- `data/scenarios/coldchain_chain_10_priority_delay.json` / `scripts/build_priority_delay_scenario.py`：独立标识的确定性合成场景与生成脚本。
- `tests/unit/test_simulation_comparison.py`：对比分摊、重复交付/费用等边界测试样例。

## 与当前开发约定一致

- 本轮只进行 TypeScript 静态类型检查、Python 编译检查和场景合同校验；不安排 DSH 和数据库端到端验收。
- 不启动 Docker，不连接 5433/5434，不删除数据库历史，不向 GitHub push/merge。
