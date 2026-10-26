# R19 / B-04 三策略对照已验收冻结归档

- 来源运行：`run_20261014_235140_246501`（2026-10-15 交接清理时已删除原始运行目录；本归档＝它的逐字节副本，逐文件 SHA256 见清单，来源目录名保存在 `source_run`）。
- 协议：`r19-b04-reschedule-strategies-1.0`；场景 3 组 × 族 ['base', 'stress'] × 延误 [900, 3600, 14400, 28800] s。
- 归档 16 个文件、5003952 字节，逐文件 SHA256 见 `r19_accepted_manifest.json`。
- 独立复算：24 组对照的每个指标与合法性均由归档方案重算，不一致数 0（见 `r19_recompute_audit.json`）。
- 各臂合法组数：{'no_reschedule': 15, 'full_reschedule': 21, 'local_reschedule': 15}。

## 口径

- 合成场景；不构成县域真实收益，未做显著性检验。
- 「不重调度」不消耗求解预算，其代价体现在违约与延误；求解耗时不可直接用来判定优劣。
- 求解器返回的无解是本次预算内的搜索结论，证据中原样保留错误类型。

## 复现

```powershell
cd backend; python -m tools.r19_reschedule_ablation --case-count 3 --budget-ms 60000
```
