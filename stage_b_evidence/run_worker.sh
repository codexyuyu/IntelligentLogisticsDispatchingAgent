#!/usr/bin/env bash
# Stage B 本地验收：作业 worker（处理联合调度 / 运输求解等异步 job）。
# 与 run_backend.sh 使用同一套环境变量，详见 STAGE_B_LOCAL_RUNBOOK_20261030.md。
# 本文件刻意不包含任何口令。
set -euo pipefail

: "${DATABASE_URL:?请导出 DATABASE_URL（指向 5434 隔离测试库）}"
: "${LOGISTICS_SETTINGS_JSON:?请导出 LOGISTICS_SETTINGS_JSON}"

command -v uv >/dev/null 2>&1 || export PATH="${UV_BIN_DIR:-$HOME/.local/bin}:$PATH"

# 必须有 worker 领取 job，否则 integration run 会以
# dependency_unavailable / job deadline or attempt limit reached 失败。
exec uv run python -m logistics_backend.worker
