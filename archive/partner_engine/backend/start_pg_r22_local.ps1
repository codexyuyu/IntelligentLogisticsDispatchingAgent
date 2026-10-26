# R22 simulation archive. Explicit opt-in; only localhost. Does not change original dispatch plan tables.
param([switch]$CreateDemoTable)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:PG_DEMO_ENABLED = '1'
$env:PG_PREVIEW_WRITE_ENABLED = '1'
$env:PGHOST = '127.0.0.1'
$env:PGPORT = '5432'
$env:PGDATABASE = 'coldchain_db'
$env:PGUSER = 'postgres' # Local demonstration only; use least-privilege user for real deployment.
$secret = Read-Host '请输入 PostgreSQL 密码' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try { $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
try {
    if ($CreateDemoTable) {
        Write-Host '显式创建独立演示表 public.pg_simulation_previews（不修改原调度方案表）'
        python -m tools.setup_pg_simulation_archive --create-demo-table
        if ($LASTEXITCODE -ne 0) { throw '演示表初始化失败，请查看上方错误' }
    }
    Write-Host 'R22 本机模拟调度归档：http://127.0.0.1:8000/local-pg/docs'
    Write-Host '仅保存独立模拟方案，不会写入 dispatch_plans/routes/route_stops'
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
} finally {
    Remove-Item Env:PGPASSWORD, Env:PG_DEMO_ENABLED, Env:PG_PREVIEW_WRITE_ENABLED -ErrorAction SilentlyContinue
}
