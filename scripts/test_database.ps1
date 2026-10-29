param(
    [switch]$SetupOnly,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$PytestArgs
)
# docker compose 会把无害警告写到 stderr；用 Continue 避免被当成终止错误，失败一律看 $LASTEXITCODE。
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
$testUrl = 'postgresql+psycopg://logistics:logistics@127.0.0.1:5433/logistics_test'
Push-Location $root
try {
    docker compose up -d --wait db
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL 容器未就绪；请先启动 Docker Desktop 的 Linux 引擎。' }

    $exists = docker compose exec -T db psql -U logistics -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='logistics_test'"
    if ("$exists".Trim() -ne '1') {
        docker compose exec -T db psql -U logistics -d postgres -c 'CREATE DATABASE logistics_test'
        if ($LASTEXITCODE -ne 0) { throw '创建 logistics_test 失败。' }
    }

    $env:DATABASE_URL = $testUrl
    & .\.venv\Scripts\alembic.exe upgrade head
    if ($LASTEXITCODE -ne 0) { throw '测试库迁移失败。' }

    $env:TEST_DATABASE_URL = $testUrl
    if ($SetupOnly -or $PytestArgs.Count -eq 0) {
        Write-Host "测试库就绪：$testUrl"
        Write-Host '运行测试：.\scripts\test_database.ps1 tests/integration -q'
        return
    }

    & .\.venv\Scripts\python.exe -m pytest @PytestArgs
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
