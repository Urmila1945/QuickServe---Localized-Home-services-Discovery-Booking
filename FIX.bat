@echo off
title QuickServe - Setup & Fix
color 0B

echo ========================================
echo    QuickServe - Setup & Fix
echo ========================================
echo.

REM Check Python
echo [1/6] Checking Python...
python --version 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Install from: https://www.python.org/
    pause
    exit /b 1
)
echo [OK] Python installed
echo.

REM Check Node.js
echo [2/6] Checking Node.js...
node --version 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js not found!
    echo Install from: https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Node.js installed
echo.

REM Start MongoDB
echo [3/6] Starting MongoDB...
sc query MongoDB | find "RUNNING" >nul
if errorlevel 1 (
    net start MongoDB >nul 2>&1
    if errorlevel 1 (
        echo [WARN] Run as Administrator to start MongoDB
        echo Or manually: net start MongoDB
    ) else (
        echo [OK] MongoDB started
    )
) else (
    echo [OK] MongoDB running
)
echo.

REM Clear ports
echo [4/6] Clearing ports...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING 2^>nul') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING 2^>nul') do taskkill /F /PID %%a >nul 2>&1
echo [OK] Ports cleared
echo.

REM Install backend dependencies
echo [5/6] Installing backend dependencies...
cd backend
pip install -q -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install backend dependencies
    pause
    exit /b 1
)
echo [OK] Backend dependencies installed

REM Create admin user
echo Creating admin user...
python create_admin.py
cd ..
echo.

REM Install frontend dependencies
echo [6/6] Installing frontend dependencies...
cd frontend
if not exist node_modules (
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install frontend dependencies
        pause
        exit /b 1
    )
)
echo [OK] Frontend dependencies installed
cd ..
echo.

echo ========================================
echo    Setup Complete!
echo ========================================
echo.
echo Next: Run START.bat to launch the app
echo.
pause
