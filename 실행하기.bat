@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ====================================
echo   ���� �м� ���α׷� ����
echo ====================================
echo.

rem ���̽� ����� ã�� (py �켱, ������ python)
set "PYEXE="
where py >nul 2>nul && set "PYEXE=py"
if not defined PYEXE where python >nul 2>nul && set "PYEXE=python"

if not defined PYEXE (
    echo [����] ���̽��� ��ġ�Ǿ� ���� �ʽ��ϴ�.
    echo https://www.python.org ���� Python �� ���� ��ġ�ϼ���.
    echo ��ġ �� "Add Python to PATH" �� �� üũ�ϼ���.
    pause
    exit /b 1
)

echo �ʼ� ���̺귯�� Ȯ��/��ġ ��... (pandas, openpyxl)
%PYEXE% -m pip install --quiet --disable-pip-version-check pandas openpyxl

echo ���α׷��� �����մϴ�...
%PYEXE% "����м����α׷�.py"

echo.
echo (â�� �������ϴ�. ������ ������ �� �޽����� Ȯ���ϼ���.)
pause
