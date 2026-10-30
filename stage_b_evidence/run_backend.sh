#!/usr/bin/env bash
# Stage B 本地验收：启动隔离后端，只连接 5434 测试库，绝不触碰 5433 演示库。
#
# 前置：按 docs/implementation/STAGE_B_LOCAL_RUNBOOK_20261030.md 导出环境变量
#   DATABASE_URL / TEST_DATABASE_URL（同一个 5434 隔离库）
#   LOGISTICS_SETTINGS_JSON（mode / database_url / scope_id / credentials）
# 本文件刻意不包含任何口令，避免把本地凭据写进仓库历史。
set -euo pipefail

: "${DATABASE_URL:?请导出 DATABASE_URL（指向 5434 隔离测试库，勿用 5433 演示库）}"
: "${TEST_DATABASE_URL:?请导出 TEST_DATABASE_URL，Stage A 要求与 DATABASE_URL 指向同一库}"
: "${LOGISTICS_SETTINGS_JSON:?请导出 LOGISTICS_SETTINGS_JSON（格式见 RUNBOOK）}"

# uv 若不在 PATH，可用 UV_BIN_DIR 指定其所在目录。
command -v uv >/dev/null 2>&1 || export PATH="${UV_BIN_DIR:-$HOME/.local/bin}:$PATH"

API_PORT="${API_PORT:-8100}"
exec uv run uvicorn logistics_backend.main:create_app --factory \
  --host "${API_HOST:-127.0.0.1}" --port "$API_PORT"
