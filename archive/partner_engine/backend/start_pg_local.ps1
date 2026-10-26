# 仅供本机开发：只读 PostgreSQL + R20 运输求解模拟预览。
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:PG_DEMO_ENABLED = '1'
$env:PGHOST = '127.0.0.1'
$env:PGPORT = '5432'
$env:PGDATABASE = 'coldchain_db'
$env:PGUSER = 'postgres'  # 建议后续换专用只读账号
$secret = Read-Host '请输入 PostgreSQL 密码' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try { $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
Write-Host '启动本机数据库只读演示 API: http://127.0.0.1:8000/local-pg/docs'
Write-Host '可访问 /local-pg/pg-preview/summary, /orders, /vehicles 和 POST /route'
try {
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
} finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:PG_DEMO_ENABLED -ErrorAction SilentlyContinue
}
