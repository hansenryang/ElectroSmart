@echo off
setlocal enabledelayedexpansion
echo ================================
echo ElectroSmart Launcher
echo ================================
:: Always move to BAT directory
cd /d "%~dp0"
echo.
echo [1/6] Checking virtual environment...
:: Create venv if missing
if not exist "ElectroSmartEnv\Scripts\python.exe" (
    echo Virtual environment not found. Creating...
    python -m venv ElectroSmartEnv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)
echo.
echo [2/6] Activating environment...
call "ElectroSmartEnv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)
echo.
echo [3/6] Verifying Python path...
where python
echo.
echo [4/6] Installing/updating dependencies...
set "PY=%~dp0ElectroSmartEnv\Scripts\python.exe"
"%PY%" -m pip install --upgrade pip
if exist "requirements.txt" (
    "%PY%" -m pip install -r requirements.txt
) else (
    echo WARNING: requirements.txt not found
    "%PY%" -m pip install streamlit pandas numpy matplotlib scipy galvani
)
echo.
echo [5/6] Shortcut setup...
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\ElectroSmart.lnk"
set "TARGET_PATH=%~dp0ElectroSmart.bat"
set "ICON_PATH=%~dp0Logo.ico"
if not exist "%SHORTCUT_PATH%" (
    echo Creating shortcut...
        powershell -NoProfile -ExecutionPolicy Bypass -Command "$W=New-Object -ComObject WScript.Shell; $L=$W.CreateShortcut('%SHORTCUT_PATH%'); $L.TargetPath='%TARGET_PATH%'; $L.WorkingDirectory='%~dp0'; $L.IconLocation='%ICON_PATH%,0'; $L.Save()"
        if exist "%SHORTCUT_PATH%" (
            echo Shortcut created successfully.
        ) else (
            echo WARNING: Shortcut creation failed (non-fatal^)
        )
) else (
    echo Shortcut already exists.
)
echo.
echo [6/6] Launching Streamlit app...
"%PY%" -m streamlit run app.py
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo Streamlit exited with code %EXIT_CODE%
pause
endlocal