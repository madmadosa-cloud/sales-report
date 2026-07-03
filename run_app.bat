@echo off
setlocal
pushd "%~dp0"
title Sales Analysis App

set "PYEXE="
where py >nul 2>&1 && set "PYEXE=py -3"
if not defined PYEXE where python >nul 2>&1 && set "PYEXE=python"

if not defined PYEXE (
    echo [ERROR] Python not found.
    echo Install from https://www.python.org
    echo Check Add Python to PATH during install.
    pause
    exit /b 1
)

echo Starting desktop app...
echo.

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :17890 ^| findstr LISTENING') do (
    echo Stopping old app server PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

%PYEXE% -u "%~dp0setup_env.py" --quiet
%PYEXE% -u "%~dp0app_launcher.py"
if errorlevel 1 pause

popd
endlocal
