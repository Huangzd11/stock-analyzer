# Stock Analyzer Web 服务启动脚本（PowerShell）
# 用法:
#   .\scripts\start.ps1
#   .\scripts\start.ps1 -Port 8080 -Reload

param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "[错误] 未找到虚拟环境 .venv" -ForegroundColor Red
    Write-Host "请先执行:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv"
    Write-Host "  .venv\Scripts\pip install -e `".[dev]`""
    Write-Host "  .venv\Scripts\pip install -e `".[ml]`"   # 可选：深度学习预测"
    exit 1
}

if (-not (Test-Path (Join-Path $Root ".env"))) {
    $example = Join-Path $Root ".env.example"
    if (Test-Path $example) {
        Copy-Item $example (Join-Path $Root ".env")
        Write-Host "[提示] 已从 .env.example 创建 .env" -ForegroundColor Yellow
    }
}

$uvicornArgs = @(
    "-m", "uvicorn",
    "stock_analyzer.interface.api.app:app",
    "--host", $BindHost,
    "--port", "$Port"
)
if ($Reload) {
    $uvicornArgs += "--reload"
}

Write-Host ""
Write-Host " Stock Analyzer 正在启动..." -ForegroundColor Cyan
Write-Host " 控制台: http://${BindHost}:${Port}/" -ForegroundColor Green
Write-Host " API 文档: http://${BindHost}:${Port}/docs" -ForegroundColor Green
Write-Host " 按 Ctrl+C 停止服务" -ForegroundColor DarkGray
Write-Host ""

& $Python @uvicornArgs
