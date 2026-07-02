@echo off
cd /d "%~dp0"

if not exist .env (
  if exist .env.example (
    echo [INFO] Copying .env.example to .env
    copy /Y .env.example .env >nul
    echo [INFO] Edit .env and set DJANGO_SECRET_KEY, then run this file again.
    pause
    exit /b 1
  )
)

if not exist .venv\Scripts\python.exe (
  echo [INFO] Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create venv. Install Python 3.11+ and try again.
    pause
    exit /b 1
  )
  call .venv\Scripts\pip install -r requirements.txt -q
  call .venv\Scripts\python manage.py migrate
)

echo [INFO] Starting server...
start "SalesReportServer" /D "%~dp0" cmd /k .venv\Scripts\python.exe manage.py runserver

ping 127.0.0.1 -n 3 >nul
start "" http://127.0.0.1:8000/

echo.
echo [OK] Browser opened: http://127.0.0.1:8000/
echo [INFO] Close the "SalesReportServer" window to stop the server.
pause
