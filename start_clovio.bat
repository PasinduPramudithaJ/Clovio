@echo off
echo ==========================================
echo Starting Clovio Application
echo ==========================================
echo.

REM Check if .env exists, if not create it with SQLite default
if not exist backend\.env (
    echo [INFO] Creating .env file with SQLite configuration...
    echo USE_SQLITE=true > backend\.env
    echo DATABASE_URL=sqlite:///./clovio.db >> backend\.env
    echo [OK] Created .env file
)

REM Start backend
echo.
echo Starting backend server...
cd backend
python start_backend.py
cd ..

pause

