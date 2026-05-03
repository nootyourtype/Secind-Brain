@echo off
title Second Brain
color 0B

echo.
echo   ==============================
echo    Second Brain - Starting Up
echo   ==============================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

REM Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

echo [1/3] Starting Python backend...
start "Second Brain - Backend" /min cmd /c "python main.py"

echo [2/3] Waiting for API server...
timeout /t 6 /nobreak >nul

echo [3/3] Starting React dashboard...
cd web
start "Second Brain - Dashboard" /min cmd /c "npm run dev"
cd ..

timeout /t 3 /nobreak >nul

echo.
echo   ==============================
echo    Second Brain is LIVE!
echo   ==============================
echo.
echo   Backend API:   http://127.0.0.1:8000
echo   Dashboard:     http://localhost:5173
echo   System Tray:   Check your taskbar
echo.
echo   Press any key to open the dashboard...
pause >nul

start http://localhost:5173
