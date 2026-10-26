# R26 WH002 -> WH001 migration preflight: read-only unless explicit Apply and BackupVerified.
param([switch]$Apply, [switch]$BackupVerified)
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
    Write-Host 'R26 只读预检：不修改仓库、车辆或调度方案'
    python -m tools.pg_r26_single_warehouse
  } else {
    if (-not $BackupVerified) { throw '必须先用 pg_dump / pgAdmin 完整备份并校验；再同时指定 -Apply -BackupVerified' }
    $code = Read-Host '输入 WH001 确认将旧仓 WH002 合并至 WH001'
    if ($code -cne 'WH001') { throw '仓库代码确认失败，未进行迁移' }
    python -m tools.pg_r26_single_warehouse --apply --confirm WH001 --backup-verified
  }
  if ($LASTEXITCODE -ne 0) { throw 'R26 单仓检查或迁移失败；请查看上方原因。' }
} finally {
  Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
