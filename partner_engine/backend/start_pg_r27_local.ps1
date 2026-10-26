# R27 local closed-loop simulator. Existing R21/22 launchers remain available.
param([switch]$CreateR24Tables, [switch]$CreateR27Tables, [string]$OsrmBaseUrl = '')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:PG_DEMO_ENABLED = '1'
$env:PG_PREVIEW_WRITE_ENABLED = '1'
$env:PGHOST = '127.0.0.1'
$env:PGPORT = '5432'
$env:PGDATABASE = 'coldchain_db'
$env:PGUSER = 'postgres' # local only; use separate least-privilege account in deployment
if ($OsrmBaseUrl -ne '') { $env:OSRM_BASE_URL = $OsrmBaseUrl }
$secret = Read-Host '请输入 PostgreSQL 密码' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try { $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
try {
  if ($CreateR24Tables) {
    Write-Host '首次显式创建 R24 冷链扩展表（不回写现有业务表）'
    python -m tools.setup_pg_r24 --create-tables
    if ($LASTEXITCODE -ne 0) { throw 'R24 增量建表失败，服务未启动' }
  }
  if ($CreateR27Tables) {
    Write-Host '显式创建 R27 作业工时扩展表（不写入模拟数据）'
    python -m tools.setup_pg_r27 --create-tables
    if ($LASTEXITCODE -ne 0) { throw 'R27 增量建表失败，服务未启动' }
  }
  Write-Host 'R27 PostgreSQL + CP-SAT + OR-Tools + 3D 本地调度台 http://127.0.0.1:8000/local-pg/docs'
  if (-not $env:OSRM_BASE_URL) { Write-Host '未配置 OSRM_BASE_URL，OSRM 模式将明确报错，旧直线模拟仍可用。' }
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
} finally {
  Remove-Item Env:PGPASSWORD,Env:PG_DEMO_ENABLED,Env:PG_PREVIEW_WRITE_ENABLED,Env:OSRM_BASE_URL -ErrorAction SilentlyContinue
}
