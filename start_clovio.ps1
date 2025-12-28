# PowerShell script to start Clovio application
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Starting Clovio Application" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env exists, if not create it with SQLite default
$envFile = "backend\.env"
if (-not (Test-Path $envFile)) {
    Write-Host "[INFO] Creating .env file with SQLite configuration..." -ForegroundColor Yellow
    @"
USE_SQLITE=true
DATABASE_URL=sqlite:///./clovio.db
"@ | Out-File -FilePath $envFile -Encoding utf8
    Write-Host "[OK] Created .env file" -ForegroundColor Green
}

# Start backend
Write-Host ""
Write-Host "Starting backend server..." -ForegroundColor Yellow
Set-Location backend
python start_backend.py
Set-Location ..

Read-Host "Press Enter to exit"

