# B-01 CP-SAT 新框架迁移完成

## 本次变更

1. 保留原 `algorithm-service/` 全部代码，作为旧版 B-01 回归基线，不删除、不覆盖。
2. 将 B-01 的“可由当前共享契约表达”的仓储排程能力迁入 `backend/app/adapters/warehouse/cp_sat_scheduler.py`，实现 `WarehouseScheduler` port。
3. 新增 `backend/app/adapters/warehouse/validator.py`，独立检查 release/deadline、资源可用窗口、资源不重叠、前置关系、冻结事实与请求范围。
4. 新增仓储迁移说明 `backend/app/adapters/warehouse/MIGRATION.md`。
5. 新增回归测试 `backend/tests/warehouse/test_cp_sat_migration.py`。

## 重要边界

当前共享契约没有完整表达旧版 B-01 的批次数量分配、订单分配量、温区/品类与冷间库存容量等 richer 业务字段，因此新适配器不自行猜字段、不修改公共契约。
这些旧版能力仍保留在 `algorithm-service/`，待团队完成正式 contract change 后再逐项迁移。

## 验证

- Python compile check：PASS
- backend pytest：22 passed
- 旧 `algorithm-service` 目录仍存在
- 未执行数据库 DDL/DML
- 未删除旧 Vue3/Spring Boot legacy 项目
