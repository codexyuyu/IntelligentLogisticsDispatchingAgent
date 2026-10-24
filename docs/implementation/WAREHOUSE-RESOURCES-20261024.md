# WAREHOUSE-RESOURCES-20261024

用户明确要求补第一项“仓储完整排程”：多资源同时占用、相邻准备时间。
本任务以现有未提交的 WAREHOUSE-JOB 修复为基线；不回退旧改动，不签 Gate。
本次业务范围明确包含 B 的仓储求解与独立校验，非沿用上一轮的一处导入授权。

写集合：
- packages/domain/src/logistics_domain/{planning,warehouse}.py
- packages/contracts/src/logistics_contracts/{planning,warehouse,mapping}.py
- packages/optimization/src/logistics_optimization/warehouse/solver.py
- packages/optimization/src/logistics_optimization/validation/warehouse.py
- apps/backend/src/logistics_backend/application/{warehouse,schedule}.py
- tests/solver/test_warehouse_resources_setup.py
- tests/integration/test_warehouse_job_pipeline.py
- contracts/changes/WAREHOUSE-RESOURCES-20261024.md
- contracts/{schemas,openapi}.json（仅生成）
- docs/implementation/WAREHOUSE-RESOURCES-20261024.md
- docs/implementation/reports/WAREHOUSE-RESOURCES-20261024.md
- tmp/WAREHOUSE-RESOURCES-20261024/**

不修改前端、所有权、依赖锁、官方 Gate、运输/仿真模型。仓储候选自动生成、
正式提交中的数量预留/准备预留和仓运联合仍由后续任务实现；本次保留候选数据完整性。
使用真实 CP-SAT、独立反例、微型枚举对照与真实 PostgreSQL/worker 回归。
