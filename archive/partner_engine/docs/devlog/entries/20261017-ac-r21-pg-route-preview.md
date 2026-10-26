# 2026-10-17 · AC · PostgreSQL 只读接口 + R20 正式算法演示调用

负责人 AC：本任务由用户明确交付。具体边界、模拟假设、安全限制及 Windows 步骤见 `docs/R21_POSTGRES_R20_INTEGRATION.md`。

改动文件：`backend/app/adapters/persistence/pg_routing_preview.py`（新增）、`backend/app/api/routes/postgres_demo.py`（新增）、`backend/app/main.py`（挂载隔离子应用）、`backend/start_pg_local.ps1`（新增）、`backend/tests/test_pg_routing_preview.py`（新增）、`backend/requirements.txt` / `requirements-lock.txt`（psycopg）、`README.md`、`DEV_LOG.md`、`FILE_MAP.md`、本日志及 R21 指南。

遵循已有共享契约；没有改 `backend/app/adapters/routing/`、`backend/app/domain/transport_rules.py`、`backend/app/contracts`、`backend/app/ports`、`frontend` 和任一冻结 benchmark 文件。没有 PostgreSQL 生产表迁移、写操作或原始实验重跑。

验证原始结果：`PYTHONPATH=backend python -m pytest -q backend/tests/test_pg_routing_preview.py backend/tests/test_contracts.py` = `23 passed`；`python scripts/export_contracts.py --check` = `Contracts match source`；`python scripts/check_project.py` 仅输出基线的 7 条 application→adapters 告警。`python -m compileall -q` exit 0。

环境限制：当前隔离机器无 psycopg、OR-Tools 及可联网安装能力；故模拟场景字段检查与 API 行为已测试，但不能声称真实 PostgreSQL 连通或真实 OR-Tools 路由计算已经在这里完成。真实端到端需 Windows 本机验证。仅保留必须的功能测试，不产生大规模新实验数据。
