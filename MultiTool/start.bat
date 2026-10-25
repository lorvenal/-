@echo off
chcp 65001 >nul
title Multi-Account Tool
cd /d "%~dp0"

echo ═══════════════════════════════════════════════════════════
echo   Multi-Account Tool
echo ═══════════════════════════════════════════════════════════
echo.

REM ─── تحقق من Python ───
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python مو مثبت!
    echo.
    echo نزّله من: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM ─── تحقق من aiohttp ───
python -c "import aiohttp" >nul 2>&1
if errorlevel 1 (
    echo ⚠️ مكتبة aiohttp مو مثبتة
    echo.
    echo جاري التثبيت...
    python -m pip install aiohttp
    echo.
)

REM ─── تحقق من الملفات ───
if not exist "accounts.json" (
    echo ❌ ما لقيت accounts.json
    echo.
    pause
    exit /b 1
)

if not exist "tasks.json" (
    echo ❌ ما لقيت tasks.json
    echo.
    pause
    exit /b 1
)

REM ─── تشغيل ───
python main.py

echo.
echo ═══════════════════════════════════════════════════════════
echo   انتهى
echo ═══════════════════════════════════════════════════════════
pause