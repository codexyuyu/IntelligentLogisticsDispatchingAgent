# 运输途中延误：真实求解的优化对照子场景

## 作用域与证据边界

- 本次以 DSH 修订版 `coldchain-latest (2).zip` 为基础。
- 新增**只读、独立的三收货点压力场景**，复用 `data/scenarios/coldchain_chain_10.json` 的实际合成道路距离矩阵和行驶时间矩阵。
- 三个配送点的软时效截止时间、延误时间、成本权重由独立 fixture 明确声明，可审计、可修改；这些值不是历史十订单业务运行的数据。
- 后端对剩余三个点的全部 **3! = 6 种访问顺序**分别计算真实距离、行驶时间、软迟到和综合成本，取最小值。无预设最优路径、前端没有写死优化比例。
- **这是精确枚举优化基准，不是既有 OR-Tools 十订单联合求解器或已批准的 PostgreSQL 运营模拟的结果。** 不能把子场景的收益当作完整十订单生产算法收益。

## 默认 90 秒延误，计算结果

| 指标 | 未延误原方案 | 延误后保留原路线 | 延误后重新求解 |
| --- | ---: | ---: | ---: |
| 路程 | 19 km | 19 km | 20 km |
| 里程费 | ¥41.80 | ¥41.80 | ¥44.00 |
| 固定车辆费 | ¥50.00 | ¥50.00 | ¥50.00 |
| 软时效违约费 | ¥0.00 | ¥4.50 | ¥0.00 |
| 综合目标（以上相加） | ¥91.80 | ¥96.30 | ¥94.00 |
| 软时效迟到订单 | 0/3 | 1/3 | 0/3 |
| 累计软时效迟到 | 0s | 90s | 0s |
| 返回时刻 | 2500s | 2590s | 2690s |
| 硬时窗 | 满足 | 满足 | 满足 |

与**相同延误的简单顺延**相比，重调度多走 1km、里程费增加 ¥2.20，但少迟到 90 秒、时效违约费减少 ¥4.50，综合目标最终减少 ¥2.30。不能声称节约里程或所有维度均有改进。

## 界面入口

左侧 `评测 → 对照实验` 页顶部新增 `途中延误 · 路线优化对照` 区域。后端只读接口：

`GET /api/v1/integration/benchmarks/delay-replanning?delay_s=90`

可改延误时长、点击“重新计算对照”查看新的完整指标、下载 JSON 结果。原有批量实验保留在页面下方。

数据文件：`data/benchmarks/delay_replanning_v1.json`；算法：`apps/backend/src/logistics_backend/application/delay_benchmark.py`；界面：`apps/frontend/src/features/experiments/DelayReplanningBenchmark.tsx`；参考证据：`artifacts/benchmarks/delay_replanning_90s_reference.json`。

## 非破坏性约束及验证状态

- 没有 PostgreSQL schema 迁移、写库、启动服务、Docker 操作，也没有接触 5433 或 5434。
- 没有改动既有的 `midroad_reroute.py`、模拟审批逻辑或原始 `coldchain_chain_10.json`。
- 仅做轻量静态检查：`tsc --noEmit` 无报错；新增三个纯函数测试通过。**未运行整套前后端验收、也未在数据库中执行完整十订单场景**。
- 当前环境没有 OR-Tools，故**尚未证明在原始十订单完整求解链路中可以产生相同的优化收益**。如果未来要求将此结果融入主联合调度流程，需要进一步建立具备真实差异的多节点十订单场景并在完整 OR-Tools + PostgreSQL 环境中验证。

### 只读复算（不连接数据库）

在项目根目录运行：

```bash
PYTHONPATH=apps/backend/src python -c "from logistics_backend.application.delay_benchmark import solve_delay_benchmark; import json; print(json.dumps(solve_delay_benchmark(), ensure_ascii=False, indent=2))"
```

这一对照强调时效—里程的权衡，而不是宣传所有指标都能优化。
