$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Chua co moi truong Python .venv." -ForegroundColor Yellow
    Write-Host "Chay: python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements-web.txt"
    exit 1
}

Write-Host "Chess Vision backend dang chay tai http://127.0.0.1:8000" -ForegroundColor Green
& $python -m uvicorn web.server:app --host 127.0.0.1 --port 8000 --reload
