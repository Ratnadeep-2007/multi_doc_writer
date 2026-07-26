@echo off
title Solar Docs CLI Runner (Sample 2)
echo ==============================================
echo  Running Solar Docs CLI Generator on Sample 2...
echo ==============================================
echo.
cd /d "%~dp0"

echo [1/3] Checking dependencies...
python -c "import docxtpl" 2>nul
if %errorlevel% neq 0 (
    echo Python dependencies not found. Installing docxtpl...
    python -m pip install docxtpl
) else (
    echo Dependencies are already satisfied.
)

echo.
echo [2/3] Generating documents from sample_input_2.json...
python generate_docs.py sample_input_2.json

echo.
echo [3/3] Opening output folder...
timeout /t 2 >nul
if exist "output\ASHISH_JAYVANT_RANE" (
    explorer "output\ASHISH_JAYVANT_RANE"
) else (
    explorer "output"
)

echo.
echo Finished generating sample 2 documents!
echo ==============================================
pause
