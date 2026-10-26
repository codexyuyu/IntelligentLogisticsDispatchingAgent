# R30-B: read-only PostgreSQL source and event-driven suffix forecast.
# No DB migrations, archive writes, order fulfillment writes, or fleet commands.
param([string]$OsrmBaseUrl = '')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:PG_DEMO_ENABLED = '1'
$env:PG_PREVIEW_WRITE_ENABLED = '0'
$env:PGHOST = '127.0.0.1'
$env:PGPORT = '5432'
$env:PGDATABASE = 'coldchain_db'
$env:PGUSER = 'postgres'
if ($OsrmBaseUrl -ne '') { $env:OSRM_BASE_URL = $OsrmBaseUrl }
$secret = Read-Host '请输入 PostgreSQL 密码（只读异常预览）' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try { $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
try {
  Write-Host 'R30-B 单仓 WH001 / PostgreSQL → CP-SAT → OR-Tools → 异常后缀只读预览'
  Write-Host '本启动脚本禁用 R22 演示归档写入，不新建或修改数据库表。'
  Write-Host '接口文档 http://127.0.0.1:8000/local-pg/docs'
  if (-not $env:OSRM_BASE_URL) { Write-Host 'OSRM 未启用：直线距离与示意路线不能作为真实道路。' }
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
} finally {
  Remove-Item Env:PGPASSWORD,Env:PG_DEMO_ENABLED,Env:PG_PREVIEW_WRITE_ENABLED,Env:OSRM_BASE_URL -ErrorAction SilentlyContinue
}
