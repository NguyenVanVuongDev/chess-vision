$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Chua co .venv. Tao moi truong truoc." -ForegroundColor Yellow
    exit 1
}
if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Host "Chua cai cloudflared hoac cloudflared chua co trong PATH." -ForegroundColor Yellow
    exit 1
}

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $PSScriptRoot "start-backend.ps1")
)

Start-Sleep -Seconds 3

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $PSScriptRoot "start-cloudflared.ps1")
)

Write-Host "Da khoi dong backend va Cloudflare Tunnel trong hai cua so rieng." -ForegroundColor Green
