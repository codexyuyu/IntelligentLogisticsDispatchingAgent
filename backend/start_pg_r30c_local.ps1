# R30-C DeepSeek + R27/R30B local-only and read-only Demo.
# Usage: powershell -ExecutionPolicy Bypass -File .\start_pg_r30c_local.ps1 -DemoOnly
# No persistent secrets; prompts do not echo credentials or include them in command history.
param([switch]$DemoOnly)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:PG_DEMO_ENABLED = '1'
$env:PG_PREVIEW_WRITE_ENABLED = '0'
$env:DEEPSEEK_BASE_URL = 'https://api.deepseek.com'
if (-not $env:DEEPSEEK_MODEL) { $env:DEEPSEEK_MODEL = 'deepseek-flash' }
if (-not $DemoOnly) {
  $env:PGHOST = '127.0.0.1'
  $env:PGPORT = '5432'
  $env:PGDATABASE = 'coldchain_db'
  $env:PGUSER = 'postgres'
}
function Read-LocalSecret([string]$Prompt) {
  $secret = Read-Host $Prompt -AsSecureString
  $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
  try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}
try {
  if (-not $DemoOnly -and -not $env:PGPASSWORD) {
    $env:PGPASSWORD = Read-LocalSecret '请输入 PostgreSQL 密码（仅当前进程使用）'
  }
  if (-not $env:DEEPSEEK_API_KEY) {
    $env:DEEPSEEK_API_KEY = Read-LocalSecret '请输入 DeepSeek API Key（仅当前进程使用，不会回显）'
  }
  Write-Host 'R30-C DeepSeek Agent + CP-SAT / OR-Tools + R30-B read-only preview'
  Write-Host 'DemoOnly=' $DemoOnly '；仅监听 127.0.0.1，不执行正式出库/派车，不写数据库。'
  Write-Host 'AI 接口状态：http://127.0.0.1:8000/local-pg/pg-preview/r30c/status'
  Write-Host '前端启动：cd ..\frontend; npm ci; npm run dev'
  if ($DemoOnly) { Write-Host '当前不连接 PostgreSQL；请选择前端内置单仓合成演示场景。' }
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
} finally {
  Remove-Item Env:PGPASSWORD,Env:DEEPSEEK_API_KEY,Env:PG_DEMO_ENABLED,Env:PG_PREVIEW_WRITE_ENABLED -ErrorAction SilentlyContinue
}
