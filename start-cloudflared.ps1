$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Host "Khong tim thay cloudflared trong PATH." -ForegroundColor Yellow
    Write-Host "Cai bang: winget install Cloudflare.cloudflared"
    exit 1
}

Write-Host "Tunnel se mo cong 8000. Hay copy URL https://...trycloudflare.com trong output." -ForegroundColor Green
& cloudflared tunnel --url http://127.0.0.1:8000
