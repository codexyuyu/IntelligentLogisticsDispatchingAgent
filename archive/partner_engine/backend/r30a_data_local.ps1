# R30-A synthetic demo extension data: generate/verify/opt-in import.
param(
  [switch]$Apply,
  [switch]$Validate,
  [switch]$CreateR27Tables,
  [switch]$BackupVerified,
  [string]$BundleDirectory = ''
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:PGHOST = '127.0.0.1'
$env:PGPORT = '5432'
$env:PGDATABASE = 'coldchain_db'
$env:PGUSER = 'postgres'
if (-not $BundleDirectory) { $BundleDirectory = Join-Path $PSScriptRoot '..\r30a_synthetic_data' }
$secret = Read-Host '请输入 PostgreSQL 密码（不会回显）' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try { $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
try {
  if ($CreateR27Tables) {
    if ($Apply -or $Validate) { throw '建表、校验和数据导入不能组合执行' }
    if (-not $BackupVerified) { throw '新增 R27 作业表前需先备份，并指定 -BackupVerified' }
    $confirmation = Read-Host '显式新增一张 R27 空作业表（不删除旧数据），确认请输入 WH001'
    if ($confirmation -cne 'WH001') { throw '确认码不匹配，没有建表' }
    python -m tools.setup_pg_r27 --create-tables
  } elseif ($Apply) {
    if (-not $BackupVerified) { throw '请先备份当前 coldchain_db 并验证归档，再指定 -BackupVerified' }
    Write-Host '注意：这将向现有 R24/R27 扩展表写入明确标注为【合成演示】的数据。不是实际业务数据！'
    $confirmation = Read-Host '确实理解并同意写入合成演示数据，请输入 DEMO_WH001'
    if ($confirmation -cne 'DEMO_WH001') { throw '确认码不匹配，没有执行导入' }
    python -m tools.pg_r30a_bundle --bundle $BundleDirectory --apply --backup-verified --confirm DEMO_WH001
  } elseif ($Validate) {
    python -m tools.pg_r30a_bundle --bundle $BundleDirectory
  } else {
    Write-Host '默认只读：基于本机真实订单/车辆编号生成【合成演示】扩展 CSV，不修改数据库。'
    python -m tools.pg_r30a_bundle --output $BundleDirectory
  }
  if ($LASTEXITCODE -ne 0) { throw 'R30-A 数据准备/校验失败；请保留错误日志，不要跳过检查' }
} finally { Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue }
