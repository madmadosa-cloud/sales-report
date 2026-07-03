# -*- coding: utf-8 -*-
"""다른 PC·최초 실행 시 Python 패키지 준비."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def pip_install(*packages: str, quiet: bool = True) -> None:
    if getattr(sys, "frozen", False):
        return
    cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check"]
    if quiet:
        cmd.append("--quiet")
    cmd.extend(packages)
    subprocess.check_call(cmd)


def full_setup(quiet: bool = False) -> int:
    if not getattr(sys, "frozen", False):
        pip_install("pywebview", "openpyxl", "pillow", quiet=quiet)
    if not quiet:
        print()
        print("설치 완료. run_app.bat 으로 프로그램을 실행하세요.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="매출 분석 프로그램 환경 설정")
    parser.add_argument("--quiet", action="store_true", help="메시지 최소화 (bat에서 호출)")
    args = parser.parse_args()
    return full_setup(quiet=args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
