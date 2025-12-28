@echo off
echo ==========================================
echo Starting PostgreSQL Database for Clovio
echo ==========================================
echo.

REM Check if container already exists
docker ps -a --filter "name=clovio_db" --format "{{.Names}}" | findstr /C:"clovio_db" >nul
if %errorlevel% == 0 (
    echo [INFO] Container clovio_db already exists
    echo [INFO] Starting existing container...
    docker start clovio_db
    if %errorlevel% == 0 (
        echo [OK] PostgreSQL container started successfully!
        echo.
        echo Database is ready at: postgresql://clovio_user:clovio_pass@localhost:5432/clovio_db
        echo.
        pause
        exit /b 0
    ) else (
        echo [ERROR] Failed to start container
        pause
        exit /b 1
    )
) else (
    echo [INFO] Creating new PostgreSQL container...
    docker run -d --name clovio_db -e POSTGRES_USER=clovio_user -e POSTGRES_PASSWORD=clovio_pass -e POSTGRES_DB=clovio_db -p 5432:5432 postgres:15-alpine
    if %errorlevel% == 0 (
        echo [OK] PostgreSQL container created and started!
        echo.
        echo Waiting for database to be ready...
        timeout /t 5 /nobreak >nul
        echo [OK] Database is ready at: postgresql://clovio_user:clovio_pass@localhost:5432/clovio_db
        echo.
        echo You can now start your backend server.
        echo.
        pause
        exit /b 0
    ) else (
        echo [ERROR] Failed to create container
        echo.
        echo Make sure Docker is installed and running.
        echo Download Docker Desktop from: https://www.docker.com/products/docker-desktop
        echo.
        pause
        exit /b 1
    )
)

