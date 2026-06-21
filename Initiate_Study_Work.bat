@echo off
title Skill Enhancer Boot Sequence
echo [System] Initializing Tactical Study Platform...
echo ==================================================

:: 1. Dynamically navigate to the directory where this batch file is located
cd /d "%~dp0"

:: 2. Verify Python is installed and accessible
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [CRITICAL ERROR] Python is not detected on this system.
    echo.
    echo Please install Python to use this platform.
    echo 1. Go to python.org and download the latest Windows installer.
    echo 2. When installing, YOU MUST CHECK THE BOX that says:
    echo    "Add python.exe to PATH" at the bottom of the first screen.
    echo.
    pause
    exit /b
)

:: 3. Automatically install missing modules from requirements.txt
echo [System] Verifying necessary modules...
python -m pip install -r requirements.txt --quiet --disable-pip-version-check

:: 4. Launch the server directly in this command window
echo [System] Environment stable. Handing over to Core Code...
echo ==================================================
python core_code.py

echo [System] Server offline.
pause