#!/usr/bin/env bash
# Stage B 本地验收环境变量模板（占位符，请按本机实际情况替换后 source）。
#   用法：cp stage_b_evidence/env_stage_b.example.sh stage_b_evidence/.env.local
#         source stage_b_evidence/.env.local      # 该文件已被 .gitignore 忽略
#
# 完整说明见 docs/implementation/STAGE_B_LOCAL_RUNBOOK_20261030.md。
# 硬约束：一律使用 5434 隔离测试库，5433 演示库保持停止、不可连接。

# 5434 隔离 PostgreSQL（本机 cc_test_pg 容器映射）
export STAGE_B_PG_HOST="127.0.0.1"
export STAGE_B_PG_PORT="5434"
export STAGE_B_PG_USER="<填本机测试库用户名>"
export STAGE_B_PG_PASSWORD="<填本机测试库口令>"
export STAGE_B_PG_DB="logistics_stage_a_test"

export DATABASE_URL="postgresql+psycopg://${STAGE_B_PG_USER}:${STAGE_B_PG_PASSWORD}@${STAGE_B_PG_HOST}:${STAGE_B_PG_PORT}/${STAGE_B_PG_DB}"
# Stage A 的 alembic 用 DATABASE_URL，pytest 用 TEST_DATABASE_URL，二者必须同指隔离库。
export TEST_DATABASE_URL="$DATABASE_URL"

# 后端 Settings JSON（LOGISTICS_SETTINGS_JSON）。
# token_sha256 必须是所使用 API Key 的 sha256；验证方式见 RUNBOOK。
export LOGISTICS_SETTINGS_JSON='{"mode":"development","database_url":"<同上 DATABASE_URL>","scope_id":"11111111-1111-4111-8111-111111111111","credentials":[{"actor_id":"22222222-2222-4222-8222-222222222222","role":"operator","token_sha256":"<API Key 的 sha256>"}],"bind_host":"127.0.0.1","bind_port":8000}'

# 隔离后端端口（避开演示环境的 8000）
export API_PORT="8100"
# uv 可执行文件所在目录（不在 PATH 时使用）
export UV_BIN_DIR="<uv 所在目录，可留空>"

# UI 验收脚本
export STAGE_B_BASE_URL="http://localhost:5199"      # vite dev server（注意用 localhost）
export STAGE_B_API_TOKEN="< operator 角色 API Key >"
export CHROME_PATH="<本机 Chrome 可执行文件绝对路径>"

# 前端 dev server 代理目标（指向上面的隔离后端）
export VITE_API_PROXY="http://127.0.0.1:${API_PORT}"
