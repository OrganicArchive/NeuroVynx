@echo off
TITLE NeuroVynx Control Center
SETLOCAL EnableExtensions EnableDelayedExpansion

:: Force working directory to the script's location
cd /d "%~dp0"

echo.
echo ===================================================
echo   NeuroVynx: High-Fidelity EEG Analysis Platform
echo ===================================================
echo.

:: 1. Check for Python presence
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 goto :no_python

:: 2. Check Python Version (3.9+)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "pyver=%%v"
for /f "delims=. tokens=1,2" %%a in ("%pyver%") do (
    set major=%%a
    set minor=%%b
)
set /a is_old=0
if %major% LSS 3 set /a is_old=1
if %major% EQU 3 if %minor% LSS 9 set /a is_old=1

if %is_old% EQU 1 goto :old_python

:check_venv
:: 3. Setup Virtual Environment (The "Correct Environment")
if not exist ".venv" (
    echo [!] Virtual environment not found. Creating one now...
    python -m venv .venv
    if !ERRORLEVEL! NEQ 0 (
        echo [ERROR] Failed to create .venv. 
        pause & exit /b
    )
    echo [SUCCESS] Virtual environment created in .venv folder.
)

:: Define absolute path to the virtual environment's python
set "PY_EXEC=%~dp0.venv\Scripts\python.exe"

:: 4. Check for Node.js
node --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 goto :no_node

:: 5. Verify folders exist
if not exist "backend" (
    echo [ERROR] 'backend' folder not found. Please run this from the root.
    pause & exit /b
)
if not exist "frontend" (
    echo [ERROR] 'frontend' folder not found. Please run this from the root.
    pause & exit /b
)

:: 6. Check for Frontend Dependencies
if exist "frontend\node_modules" goto :check_backend

echo [!] Frontend dependencies (node_modules) are missing.
set /p install_front="Would you like to run 'npm install' now? (y/n): "
if /i "!install_front!"=="y" (
    echo [INSTALL] Installing frontend dependencies...
    cd /d frontend && npm install
    cd /d "%~dp0"
) else (
    echo.
    echo [MANUAL STEPS] To fix this later:
    echo 1. Open a terminal in 'frontend'
    echo 2. Run: npm install
    echo.
    pause & exit /b
)

:check_backend
:: 7. Check for Backend Dependencies (using the venv)
"!PY_EXEC!" -c "import mne" >nul 2>&1
if !ERRORLEVEL! EQU 0 goto :launch

echo [!] Backend dependencies appear to be missing in the virtual environment.
set /p install_back="Would you like to run 'pip install -r backend/requirements.txt' now? (y/n): "
if /i "!install_back!"=="y" (
    echo [INSTALL] Installing backend dependencies...
    "!PY_EXEC!" -m pip install -r backend/requirements.txt
) else (
    echo.
    echo [MANUAL STEPS] To fix this later:
    echo 1. Run: .venv\Scripts\pip install -r backend/requirements.txt
    echo.
    pause & exit /b
)

:launch
:: 8. Launch Backend
echo [SERVER] Starting FastAPI Backend on 127.0.0.1:8000...
start "NeuroVynx Backend" cmd /k "cd /d "%~dp0backend" && "!PY_EXEC!" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

:: 9. Launch Frontend
echo [SERVER] Starting Vite Frontend on localhost:5173...
start "NeuroVynx Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

:: 10. Open Browser
echo [BROWSER] Waiting for servers to initialize...
timeout /t 5 /nobreak > nul
start http://localhost:5173

echo.
echo [SUCCESS] Both servers are booting in separate windows.
echo [INFO] Python is running from the local .venv.
echo.
echo To stop everything, close the server windows or run stop_neurovynx.bat
echo.
pause
exit /b

:no_python
echo [!] Python not found in PATH.
echo Python 3.9+ is required to run this application.
echo.
set /p do_install="Would you like to install Python 3.11 now via winget? (y/n): "
if /i "!do_install!"=="y" (
    echo.
    echo [INSTALL] Attempting to install Python 3.11 via winget...
    winget install --id Python.Python.3.11 --exact --source winget
    if !ERRORLEVEL! NEQ 0 (
        echo.
        echo [ERROR] Automatic installation failed. 
        echo Please install Python 3.9+ manually from https://www.python.org/downloads/
        pause & exit /b
    )
    echo.
    echo [SUCCESS] Python installation initiated. 
    echo IMPORTANT: Please CLOSE this window and RE-RUN this script once the installer finishes.
    pause & exit /b
) else (
    echo [ERROR] Python is required. Setup aborted.
    pause & exit /b
)

:old_python
echo [!] Your Python version (%pyver%) is too old. 3.9+ is required.
echo.
set /p do_up="Would you like to install a compatible version (Python 3.11) now? (y/n): "
if /i "!do_up!"=="y" (
    echo.
    echo [INSTALL] Installing Python 3.11...
    winget install --id Python.Python.3.11 --exact --source winget
    echo [SUCCESS] Installation initiated. Please RESTART this script once finished.
    pause & exit /b
) else (
    echo [ERROR] Version requirement not met. Setup aborted.
    pause & exit /b
)

:no_node
echo [!] Node.js not found in PATH.
echo Node.js 18+ is required to run the frontend.
echo.
set /p do_node="Would you like to install Node.js (LTS) now via winget? (y/n): "
if /i "!do_node!"=="y" (
    echo.
    echo [INSTALL] Attempting to install Node.js LTS via winget...
    winget install --id OpenJS.NodeJS.LTS --exact --source winget
    if !ERRORLEVEL! NEQ 0 (
        echo.
        echo [ERROR] Automatic installation failed. 
        echo Please install Node.js manually from https://nodejs.org/
        pause & exit /b
    )
    echo.
    echo [SUCCESS] Node.js installation initiated. 
    echo IMPORTANT: Please CLOSE this window and RE-RUN this script once finished.
    pause & exit /b
) else (
    echo [ERROR] Node.js is required. Setup aborted.
    pause & exit /b
)

