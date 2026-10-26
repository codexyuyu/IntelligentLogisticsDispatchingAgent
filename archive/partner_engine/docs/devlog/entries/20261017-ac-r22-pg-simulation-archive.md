# 2026-10-17 · AC · R22 PG 模拟结果独立归档

## 新需求与事实

用户确认 R21 本机 4 接口成功并上传了实际 POST /route 的返回截图（`代码.docx`）：HTTP 200，R20 `ROUTING_SOLUTION`，独立校验 `passed`，`unserved_orders=[]`；用户明确优先开发功能、尽量少做实验。

## 实际修改

新增 AC-owned `backend/app/adapters/persistence/pg_simulation_archive.py`、单独 DDL `backend/sql/pg_simulation_previews.sql`、显式初始化 `backend/tools/setup_pg_simulation_archive.py`、本机可选启动脚本 `backend/start_pg_r22_local.ps1`；扩展 AC API `backend/app/api/routes/postgres_demo.py`，增加本机模拟归档保存/列表/详情/geojson/地图；主应用仅改本机子应用描述。新增文档和小型回归测试。

**安全承诺**：请求由后端重新读库并运行既有求解器，独立校验通过、无漏单、订单覆盖数正确才允许写一条归档；用户提交的路线结果不接受。数据**只写**新独立 `public.pg_simulation_previews`，老 `dispatch_plans/routes/route_stops` 不动。旧 R21 PowerShell 仍只读。保留 `simulation_only_not_executable` 与所有模拟假设，不允许“确认”为业务方案。

## 约束与治理

不修改 B 求解器、原合同、OpenAPI 主应用、前端生成 TS 和冻结历史实验。新增路由仍保留在 localhost 子应用。单一顶层目录 ZIP。用户本机 PostgreSQL 实际保存还没有在本环境验证；只可宣称测试替身下的事务语义、API 安全和数据结构检查。

## 本轮测试和未完成

本环境运行 `python -m pytest -q tests/test_pg_simulation_archive.py tests/test_pg_routing_preview.py tests/test_contracts.py tests/test_scaffold.py` → **38 passed**；`compileall` 通过；`python scripts/export_contracts.py --check` → Contracts match source；`scripts/check_project.py` 仅 7 条历史 application→adapters 告警。待办：用户 Windows 本机的一次 POST save / GET saved / map 验收；正式仓储资源与道路时长、合法 business PlanCommit、React 正式页面均未完成。不做规模测试。
