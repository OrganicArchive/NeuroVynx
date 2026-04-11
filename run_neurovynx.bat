@echo off
TITLE NeuroVynx Control Center
SETLOCAL EnableExtensions

:: Force working directory to the script's location
cd /d "%~dp0"

echo.
echo ===================================================
echo   NeuroVynx: High-Fidelity EEG Analysis Platform
echo ===================================================
echo.

:: 1. Check for Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found in PATH. Please install Python 3.9+ 
    echo or ensure it is added to your environment variables.
    pause
    exit /b
)

:: 2. Check for Node.js
node --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js not found in PATH. Please install Node.js 18+
    echo or ensure it is added to your environment variables.
    pause
    exit /b
)

:: 3. Verify folders exist
if not exist "backend" (
    echo [ERROR] 'backend' folder not found. Please run this from the root.
    pause
    exit /b
)
if not exist "frontend" (
    echo [ERROR] 'frontend' folder not found. Please run this from the root.
    pause
    exit /b
)

:: 4. Check for Frontend Dependencies
if exist "frontend\node_modules" goto :check_backend

echo [!] Frontend dependencies (node_modules) are missing.
set /p install_front="Would you like to run 'npm install' now? (y/n): "
if /i "%install_front%"=="y" (
    echo [INSTALL] Installing frontend dependencies...
    cd /d frontend && npm install
    cd /d "%~dp0"
) else (
    echo.
    echo [MANUAL STEPS] To fix this later:
    echo 1. Open a terminal in 'frontend'
    echo 2. Run: npm install
    echo.
    pause
    exit /b
)

:check_backend
:: 5. Check for Backend Dependencies (Check for 'mne' as a proxy)
python -c "import mne" >nul 2>&1
if %ERRORLEVEL% EQU 0 goto :launch

echo [!] Backend dependencies (e.g., mne) appear to be missing.
set /p install_back="Would you like to run 'pip install -r backend/requirements.txt' now? (y/n): "
if /i "%install_back%"=="y" (
    echo [INSTALL] Installing backend dependencies...
    python -m pip install -r backend/requirements.txt
) else (
    echo.
    echo [MANUAL STEPS] To fix this later:
    echo 1. Open a terminal in 'backend'
    echo 2. Run: pip install -r requirements.txt
    echo.
    pause
    exit /b
)

:launch
:: 6. Launch Backend
echo [SERVER] Starting FastAPI Backend on localhost:8000...
start "NeuroVynx Backend" cmd /k "cd /d "%~dp0backend" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: 7. Launch Frontend
echo [SERVER] Starting Vite Frontend on localhost:5173...
start "NeuroVynx Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

:: 8. Open Browser
echo [BROWSER] Waiting for servers to initialize...
timeout /t 5 /nobreak > nul
start http://localhost:5173

echo.
echo [SUCCESS] Both servers are booting in separate windows.
echo Keep those windows open while using the application.
echo.
pause
