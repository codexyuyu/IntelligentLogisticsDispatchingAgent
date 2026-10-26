# R18 / B-06 已验收冻结归档

- 来源运行：`run_20261014_212550_205783`（2026-10-15 交接清理时已删除原始运行目录；本归档＝它的逐字节副本，逐文件 SHA256 见清单，来源目录名保存在 `source_run`）。
- 协议：`r18-b06-multiscene-paired-1.0`；每模式总预算 90000 ms；场景数 5。
- 归档 14 个文件、487201 字节，逐文件 SHA256 见 `r18_accepted_manifest.json`。
- 复算核对：5 组逐单重算与运行 summary 完全一致（见 `r18_multiscene_audit.json`）。

## 口径

- 等待指标为逐订单「备货完成 → 车辆离仓」累计值，不是车辆排队时间；改善率仅在两组运输距离相同时披露。
- 全部为合成压力场景；不构成县域真实收益、成本或距离改善，也未做显著性检验。
- 归档字节保持运行当时的 CRLF 换行原样；换行缺陷已在本次收尾修复，故重新运行会产出 LF。

## 复现

```powershell
cd backend; python -m tools.r18_multiscene_ablation --case-count 5 --budget-ms 90000
```
