@echo off
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
  echo [INFO] Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create venv. Install Python 3.11+ and try again.
    pause
    exit /b 1
  )
)

echo [INFO] Installing packages...
call .venv\Scripts\pip install -r requirements.txt -q
call .venv\Scripts\pip install -r requirements-build.txt -q

echo [INFO] Building exe... (may take several minutes)
call .venv\Scripts\python build_support\build.py
if errorlevel 1 (
  echo [ERROR] Build failed.
  pause
  exit /b 1
)

echo.
echo [OK] Done. Deploy: dist\매출분석프로그램_배포.zip
pause
