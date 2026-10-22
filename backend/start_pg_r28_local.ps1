# R28 local read-only business preview. No automatic migrations or data seeding.
param([switch]$CreateR24Tables, [switch]$CreateR27Tables, [string]$OsrmBaseUrl = '')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:PG_DEMO_ENABLED = '1'
$env:PG_PREVIEW_WRITE_ENABLED = '1' # Only the existing R22 explicitly confirmed simulated archive.
$env:PGHOST = '127.0.0.1'
$env:PGPORT = '5432'
$env:PGDATABASE = 'coldchain_db'
$env:PGUSER = 'postgres' # local demo only; production should use a least-privileged role
if ($OsrmBaseUrl -ne '') { $env:OSRM_BASE_URL = $OsrmBaseUrl }
$secret = Read-Host '请输入 PostgreSQL 密码' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try { $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
try {
  if ($CreateR24Tables) {
    Write-Host '显式安装 R24 冷链扩展表（不修改原业务表）'
    python -m tools.setup_pg_r24 --create-tables
    if ($LASTEXITCODE -ne 0) { throw 'R24 增量建表失败；服务未启动' }
  }
  if ($CreateR27Tables) {
    Write-Host '显式安装 R27 仓储工时表（不导入任何模拟业务数据）'
    python -m tools.setup_pg_r27 --create-tables
    if ($LASTEXITCODE -ne 0) { throw 'R27 增量建表失败；服务未启动' }
  }
  Write-Host 'R28 单仓调度 + 订单对账 + 实库诊断： http://127.0.0.1:8000/local-pg/docs'
  Write-Host 'R28 默认只读核对；原历史数据、正式方案与库存均不自动改写。'
  if (-not $env:OSRM_BASE_URL) { Write-Host '未配置 OSRM；仍可使用明确标识的模拟道路回放。' }
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
} finally {
  Remove-Item Env:PGPASSWORD,Env:PG_DEMO_ENABLED,Env:PG_PREVIEW_WRITE_ENABLED,Env:OSRM_BASE_URL -ErrorAction SilentlyContinue
}
