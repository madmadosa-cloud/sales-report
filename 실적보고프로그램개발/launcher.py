#!/usr/bin/env python
"""
매출분석 프로그램 Windows 실행기 (PyInstaller 진입점)

- Django 개발 서버를 127.0.0.1 에서 기동
- 최초 실행 시 DB 마이그레이션·시드 자동 처리
- 기본 웹 브라우저 자동 실행
"""

from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _prepare_environment() -> Path:
    if getattr(sys, "frozen", False):
        data_dir = Path(sys.executable).resolve().parent
        os.chdir(data_dir)
    else:
        data_dir = Path(__file__).resolve().parent
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sales_report.settings")
    return data_dir


def _run_server(host: str, port: int) -> None:
    from django.core.management import execute_from_command_line

    execute_from_command_line(
        ["launcher.py", "runserver", f"{host}:{port}", "--noreload", "--insecure"]
    )


def main() -> int:
    data_dir = _prepare_environment()

    import django

    django.setup()

    from sales_report.bootstrap import configure_logging, ensure_runtime_dirs, initialize_database

    ensure_runtime_dirs()
    configure_logging()
    print("매출분석 프로그램을 시작합니다...")
    print(f"데이터 저장 위치: {data_dir}")
    print("데이터베이스를 확인하는 중...")
    initialize_database()

    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}/"

    server_thread = threading.Thread(
        target=_run_server,
        args=(host, port),
        name="django-server",
        daemon=True,
    )
    server_thread.start()

    for _ in range(40):
        time.sleep(0.25)
        try:
            import urllib.request

            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    break
        except OSError:
            continue
    else:
        print("서버 시작 대기 시간이 초과되었습니다. 로그를 확인하세요.")
        print(f"수동으로 브라우저에서 {url} 을(를) 열어보세요.")

    print(f"브라우저를 엽니다: {url}")
    if not os.environ.get("PACKAGING_TEST"):
        webbrowser.open(url)

    print()
    print("=" * 50)
    print(" 프로그램이 실행 중입니다.")
    print(" 종료하려면 이 창을 닫거나 Ctrl+C 를 누르세요.")
    print("=" * 50)
    print()

    try:
        while server_thread.is_alive():
            server_thread.join(timeout=1)
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
