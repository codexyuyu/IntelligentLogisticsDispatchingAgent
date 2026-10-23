# 主数据、数据库、API、作业实现范围

依据：用户在本会话要求不考虑分工，今天推进主数据模型、数据库、后端 API、作业执行，按工作区文件要求，只补代码、不运行测试。本轮按此最新授权连续编写相关任务实现，不将跨阶段代码编写等同于跨 Gate 验收。

精确范围：P02-02/P03-01/P05-01/P05-02/P05-03 的 manifest 实现文件；P02-04 runtime/common 与 P03-02 runtime_models/0002_planning_runtime、P03-03 uow、P03-04 idempotency 为必需依赖。P02-03 全部计划实体、P02-04 仿真事件、P03 完整计划版本存储和 P04 场景不因此自动标记完成。按需要逐项实现，报告明确缺项。

依赖扩展白名单：apps/backend/pyproject.toml 和 uv.lock，增加 SQLAlchemy 2、Alembic 1、psycopg 3，锁文件仅由 uv lock 生成。这是 P03 必需的 PostgreSQL 持久化依赖，不升级已有开发工具。

domain → DTO → persistence → application → API → worker；业务 schema 仍为 2.0.0。无旧实体数据库可迁移，数据库迁移脚本只生成不执行。不接用户实际数据库。未启用求解/仿真等真实 handler 时拒绝入队，不生成成功替身。

影响：新增候选与依赖使旧相关证据需要独立影响审查；不更新旧记录哈希、不冒写 Gate/precheck/review，不承诺历史通过自动适用。回滚按新增迁移 downgrade 与本轮文件清单实施。测试、数据库迁移实跑、HTTP/worker 运行均 NOT_RUN；version_id/parent_version_id/snapshot_hash 留给相应后续规划任务，不伪造。
