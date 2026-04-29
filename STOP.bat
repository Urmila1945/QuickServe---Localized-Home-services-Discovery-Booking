@echo off
title QuickServe - Stopping Application
color 0C

echo ========================================
echo    QuickServe - Stopping Services
echo ========================================
echo.

echo Stopping Backend (Port 8000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo Backend stopped.

echo Stopping Frontend (Port 5173)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo Frontend stopped.

echo.
echo All services stopped successfully!
pause
