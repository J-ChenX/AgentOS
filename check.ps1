#!/usr/bin/env pwsh
# 本地 CI 检查脚本 — 与 GitHub Actions 保持一致
# 用法: .\check.ps1 [-py] [-web]
param(
    [switch]$py,
    [switch]$web
)

$ErrorActionPreference = "Stop"
$failed = @()

function Run($label, $cmd) {
    Write-Host "`n==> $label" -ForegroundColor Cyan
    Invoke-Expression $cmd
    if ($LASTEXITCODE -ne 0) { $script:failed += $label }
}

# 不带参数时全跑
$all = -not $py -and -not $web

if ($all -or $py) {
    Run "ruff format check" "python -m ruff format src/ tests/ --check"
    Run "ruff lint"         "python -m ruff check src/ tests/"
    Run "pytest"            "python -m pytest tests/ -q"
}

if ($all -or $web) {
    Run "prettier check"    "pnpm --filter web format:check"
    Run "eslint"            "pnpm --filter web lint"
    Run "vitest"            "pnpm --filter web exec vitest run"
}

if ($failed.Count -gt 0) {
    Write-Host "`n✗ 失败: $($failed -join ', ')" -ForegroundColor Red
    exit 1
} else {
    Write-Host "`n✓ 全部检查通过" -ForegroundColor Green
}
