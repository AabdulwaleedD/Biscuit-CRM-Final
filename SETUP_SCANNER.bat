@echo off
title Biscuit CRM - Scanner Setup
echo.
echo ================================================
echo   Biscuit CRM - QR Scanner Setup
echo ================================================
echo.
echo Installing required packages...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Installation failed. Try running this file from Anaconda Prompt.
    pause
    exit /b 1
)
echo.
echo Scanner dependencies are installed.
echo You can now run: streamlit run app.py
echo.
pause
