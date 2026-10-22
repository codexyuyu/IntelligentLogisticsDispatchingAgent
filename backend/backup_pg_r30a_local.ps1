# R30-A local PG backup. Produces pg_dump custom archive and checks TOC is readable.
param([string]$OutputDirectory = '')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command pg_dump -ErrorAction SilentlyContinue)) {
  foreach ($candidate in @('D:\postgresql\17\bin', 'C:\Program Files\PostgreSQL\17\bin')) {
    if (Test-Path (Join-Path $candidate 'pg_dump.exe')) { $env:PATH = "$candidate;$env:PATH"; break }
  }
}
if (-not (Get-Command pg_dump -ErrorAction SilentlyContinue)) {
  throw '找不到 pg_dump。请安装 PostgreSQL 命令行工具，或使用 pgAdmin 的 Backup 自定义格式；先验证备份，再执行 R30-A 扩展资料导入。'
}
if (-not (Get-Command pg_restore -ErrorAction SilentlyContinue)) {
  throw '找不到 pg_restore。请配置 PostgreSQL bin 到 PATH，并验证备份可读取。'
}
$env:PGHOST = '127.0.0.1'
$env:PGPORT = '5432'
$env:PGDATABASE = 'coldchain_db'
$env:PGUSER = 'postgres'
if (-not $OutputDirectory) { $OutputDirectory = (Join-Path $PSScriptRoot '..\r30a_backups') }
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$now = Get-Date -Format 'yyyyMMdd_HHmmss'
$file = Join-Path (Resolve-Path $OutputDirectory).Path ("coldchain_db_before_R30A_" + $now + '.dump')
if (Test-Path -LiteralPath $file) { throw '备份目标已存在；请勿覆盖' }
$secret = Read-Host '请输入 PostgreSQL 密码（不会回显）' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try { $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
try {
  & pg_dump --format=custom --no-owner --no-acl --file=$file --dbname=coldchain_db
  if ($LASTEXITCODE -ne 0) { throw 'pg_dump 失败；未完成备份' }
  & pg_restore --list $file | Out-Null
  if ($LASTEXITCODE -ne 0) { throw 'pg_restore 无法读取备份目录；未通过备份检查' }
  $size = (Get-Item -LiteralPath $file).Length
  if ($size -lt 512) { throw '备份文件异常小，请检查' }
  $hash = Get-FileHash -LiteralPath $file -Algorithm SHA256
  Write-Host '备份文件：' $file
  Write-Host '文件字节：' $size
  Write-Host 'SHA256：' $hash.Hash
  Write-Host '已验证归档目录可读取。注意：这不等于实际恢复演练；有条件时请另库恢复验证。'
  Write-Host '此备份保存在本机，请妥善保存，不要上传含敏感业务数据的 dump。'
} finally {
  Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
