# R29: read-only preflight by default. Explicit migration never edits historical routes.
param([switch]$Apply, [switch]$BackupVerified, [int]$ExpectedHistoricalRoutes = 4)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:PGHOST = '127.0.0.1'
$env:PGPORT = '5432'
$env:PGDATABASE = 'coldchain_db'
$env:PGUSER = 'postgres'
$secret = Read-Host '请输入 PostgreSQL 密码（不会回显）' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try { $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
try {
  if (-not $Apply) {
    Write-Host 'R29 只读预检：检查两仓外键，不修改任何表或路线。'
    python -m tools.pg_r29_active_warehouse --expect-routes $ExpectedHistoricalRoutes
  } else {
    if (-not $BackupVerified) { throw '先执行备份并确认备份可读取，再使用 -Apply -BackupVerified' }
    $code = Read-Host '输入 WH001 确认统一四辆现役车并保留历史路线'
    if ($code -cne 'WH001') { throw '确认失败，未进行迁移' }
    Write-Host 'R29 正在原子事务内迁移：历史 routes / route_stops 不会更新或删除。'
    python -m tools.pg_r29_active_warehouse --apply --confirm WH001 --backup-verified --expect-routes $ExpectedHistoricalRoutes
  }
  if ($LASTEXITCODE -ne 0) { throw 'R29 操作失败；若为事务失败，Python 将回滚。请提供上方错误。' }
} finally {
  Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
