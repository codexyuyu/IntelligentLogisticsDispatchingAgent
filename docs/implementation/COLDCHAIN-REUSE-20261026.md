# 7 天跨批次复用（冷库时变容量）

## 实现

- `ColdChainSnapshot` 新增 `reuse_rules: tuple[ReuseRule,...]`
- `ReuseRule`：
  - `location_id`
  - `max_batch_age_s`（默认 604800 秒 = 7 天）
  - `min_gap_s`（跨批次清洁/隔离间隔）
- DTO / mapping / schema 已接通。
- CP-SAT 容量模型：
  - 无出库操作的占用，有效结束时间 = `min(horizon, start + max_batch_age_s)`；
  - 7 天后释放该库位容量，允许新批次复用。
- 独立 validator：
  - 同一库位相邻不同批次占用，间隔小于 `min_gap_s` → `coldchain_reuse_gap`；
  - 记录 `r05.reuse` checked code。
- `add_coldchain` 使用有效结束时间，不把“7 天后仍占用”当成无限占用。

## 验证

```text
unit coldchain contract：1 passed
warehouse 专项：6 passed
根目录（排除并发前端副作用用例）：399 passed
architecture：134 modules，0 violations
schema --check：exit 0
```

## 边界

- 7 天策略是显式声明，不默认套用到所有库位。
- `max_batch_age_s` 只释放容量，不改变暴露/货龄事实。
- 前端未改。
