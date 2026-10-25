@echo off
chcp 65001 >nul
title Cherry Selfbot - تثبيت المكتبات
cd /d "%~dp0"

echo ═══════════════════════════════════════════════════════════
echo   Cherry Selfbot - تثبيت المكتبات
echo ═══════════════════════════════════════════════════════════
echo.

REM ─── تأكد من Python 3.11 ───
echo [1/3] التحقق من Python 3.11...
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 3.11 مو مثبت!
    echo نزّله من: https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    pause
    exit /b 1
)
echo ✅ Python 3.11 موجود
echo.

REM ─── حدّث pip ───
echo [2/3] تحديث pip...
py -3.11 -m pip install --upgrade pip --quiet
echo ✅ تم
echo.

REM ─── ثبّت المكتبات من requirements.txt ───
echo [3/3] تثبيت المكتبات...
py -3.11 -m pip install -r requirements.txt
echo.
echo ✅ تم التثبيت
echo.
echo 💡 الحين شغّل البوت من start.bat
pause