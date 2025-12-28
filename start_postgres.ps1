# PowerShell script to start PostgreSQL for Clovio
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Starting PostgreSQL Database for Clovio" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is available
$dockerAvailable = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerAvailable) {
    Write-Host "[ERROR] Docker is not installed or not in PATH" -ForegroundColor Red
    Write-Host "[INFO] Please install Docker Desktop from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if container already exists
$existingContainer = docker ps -a --filter "name=clovio_db" --format "{{.Names}}" 2>&1
if ($existingContainer -eq "clovio_db") {
    Write-Host "[INFO] Container clovio_db already exists" -ForegroundColor Yellow
    Write-Host "[INFO] Starting existing container..." -ForegroundColor Yellow
    
    docker start clovio_db 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] PostgreSQL container started successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Database is ready at: postgresql://clovio_user:clovio_pass@localhost:5432/clovio_db" -ForegroundColor Green
        Write-Host ""
        Write-Host "You can now start your backend server." -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 0
    } else {
        Write-Host "[ERROR] Failed to start container" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "[INFO] Creating new PostgreSQL container..." -ForegroundColor Yellow
    
    docker run -d --name clovio_db `
        -e POSTGRES_USER=clovio_user `
        -e POSTGRES_PASSWORD=clovio_pass `
        -e POSTGRES_DB=clovio_db `
        -p 5432:5432 `
        postgres:15-alpine 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] PostgreSQL container created and started!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Waiting for database to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        Write-Host "[OK] Database is ready at: postgresql://clovio_user:clovio_pass@localhost:5432/clovio_db" -ForegroundColor Green
        Write-Host ""
        Write-Host "You can now start your backend server." -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 0
    } else {
        Write-Host "[ERROR] Failed to create container" -ForegroundColor Red
        Write-Host ""
        Write-Host "Make sure Docker is installed and running." -ForegroundColor Yellow
        Write-Host "Download Docker Desktop from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
}

