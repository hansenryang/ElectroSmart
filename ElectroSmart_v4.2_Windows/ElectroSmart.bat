@echo off
setlocal enabledelayedexpansion
echo ================================
echo ElectroSmart Launcher
echo ================================
:: Always move to BAT directory
cd /d "%~dp0"

echo.
echo [1/4] Verifying Python path...
where python
if errorlevel 1 (
    echo ERROR: Python was not found.
    echo Please install Python and make sure it is available from Command Prompt.
    pause
    exit /b 1
)

echo.
echo [2/4] Installing/updating dependencies...
python -m pip install --upgrade pip
if exist "requirements.txt" (
    python -m pip install -r requirements.txt
) else (
    echo WARNING: requirements.txt not found
    python -m pip install streamlit pandas numpy matplotlib scipy galvani openpyxl
)
if errorlevel 1 (
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
)

echo.
echo [3/4] Shortcut setup...
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
echo [4/4] Launching Streamlit app...
python -m streamlit run app.py --server.port 8501
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo Streamlit exited with code %EXIT_CODE%
pause
endlocal
