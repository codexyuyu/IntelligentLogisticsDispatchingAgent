# R19 / B-04 异常重调度三策略对照结果

- 协议：`r19-b04-reschedule-strategies-1.0`；每求解臂预算 60000 ms；延误梯度 [900, 3600, 14400, 28800] s（事件发生在 0 s）。
- 场景 3 组 × 场景族 2 × 延误 4 档 = 24 组对照；完整三臂对照 15 组。
- 场景族：base = R18 生成器原样快照；stress = 同订单同路网，服务时间窗与保鲜期限压缩 1/2，并为每个（仓库×温区）增加一辆同型备用车。两族全部结果都报告，不挑选有利族。
- 各臂独立校验通过组数：{'no_reschedule': 15, 'full_reschedule': 21, 'local_reschedule': 15}。
- 不重调度出现违约的对照：['s12_seed17@base@28800', 's12_seed17@stress@14400', 's12_seed17@stress@28800', 's16_seed42@base@28800', 's16_seed42@stress@14400', 's16_seed42@stress@28800', 's20_seed66@base@28800', 's20_seed66@stress@14400', 's20_seed66@stress@28800']。
- 不重调度首次违约的有效延误(s)：{'s12_seed17@base': 28560, 's12_seed17@stress': 14160, 's16_seed42@base': 28320, 's16_seed42@stress': 13920, 's20_seed66@base': 28200, 's20_seed66@stress': 13800}。

| 场景 | 族 | 订单 | 原始延误(s) | 有效延误(s) | 臂 | 状态 | 合法 | 准时单 | 最晚延误(s) | 交接等待(s) | 改派订单 | 距离差(m) | 耗时(ms) |
|---|---|---:|---:|---:|---|---|---|---:|---:|---:|---:|---:|---:|
| s12_seed17 | base | 12 | 900 | 660 | no_reschedule | complete | True | 12 | 0 | 56070 | 0 | 0 | 0 |
| s12_seed17 | base | 12 | 900 | 660 | full_reschedule | complete | True | 12 | 0 | 56070 | 0 | 0 | 50630 |
| s12_seed17 | base | 12 | 900 | 660 | local_reschedule | complete | True | 12 | 0 | 56070 | 0 | 0 | 22508 |
| s12_seed17 | base | 12 | 3600 | 3360 | no_reschedule | complete | True | 12 | 0 | 64170 | 0 | 0 | 0 |
| s12_seed17 | base | 12 | 3600 | 3360 | full_reschedule | complete | True | 12 | 0 | 64170 | 0 | 0 | 50629 |
| s12_seed17 | base | 12 | 3600 | 3360 | local_reschedule | complete | True | 12 | 0 | 64170 | 0 | 0 | 22508 |
| s12_seed17 | base | 12 | 14400 | 14160 | no_reschedule | complete | True | 12 | 0 | 96570 | 0 | 0 | 0 |
| s12_seed17 | base | 12 | 14400 | 14160 | full_reschedule | complete | True | 12 | 0 | 96570 | 0 | 0 | 50629 |
| s12_seed17 | base | 12 | 14400 | 14160 | local_reschedule | complete | True | 12 | 0 | 96570 | 0 | 0 | 22506 |
| s12_seed17 | base | 12 | 28800 | 28560 | no_reschedule | complete | False | 9 | 5460 | 139770 | 0 | 0 | 0 |
| s12_seed17 | base | 12 | 28800 | 28560 | full_reschedule | failed | — | — | — | — | — | — | 52 |
| s12_seed17 | base | 12 | 28800 | 28560 | local_reschedule | failed | — | — | — | — | — | — | 9 |
| s12_seed17 | stress | 12 | 900 | 660 | no_reschedule | complete | True | 12 | 0 | 56070 | 0 | 0 | 0 |
| s12_seed17 | stress | 12 | 900 | 660 | full_reschedule | complete | True | 12 | 0 | 56070 | 0 | 0 | 50630 |
| s12_seed17 | stress | 12 | 900 | 660 | local_reschedule | complete | True | 12 | 0 | 56070 | 0 | 0 | 22508 |
| s12_seed17 | stress | 12 | 3600 | 3360 | no_reschedule | complete | True | 12 | 0 | 64170 | 0 | 0 | 0 |
| s12_seed17 | stress | 12 | 3600 | 3360 | full_reschedule | complete | True | 12 | 0 | 64170 | 0 | 0 | 50630 |
| s12_seed17 | stress | 12 | 3600 | 3360 | local_reschedule | complete | True | 12 | 0 | 64170 | 0 | 0 | 22507 |
| s12_seed17 | stress | 12 | 14400 | 14160 | no_reschedule | complete | False | 9 | 5460 | 96570 | 0 | 0 | 0 |
| s12_seed17 | stress | 12 | 14400 | 14160 | full_reschedule | complete | True | 12 | 0 | 50490 | 3 | 0 | 50631 |
| s12_seed17 | stress | 12 | 14400 | 14160 | local_reschedule | failed | — | — | — | — | — | — | 82 |
| s12_seed17 | stress | 12 | 28800 | 28560 | no_reschedule | complete | False | 9 | 19860 | 139770 | 0 | 0 | 0 |
| s12_seed17 | stress | 12 | 28800 | 28560 | full_reschedule | complete | True | 12 | 0 | 50490 | 3 | 0 | 50630 |
| s12_seed17 | stress | 12 | 28800 | 28560 | local_reschedule | failed | — | — | — | — | — | — | 2 |
| s16_seed42 | base | 16 | 900 | 420 | no_reschedule | complete | True | 16 | 0 | 79110 | 0 | 0 | 0 |
| s16_seed42 | base | 16 | 900 | 420 | full_reschedule | complete | True | 16 | 0 | 79110 | 0 | 0 | 50629 |
| s16_seed42 | base | 16 | 900 | 420 | local_reschedule | complete | True | 16 | 0 | 79110 | 0 | 0 | 22507 |
| s16_seed42 | base | 16 | 3600 | 3120 | no_reschedule | complete | True | 16 | 0 | 89910 | 0 | 0 | 0 |
| s16_seed42 | base | 16 | 3600 | 3120 | full_reschedule | complete | True | 16 | 0 | 89910 | 0 | 0 | 50630 |
| s16_seed42 | base | 16 | 3600 | 3120 | local_reschedule | complete | True | 16 | 0 | 89910 | 0 | 0 | 22507 |
| s16_seed42 | base | 16 | 14400 | 13920 | no_reschedule | complete | True | 16 | 0 | 133110 | 0 | 0 | 0 |
| s16_seed42 | base | 16 | 14400 | 13920 | full_reschedule | complete | True | 16 | 0 | 133110 | 0 | 0 | 50630 |
| s16_seed42 | base | 16 | 14400 | 13920 | local_reschedule | complete | True | 16 | 0 | 133110 | 0 | 0 | 22507 |
| s16_seed42 | base | 16 | 28800 | 28320 | no_reschedule | complete | False | 12 | 6930 | 190710 | 0 | 0 | 0 |
| s16_seed42 | base | 16 | 28800 | 28320 | full_reschedule | failed | — | — | — | — | — | — | 243 |
| s16_seed42 | base | 16 | 28800 | 28320 | local_reschedule | failed | — | — | — | — | — | — | 23 |
| s16_seed42 | stress | 16 | 900 | 420 | no_reschedule | complete | True | 16 | 0 | 79110 | 0 | 0 | 0 |
| s16_seed42 | stress | 16 | 900 | 420 | full_reschedule | complete | True | 16 | 0 | 79110 | 0 | 0 | 50632 |
| s16_seed42 | stress | 16 | 900 | 420 | local_reschedule | complete | True | 16 | 0 | 79110 | 0 | 0 | 22508 |
| s16_seed42 | stress | 16 | 3600 | 3120 | no_reschedule | complete | True | 16 | 0 | 89910 | 0 | 0 | 0 |
| s16_seed42 | stress | 16 | 3600 | 3120 | full_reschedule | complete | True | 16 | 0 | 89910 | 0 | 0 | 50630 |
| s16_seed42 | stress | 16 | 3600 | 3120 | local_reschedule | complete | True | 16 | 0 | 89910 | 0 | 0 | 22509 |
| s16_seed42 | stress | 16 | 14400 | 13920 | no_reschedule | complete | False | 12 | 6930 | 133110 | 0 | 0 | 0 |
| s16_seed42 | stress | 16 | 14400 | 13920 | full_reschedule | complete | True | 16 | 0 | 77310 | 4 | 0 | 50630 |
| s16_seed42 | stress | 16 | 14400 | 13920 | local_reschedule | failed | — | — | — | — | — | — | 136 |
| s16_seed42 | stress | 16 | 28800 | 28320 | no_reschedule | complete | False | 12 | 21330 | 190710 | 0 | 0 | 0 |
| s16_seed42 | stress | 16 | 28800 | 28320 | full_reschedule | complete | True | 16 | 0 | 77310 | 4 | 0 | 50630 |
| s16_seed42 | stress | 16 | 28800 | 28320 | local_reschedule | failed | — | — | — | — | — | — | 3 |
| s20_seed66 | base | 20 | 900 | 300 | no_reschedule | complete | True | 20 | 0 | 114210 | 0 | 0 | 0 |
| s20_seed66 | base | 20 | 900 | 300 | full_reschedule | complete | True | 20 | 0 | 114210 | 0 | 0 | 50630 |
| s20_seed66 | base | 20 | 900 | 300 | local_reschedule | complete | True | 20 | 0 | 114210 | 0 | 0 | 22508 |
| s20_seed66 | base | 20 | 3600 | 3000 | no_reschedule | complete | True | 20 | 0 | 127710 | 0 | 0 | 0 |
| s20_seed66 | base | 20 | 3600 | 3000 | full_reschedule | complete | True | 20 | 0 | 127710 | 0 | 0 | 50631 |
| s20_seed66 | base | 20 | 3600 | 3000 | local_reschedule | complete | True | 20 | 0 | 127710 | 0 | 0 | 22509 |
| s20_seed66 | base | 20 | 14400 | 13800 | no_reschedule | complete | True | 20 | 0 | 181710 | 0 | 0 | 0 |
| s20_seed66 | base | 20 | 14400 | 13800 | full_reschedule | complete | True | 20 | 0 | 181710 | 0 | 0 | 50631 |
| s20_seed66 | base | 20 | 14400 | 13800 | local_reschedule | complete | True | 20 | 0 | 181710 | 0 | 0 | 22508 |
| s20_seed66 | base | 20 | 28800 | 28200 | no_reschedule | complete | False | 15 | 8490 | 253710 | 0 | 0 | 0 |
| s20_seed66 | base | 20 | 28800 | 28200 | full_reschedule | failed | — | — | — | — | — | — | 602 |
| s20_seed66 | base | 20 | 28800 | 28200 | local_reschedule | failed | — | — | — | — | — | — | 39 |
| s20_seed66 | stress | 20 | 900 | 300 | no_reschedule | complete | True | 20 | 0 | 114210 | 0 | 0 | 0 |
| s20_seed66 | stress | 20 | 900 | 300 | full_reschedule | complete | True | 20 | 0 | 114210 | 0 | 0 | 50631 |
| s20_seed66 | stress | 20 | 900 | 300 | local_reschedule | complete | True | 20 | 0 | 114210 | 0 | 0 | 22510 |
| s20_seed66 | stress | 20 | 3600 | 3000 | no_reschedule | complete | True | 20 | 0 | 127710 | 0 | 0 | 0 |
| s20_seed66 | stress | 20 | 3600 | 3000 | full_reschedule | complete | True | 20 | 0 | 127710 | 0 | 0 | 50631 |
| s20_seed66 | stress | 20 | 3600 | 3000 | local_reschedule | complete | True | 20 | 0 | 127710 | 0 | 0 | 22511 |
| s20_seed66 | stress | 20 | 14400 | 13800 | no_reschedule | complete | False | 15 | 8490 | 181710 | 0 | 0 | 0 |
| s20_seed66 | stress | 20 | 14400 | 13800 | full_reschedule | complete | True | 20 | 0 | 106620 | 5 | 0 | 50632 |
| s20_seed66 | stress | 20 | 14400 | 13800 | local_reschedule | failed | — | — | — | — | — | — | 7 |
| s20_seed66 | stress | 20 | 28800 | 28200 | no_reschedule | complete | False | 15 | 22890 | 253710 | 0 | 0 | 0 |
| s20_seed66 | stress | 20 | 28800 | 28200 | full_reschedule | complete | True | 20 | 0 | 106620 | 5 | 0 | 50630 |
| s20_seed66 | stress | 20 | 28800 | 28200 | local_reschedule | failed | — | — | — | — | — | — | 3 |

## 汇总口径

- 不发布均值：only 15/24 pre-registered comparisons completed
- SimPy 回放一致性（s20_seed66，跑 2 次）：identical

**限制**：全部为合成场景；样本量不足以做显著性推断；“不重调度”不消耗求解预算，其代价体现在违约与延误上而不是耗时上；有效延误为 0 表示班次表吸收了该延误；本结果不替代已验收的 R17/R18 证据。
