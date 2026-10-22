# 2026-10-20 · R30-D / 仓储协同后端增强

- 用户明确授权直接基于 R30-C 完整包开发仓储数据映射、业务校验、仓运一致性与 AI 摘要，优先保证 10 月 26 日组会 Demo。
- 文件：`backend/app/domain/cold_chain_rules.py`、`backend/app/adapters/warehouse/validator.py`、`backend/app/application/coordinator.py`、`backend/app/adapters/persistence/pg_r27_workflow.py`、`backend/app/api/routes/agent_demo.py`、`backend/app/adapters/llm/prompts.py`、`backend/tests/test_r30d_warehouse_business.py`。不修改共享契约、正式 SQL schema、求解器核心和 React/Three.js。
- 增加批次、温区、数量、资源与实际运输完工时刻纯规则审计；显式 not_checked 防止 R24 零预留字段被错误宣传成真实余额。仓库 handoff 根据实际作业结束独立验证，AI 提供求解明细而非虚构顺序。
- 命令：`cd backend; python -m pytest -q tests/test_r30d_warehouse_business.py tests/test_r27_workflow.py tests/test_r30c_deepseek_agent.py tests/test_r30b_reschedule.py tests/test_r30a_pg_stage.py tests/test_r28_reconciliation.py tests/test_pg_r24.py tests/warehouse/test_cp_sat_migration.py tests/test_b03_coordination.py` => 70 passed。
- `python -m pytest -q tests --maxfail=3` => 收集时 `ModuleNotFoundError: simpy`；本机缺 `ortools`、`psycopg`，故未能实际联动求解器或 PostgreSQL。不宣称全量验证。更多运行限制详见 R30-D 操作说明。
- 已有 R24 verified_r24 预检会优先拒绝超量/温区错误（`r24_stock_lot_oversubscribed` / `r24_lot_dock_warehouse_or_quantity_conflict`），R30-D 不是替代原来的校验，而是独立冗余复查与明确覆盖口径。
- 不允许把静态合成路线当成 GPS 或实路规划，也不能把 `cold_chain_audit.partial` 误写为完整通过。
