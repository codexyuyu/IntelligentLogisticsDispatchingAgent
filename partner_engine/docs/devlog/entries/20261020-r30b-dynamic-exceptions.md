# R30-B 只读异常调度增量日志（2026-10-20）

继承 R30-A，目标覆盖四类异常。修改范围：`backend/app/adapters/persistence/pg_r30b_reschedule.py`、`pg_r27_workflow.py`、`backend/app/api/routes/postgres_demo.py`、`backend/start_pg_r30b_local.ps1`、`backend/tests/test_r30b_reschedule.py`、`backend/tests/test_r27_workflow.py`、`frontend/src/features/closedLoop/{Page.tsx,ExceptionPanel.tsx}`、相关指南/README/DEV_LOG、合同导出。见 `docs/R30_STAGE_B_EXCEPTION_RESCHEDULE.md`。

**证据等级**：隔离环境静态/单元验证；实机 PostgreSQL、OR-Tools、Windows 前端构建均待用户验收。历史日志与已接受的 R19/R28/R29/R30A 证据保留；不冒充本次运行。源代码使用 R30-A 的抽象约束模型，停止故障车转运或换批次等无记录操作，宁可未服务也不编造可执行结果。
