@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  python -m venv .venv
  .venv\Scripts\pip install -r requirements.txt -q
  .venv\Scripts\python manage.py migrate
)
.venv\Scripts\python manage.py runserver
pause
