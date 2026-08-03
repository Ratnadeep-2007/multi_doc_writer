@echo off
title Solar Docs Web App Starter
echo ==============================================
echo  Starting Solar Docs Auto-Fill Web App...
echo ==============================================
echo.
cd /d "%~dp0"

echo [1/3] Checking dependencies...
python -c "import flask, docxtpl" 2>nul
if %errorlevel% neq 0 (
    echo Python dependencies not found. Installing docxtpl and flask...
    python -m pip install docxtpl flask
) else (
    echo Dependencies are already satisfied.
)

echo.
echo [2/3] Starting Flask local server in background...
start "" /b python app.py

echo.
echo [3/3] Opening web browser...
timeout /t 2 >nul
start http://127.0.0.1:5001

echo.
echo Server is running on http://127.0.0.1:5001
echo Close this window to stop the server.
echo ==============================================
pause
