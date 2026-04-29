@echo off
title MongoDB Starter
color 0E

echo Checking MongoDB status...
sc query MongoDB | find "RUNNING" >nul

if errorlevel 1 (
    echo MongoDB is not running. Starting MongoDB...
    net start MongoDB
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to start MongoDB!
        echo.
        echo Please run this command as Administrator:
        echo   net start MongoDB
        echo.
        echo Or start MongoDB manually from Services.
        pause
        exit /b 1
    )
    echo MongoDB started successfully!
) else (
    echo MongoDB is already running!
)

echo.
echo MongoDB is ready!
timeout /t 2
