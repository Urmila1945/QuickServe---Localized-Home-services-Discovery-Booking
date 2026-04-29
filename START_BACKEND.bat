@echo off
echo Starting QuickServe Backend...
cd /d "%~dp0backend"

echo Checking Python installation...
python --version
if errorlevel 1 (
    echo Python not found! Please install Python 3.8+
    pause
    exit /b 1
)

echo Installing/updating dependencies...
pip install -r requirements.txt

echo Starting FastAPI server...
python -m uvicorn app_monolith:app --host 0.0.0.0 --port 8000 --reload

pause