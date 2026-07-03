@echo off
setlocal
pushd "%~dp0"
title Restart Sales Analysis App

echo Stopping old app server on port 17890...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :17890 ^| findstr LISTENING') do (
    echo   taskkill PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

timeout /t 2 /nobreak >nul
call "%~dp0run_app.bat"
popd
endlocal
