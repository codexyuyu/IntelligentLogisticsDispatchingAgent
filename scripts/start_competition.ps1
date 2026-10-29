param([switch]$SkipBuild, [switch]$SkipSeed)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    docker info --format '{{.ServerVersion}}'
    if ($LASTEXITCODE -ne 0) { throw '请先启动 Docker Desktop 的 Linux 引擎。' }
    $composeArgs = @('compose', 'up', '-d', '--wait', '--wait-timeout', '180')
    if (-not $SkipBuild) { $composeArgs += '--build' }
    & docker @composeArgs
    if ($LASTEXITCODE -ne 0) { throw '服务构建或启动失败；使用 docker compose logs 查看原因。' }
    if (-not $SkipSeed) {
        docker compose --profile tools run --rm seed
        if ($LASTEXITCODE -ne 0) { throw '演示数据导入失败。' }
    }
    Write-Host '比赛入口：http://localhost:8080/'
    Write-Host '本地演示登录令牌：dev-operator-token'
    Write-Host '联合调度：协商记录 → 加载合成测试样本 → 校验并导入 → 计算。'
} finally { Pop-Location }
