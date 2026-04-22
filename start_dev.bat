@echo off
chcp 65001 >nul
title Semantic Generator Dev
color 0A

echo.
echo ============================================
echo   Starting Backend and Frontend...
echo ============================================
echo.

cd /d "%~dp0"

REM Kill old processes
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
timeout /t 2

REM Start npm dev
echo Starting npm run dev...
npm run dev

pause







