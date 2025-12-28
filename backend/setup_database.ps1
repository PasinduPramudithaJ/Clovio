# PowerShell script for Windows to set up PostgreSQL database
# This script creates the database and user if they don't exist

param(
    [string]$DB_NAME = "clovio_db",
    [string]$DB_USER = "clovio_user",
    [string]$DB_PASSWORD = "clovio_pass",
    [string]$DB_HOST = "localhost",
    [int]$DB_PORT = 5432,
    [string]$PG_PASSWORD = "postgres"  # PostgreSQL superuser password
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Clovio Database Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Database: $DB_NAME"
Write-Host "User: $DB_USER"
Write-Host "Host: ${DB_HOST}:${DB_PORT}"
Write-Host "==========================================" -ForegroundColor Cyan

# Check if psql is available
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue
if (-not $psqlPath) {
    Write-Host "ERROR: psql command not found. Please ensure PostgreSQL client tools are installed." -ForegroundColor Red
    Write-Host "You can download PostgreSQL from: https://www.postgresql.org/download/" -ForegroundColor Yellow
    exit 1
}

# Set PostgreSQL password environment variable
$env:PGPASSWORD = $PG_PASSWORD

# Check if PostgreSQL is accessible
Write-Host ""
Write-Host "Checking PostgreSQL connection..." -ForegroundColor Yellow
try {
    $result = psql -h $DB_HOST -p $DB_PORT -U postgres -c "SELECT version();" 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Connection failed"
    }
    Write-Host "[OK] PostgreSQL server is accessible" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Cannot connect to PostgreSQL server" -ForegroundColor Red
    Write-Host "Please ensure PostgreSQL is running and accessible" -ForegroundColor Yellow
    Write-Host "Connection string: postgresql://postgres@${DB_HOST}:${DB_PORT}/postgres" -ForegroundColor Yellow
    exit 1
}

# Create user if it doesn't exist
Write-Host ""
Write-Host "Creating user '$DB_USER' if it doesn't exist..." -ForegroundColor Yellow
$userExists = psql -h $DB_HOST -p $DB_PORT -U postgres -tAc "SELECT 1 FROM pg_user WHERE usename = '$DB_USER'"
if ([string]::IsNullOrWhiteSpace($userExists)) {
    psql -h $DB_HOST -p $DB_PORT -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" | Out-Null
    Write-Host "[OK] User '$DB_USER' created" -ForegroundColor Green
} else {
    Write-Host "[OK] User '$DB_USER' already exists" -ForegroundColor Green
}

# Create database if it doesn't exist
Write-Host ""
Write-Host "Creating database '$DB_NAME' if it doesn't exist..." -ForegroundColor Yellow
$dbExists = psql -h $DB_HOST -p $DB_PORT -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'"
if ([string]::IsNullOrWhiteSpace($dbExists)) {
    psql -h $DB_HOST -p $DB_PORT -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" | Out-Null
    Write-Host "[OK] Database '$DB_NAME' created" -ForegroundColor Green
} else {
    Write-Host "[OK] Database '$DB_NAME' already exists" -ForegroundColor Green
}

# Grant privileges
Write-Host ""
Write-Host "Granting privileges..." -ForegroundColor Yellow
psql -h $DB_HOST -p $DB_PORT -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" | Out-Null
psql -h $DB_HOST -p $DB_PORT -U postgres -d $DB_NAME -c "GRANT ALL ON SCHEMA public TO $DB_USER;" | Out-Null
Write-Host "[OK] Privileges granted" -ForegroundColor Green

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Database setup complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "You can now run the application with:" -ForegroundColor Yellow
Write-Host "  python main.py" -ForegroundColor White
Write-Host "  or" -ForegroundColor White
Write-Host "  uvicorn main:app --reload" -ForegroundColor White
Write-Host ""

# Clear password from environment
Remove-Item Env:\PGPASSWORD

