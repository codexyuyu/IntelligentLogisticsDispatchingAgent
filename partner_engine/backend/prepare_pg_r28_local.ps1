# R28 read-only inventory and empty CSV worklist export; never changes PostgreSQL.
param([string]$OutputDirectory = '')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:PGHOST='127.0.0.1'
$env:PGPORT='5432'
$env:PGDATABASE='coldchain_db'
$env:PGUSER='postgres'
$secret = Read-Host '请输入 PostgreSQL 密码（仅用于只读诊断）' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try { $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
try {
  if ($OutputDirectory -eq '') {
    python -m tools.pg_r28_prepare
  } else {
    python -m tools.pg_r28_prepare --output $OutputDirectory
  }
  if ($LASTEXITCODE -ne 0) { throw 'R28 只读诊断或 CSV 生成失败；请检查错误报告' }
} finally { Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue }
