# 冷链约束接入（P2 部分）

## 已完成

- CP-SAT 新增 pre-cooling precedence：
  - `PrecoolRequirement.precool_operation_id` 与 `loading_operation_ids` 都在本次请求时，
    强制 `loading.start >= precool.end`；
  - 预冷任务时长小于 `min_duration_s` 时显式 infeasible；
  - 操作不在本次 scope 时跳过，不伪造时间。
- 独立 validator 新增 `validation/coldchain.py`：
  - pre-cooling 时长/先后；
  - 仓储占用按半开区间 `[start,end)` 推导；
  - 按地点/容量维度计算峰值，检查声明容量；
  - 检查库位可用窗口；窗口外占用产生 `coldchain_storage_window`；
  - 按 batch 合并仓储暴露区间，检查 `ExposureScope.IN_WAREHOUSE` 上限；
  - 缺失预冷/装卸操作/暴露段时进入 `unsupported/not_checked`，不当作 0。
- `validate_warehouse` 合并 coldchain 违规与 checked/unsupported codes。

## 验证

```text
tests/integration/test_warehouse_job_pipeline.py：6 passed in 7.94s
全量：309 passed in 117.15s，exit 0
architecture：122 modules，0 violations
schema --check：exit 0
```

新增测试用例覆盖：

- 预冷任务必须先于装载；
- 仓储占用跨出库位可用窗口 → `coldchain_storage_window`；
- 仓储暴露累计超过上限 → `coldchain_exposure`；
- 同一 solution 仍保留仓储资源/换批检查。

## 未完成

- 时变有效库容尚未进入 CP-SAT；当前只在 validator 检查声明容量与可用窗口；
- 7 天跨批次复用规则尚未建模；
- 装载/运输暴露未纳入（只检查 `in_warehouse`）；
- 冷链 `ColdChainPlan` 输出/持久化未实现；
- 仓储 from-job、仓运联合未开始；
- Docker 运行镜像未改。

因此这是 P2 的“预冷 + 仓储暴露 + 容量/窗口校验”切片，不是完整 R05。
