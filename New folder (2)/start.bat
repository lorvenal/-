@echo off
chcp 65001 >nul
title Cherry Selfbot
cd /d "%~dp0"

py -3.11 main.py

echo.
echo 
echo  
echo
pause