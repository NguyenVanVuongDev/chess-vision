$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Host "Khong tim thay cloudflared trong PATH." -ForegroundColor Yellow
    exit 1
}

Write-Host "Dang chay Named Tunnel chess-vision toi http://127.0.0.1:8000" -ForegroundColor Green
& cloudflared tunnel run chess-vision
