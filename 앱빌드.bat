@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 매출분석 EXE 빌드 (배포용)

echo ================================================
echo   매출분석 EXE 빌드 — 다른 PC 배포용
echo   (Python + 인터넷 필요, 5~10분)
echo ================================================
echo.

call "%~dp0build_app.bat"

