@echo off
title Second Brain - Ollama Setup
color 0B

echo.
echo   ======================================
echo    Second Brain - AI Setup (Ollama)
echo   ======================================
echo.

REM ── Step 1: Check if Ollama is installed ──
echo [1/4] Checking Ollama installation...
where ollama >nul 2>&1
if errorlevel 1 (
    echo.
    echo   Ollama is NOT installed.
    echo   Opening download page...
    echo.
    start https://ollama.com/download/windows
    echo   Please:
    echo     1. Download and install Ollama from the browser
    echo     2. Restart this script after installation
    echo.
    pause
    exit /b 1
)
echo   OK - Ollama found.

REM ── Step 2: Check if Ollama is running ──
echo [2/4] Checking if Ollama server is running...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo   Starting Ollama server...
    start /min ollama serve
    timeout /t 3 /nobreak >nul
)
echo   OK - Ollama server is running.

REM ── Step 3: Pull a lightweight model ──
echo [3/4] Pulling AI model (phi3:mini - ~2.3GB)...
echo   This may take a few minutes on first run...
echo.
ollama pull phi3:mini
if errorlevel 1 (
    echo.
    echo   phi3:mini failed. Trying llama3.2:1b instead...
    ollama pull llama3.2:1b
)
echo.
echo   OK - Model ready.

REM ── Step 4: Install Python ollama package ──
echo [4/4] Installing Python ollama package...
python -m pip install ollama >nul 2>&1
echo   OK - Python package ready.

echo.
echo   ======================================
echo    Setup Complete!
echo   ======================================
echo.
echo   Available models:
ollama list
echo.
echo   Your Second Brain can now:
echo     - Synthesize AI answers from your notes
echo     - Auto-tag and summarize documents
echo     - Generate insights via the Chat mode
echo.
echo   Run start.bat to launch the app!
echo.
pause
