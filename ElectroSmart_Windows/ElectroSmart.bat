@echo off
setlocal
cd /d "%~dp0"
echo Zirong-ECM
if not defined ELECTROSMART_PORT set "ELECTROSMART_PORT=8502"
if not exist "ElectroSmartEnv\Scripts\python.exe" (
    python -m venv ElectroSmartEnv
    if errorlevel 1 exit /b 1
    "ElectroSmartEnv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 exit /b 1
)
"ElectroSmartEnv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --server.port %ELECTROSMART_PORT% --browser.gatherUsageStats false
pause
endlocal
