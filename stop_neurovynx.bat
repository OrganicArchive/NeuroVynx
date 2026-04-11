@echo off
TITLE NeuroVynx Process Cleaner
SETLOCAL

echo.
echo ===================================================
echo   NeuroVynx: Terminating Local Server Processes
echo ===================================================
echo.

:: 1. Backend Clean (8000)
echo [BACKEND] Searching for process on port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo [FORCE] Killing PID %%a
    taskkill /F /PID %%a /T 2>nul
)

:: 2. Frontend Clean (5173)
echo [FRONTEND] Searching for process on port 5173...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do (
    echo [FORCE] Killing PID %%a
    taskkill /F /PID %%a /T 2>nul
)

echo.
echo [SUCCESS] Ports 8000 and 5173 have been cleared.
echo ===================================================
echo.
pause
