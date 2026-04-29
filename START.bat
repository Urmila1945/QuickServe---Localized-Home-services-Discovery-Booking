@echo off
title QuickServe - Starting
color 0A

echo ========================================
echo    Starting QuickServe
echo ========================================
echo.

REM Start MongoDB
echo [1/3] Starting MongoDB...
sc query MongoDB | find "RUNNING" >nul
if errorlevel 1 (
    net start MongoDB >nul 2>&1
    if errorlevel 1 (
        echo [WARN] MongoDB not started. Run FIX.bat as Admin
    ) else (
        echo [OK] MongoDB started
    )
) else (
    echo [OK] MongoDB running
)
echo.

REM Start Backend
echo [2/3] Starting Backend (port 8000)...
start "QuickServe Backend" cmd /k "cd /d "%~dp0backend" && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
echo [OK] Backend starting...
echo.

REM Wait for backend
echo Waiting for backend to start...
timeout /t 5 >nul

REM Start Frontend
echo [3/3] Starting Frontend (port 5173)...
start "QuickServe Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"
echo [OK] Frontend starting...
echo.

echo ========================================
echo    QuickServe Started!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Login: admin@quickserve.com / admin123
echo.
echo Opening browser in 10 seconds...
timeout /t 10 >nul
start http://localhost:5173

echo.
echo Keep terminal windows open!
echo Run STOP.bat to stop servers.
pause
