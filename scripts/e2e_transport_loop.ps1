param([switch]$Keep)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$db = "dsh_browser_e2e"
$url = "postgresql+psycopg://test:test@127.0.0.1:55432/$db"
$scope = "11111111-1111-4111-8111-111111111111"
$credential = "22222222-2222-4222-8222-222222222222"
$tokenHash = "277e6a75a6980887d1bc5c738e59a2504e3e2696d8f9fbf675b7fc49dabd2cf8"
$settings = @{
  mode = "production"
  database_url = $url
  scope_id = $scope
  credentials = @(@{ actor_id = $credential; role = "operator"; token_sha256 = $tokenHash })
  bind_host = "127.0.0.1"
  bind_port = 8000
} | ConvertTo-Json -Compress

$backend = $null
$worker = $null
$vite = $null
$logDir = Join-Path $root "tmp/e2e-transport"
New-Item -ItemType Directory -Force $logDir | Out-Null

function Wait-Http([string]$Url, [int]$Seconds = 60) {
  for ($i = 0; $i -lt $Seconds; $i++) {
    try { if ((Invoke-WebRequest -UseBasicParsing $Url -TimeoutSec 2).StatusCode -eq 200) { return } } catch {}
    Start-Sleep -Seconds 1
  }
  throw "timeout waiting for $Url"
}

try {
  docker exec dsh-p03-test pg_isready -U test -d test | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "isolated PostgreSQL dsh-p03-test is not ready" }

  docker exec dsh-p03-test psql -U test -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$db';" | Out-Null
  docker exec dsh-p03-test psql -U test -d postgres -c "DROP DATABASE IF EXISTS $db;" | Out-Null
  docker exec dsh-p03-test psql -U test -d postgres -c "CREATE DATABASE $db;" | Out-Null

  $env:DATABASE_URL = $url
  $env:LOGISTICS_DATABASE_URL = $url
  $env:LOGISTICS_SETTINGS_JSON = $settings
  .\.venv\Scripts\alembic.exe upgrade head
  if ($LASTEXITCODE -ne 0) { throw "alembic failed" }
  .\.venv\Scripts\python.exe -m logistics_backend.cli.seed --scenario tiny_master
  if ($LASTEXITCODE -ne 0) { throw "seed failed" }

  docker compose stop frontend backend worker | Out-Null

  $backend = Start-Process -FilePath "$root\.venv\Scripts\python.exe" -ArgumentList @(
    "-m","uvicorn","logistics_backend.main:create_app","--factory","--host","127.0.0.1","--port","8000"
  ) -WorkingDirectory $root -RedirectStandardOutput "$logDir/backend.log" -RedirectStandardError "$logDir/backend.err.log" -PassThru
  $worker = Start-Process -FilePath "$root\.venv\Scripts\python.exe" -ArgumentList @(
    "-m","logistics_backend.worker"
  ) -WorkingDirectory $root -RedirectStandardOutput "$logDir/worker.log" -RedirectStandardError "$logDir/worker.err.log" -PassThru

  $vite = Start-Process -FilePath "cmd.exe" -ArgumentList @(
    "/c","npm run dev -- --host 127.0.0.1 --port 8081"
  ) -WorkingDirectory "$root\apps\frontend" -RedirectStandardOutput "$logDir/vite.log" -RedirectStandardError "$logDir/vite.err.log" -PassThru

  Wait-Http "http://127.0.0.1:8000/api/v1/health" 60
  Wait-Http "http://127.0.0.1:8081/" 60

  $env:PLAYWRIGHT_BASE_URL = "http://127.0.0.1:8081"
  $env:PLAYWRIGHT_CHANNEL = "chrome"
  npx playwright test apps/frontend/e2e/transport-loop.spec.ts --reporter=list
  if ($LASTEXITCODE -ne 0) { throw "browser E2E failed" }

  $row = docker exec dsh-p03-test psql -U test -d $db -t -A -F "|" -c "SELECT id, version_no, status FROM schedule_versions ORDER BY created_at DESC LIMIT 1;"
  if (-not $row) { throw "no committed version found in isolated database" }
  "isolated_db_version=$row" | Tee-Object -FilePath "$logDir/db-verification.txt"
  "settings_scope=$scope" | Add-Content "$logDir/db-verification.txt"
} finally {
  if ($vite -and -not $vite.HasExited) { taskkill /PID $vite.Id /T /F | Out-Null }
  if ($worker -and -not $worker.HasExited) { Stop-Process -Id $worker.Id -Force -ErrorAction SilentlyContinue }
  if ($backend -and -not $backend.HasExited) { Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue }
  docker compose up -d backend worker frontend | Out-Null
  if (-not $Keep) {
    docker exec dsh-p03-test psql -U test -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$db';" | Out-Null
    docker exec dsh-p03-test psql -U test -d postgres -c "DROP DATABASE IF EXISTS $db;" | Out-Null
  }
}
