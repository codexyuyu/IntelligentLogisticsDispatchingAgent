# R27 optional CSV import: prompts for password; does not change DB unless explicitly approved.
param([Parameter(Mandatory=$true)][string]$CsvPath,
      [switch]$Apply,[switch]$BackupVerified)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$fullCsv = (Resolve-Path $CsvPath).Path
if ($Apply -and -not $BackupVerified) { throw '数据库写入需先备份并指定 -BackupVerified' }
if ($Apply) {
  $confirm = Read-Host '确认输入 WH001 才能导入到 R27 扩展表'
  if ($confirm -ne 'WH001') { throw '确认失败；未写数据库' }
}
$env:PGHOST = '127.0.0.1'
$env:PGPORT = '5432'
$env:PGDATABASE = 'coldchain_db'
$env:PGUSER = 'postgres'
if ($Apply) {
  $secret = Read-Host '请输入 PostgreSQL 密码' -AsSecureString
  $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
  try { $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}
try {
  if ($Apply) {
    python -m tools.pg_r27_import --csv $fullCsv --apply --backup-verified --confirm WH001
  } else {
    python -m tools.pg_r27_import --csv $fullCsv
  }
  if ($LASTEXITCODE -ne 0) { throw 'R27 CSV 校验/导入失败；检查提示，事务将回滚' }
} finally {
  Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
