@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Build EXE



set "PYEXE="

where py >nul 2>nul && set "PYEXE=py"

if not defined PYEXE where python >nul 2>nul && set "PYEXE=python"



if not defined PYEXE (

    echo [ERROR] Python is not installed.

    pause

    exit /b 1

)



"%PYEXE%" "%~dp0build_app.py"

pause

