# 冷链契约移植（路线 A · P1）

## 结论

R05 cold-chain **数据类型与快照槽位**已移植到当前 `packages/` 架构；尚未接入仓储 CP-SAT，
因此不声称 pre-cooling / exposure / 时变容量 / 7 天复用已经参与求解。

## 变更

- 新增 `packages/domain/src/logistics_domain/coldchain.py`：
  - `ColdChainSnapshot`
  - 温区、库位、占用、换批策略、预冷需求、暴露上限/片段、批次兼容
  - 全部使用当前域模型的 UUID 与整数秒；容量维度显式枚举
- `PlanningSnapshot` 增加可选 `coldchain`：
  - 无冷链条目的旧快照 hash 保持不变
  - 有冷链条目时纳入 canonical hash
- 新增 `packages/contracts/src/logistics_contracts/coldchain.py` DTO
- 新增 `coldchain_mapping.py`，`snapshot_dto` 投影可选冷链条目
- `PlanningSnapshotDTO` 增加 optional `coldchain`
- `scripts/export_contracts.py` 纳入 coldchain 模块

## 验证

```text
tests/unit/test_coldchain_snapshot_contract.py：1 passed
tests/unit/test_p02_03_planning_entities.py：4 passed
全量：308 passed（P1 前 307）
architecture：121 modules，0 violations
schema --check：exit 0
```

测试覆盖：

- 旧空快照 hash 兼容
- coldchain 快照 hash 包含冷链条目
- 嵌套 DTO → domain round-trip（UUID、枚举、容量、库位、换批、预冷、暴露、兼容策略）
- 旧 PlanningSnapshot hash 计算不被空 coldchain 扰动

## 未完成

- coldchain 尚未进入 `CpSatWarehouseScheduler`
- 未实现 pre-cooling 工序生成与 precedence
- 未实现 exposure union / 上限校验
- 未实现时变有效库容与 7 天跨批次复用
- 未实现 `ColdChainPlan` 输出与独立 R05 validator
- 未接仓储 from-job / 仓运联合
- 前端和 Docker 运行镜像未改

下一步：P2，把这些类型接入仓储 CP-SAT 和独立校验。
