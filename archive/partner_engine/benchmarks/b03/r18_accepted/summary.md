# R18 / B-06 多场景等预算成对实验结果

- 测试场景：5；每模式预算：90000ms。
- 同距离、全量服务、校验通过的可比较对：5。
- 等距离条件下等待改善/持平/变差：5/0/0。
- 改善率算术平均：40.13%。

| 场景 | 订单 | 判定 | 顺序等待(s) | 深度等待(s) | 改善率 |
|---|---:|---|---:|---:|---:|
| s12_seed17 | 12 | complete_validated_pair / equal_distance | 1260 | 900 | 28.57 |
| s16_seed42 | 16 | complete_validated_pair / equal_distance | 2880 | 1680 | 41.67 |
| s20_seed66 | 20 | complete_validated_pair / equal_distance | 4500 | 2400 | 46.67 |
| s20_seed88 | 20 | complete_validated_pair / equal_distance | 4500 | 2700 | 40.0 |
| s20_seed101 | 20 | complete_validated_pair / equal_distance | 4800 | 2700 | 43.75 |

**口径与限制**：每个场景的两种模式读取相同快照 SHA256、相同总求解预算；同一 R17 核心协调器，完整原始 CandidatePlan 和失败均留存。仅当两者订单全覆盖、校验通过且运输距离相同时才报告等待改善率。所有场景为合成压力测试，不代表县域真实货损或成本收益。
