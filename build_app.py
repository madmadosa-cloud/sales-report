# -*- coding: utf-8 -*-
"""PyInstaller로 EXE 배포 폴더(dist + 배포용) 생성."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_NAME = "매출분석"


def find_html() -> Path:
    for name in ("매출분석.html", "sales_app.html"):
        p = HERE / name
        if p.exists():
            return p
    htmls = sorted(HERE.glob("*.html"), key=lambda p: p.stat().st_size, reverse=True)
    if not htmls:
        raise SystemExit("매출분석.html 파일을 찾을 수 없습니다.")
    return htmls[0]


def pip_install(*packages: str) -> None:
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-q", "--disable-pip-version-check", *packages]
    )


def prepare_deploy_extras(target: Path) -> None:
    """배포 폴더에 사용자용 폴더·안내·실행 배치를 추가."""
    (target / "저장데이터").mkdir(exist_ok=True)
    (target / "다운로드").mkdir(exist_ok=True)
    readme_data = target / "저장데이터" / "여기에_데이터가_저장됩니다.txt"
    readme_data.write_text(
        "이 폴더는 프로그램이 자동으로 사용합니다.\n"
        "삭제하지 마세요. 다른 PC로 옮길 때 이 폴더를 통째로 복사하세요.\n",
        encoding="utf-8",
    )
    run_bat = target / "실행.bat"
    run_bat.write_text(
        "@echo off\n"
        "chcp 65001 >nul\n"
        "cd /d \"%~dp0\"\n"
        "start \"\" \"%~dp0매출분석.exe\"\n",
        encoding="utf-8",
    )
    for doc in (
        "배포용_설치안내.txt",
        "다른컴퓨터_설치안내.txt",
        "오픈소스_라이선스_고지.txt",
    ):
        src = HERE / doc
        if src.exists():
            shutil.copy2(src, target / doc)
    # 배포 폴더 루트에 짧은 안내
    quick = target / "먼저_읽어주세요.txt"
    quick.write_text(
        "매출 분석 프로그램\n\n"
        "1. 「매출분석.exe」 또는 「실행.bat」 실행\n"
        "2. 자세한 설명: 배포용_설치안내.txt\n"
        "3. CSV 불러오기 → [분석 실행]\n\n"
        "※ HTML 파일만 더블클릭하면 저장 기능이 동작하지 않습니다.\n",
        encoding="utf-8",
    )


def main() -> int:
    html = find_html()
    print("HTML:", html.name)
    print("빌드 패키지 설치 중…")
    pip_install("pyinstaller", "pywebview", "openpyxl", "pillow")

    dist_dir = HERE / "dist" / APP_NAME
    deploy_dir = HERE / "배포용" / APP_NAME
    sep = ";" if sys.platform == "win32" else ":"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name",
        APP_NAME,
        "--hidden-import",
        "openpyxl",
        "--hidden-import",
        "openpyxl.drawing.image",
        "--hidden-import",
        "PIL",
        "--hidden-import",
        "PIL.Image",
        "--collect-all",
        "webview",
        "--collect-submodules",
        "openpyxl",
        "--add-data",
        f"{html.name}{sep}.",
        str(HERE / "app_launcher.py"),
    ]
    print("PyInstaller 실행…")
    subprocess.check_call(cmd, cwd=str(HERE))

    if not dist_dir.exists():
        raise SystemExit(f"빌드 실패: {dist_dir} 가 생성되지 않았습니다.")

    shutil.copy2(html, dist_dir / html.name)
    prepare_deploy_extras(dist_dir)

    if deploy_dir.exists():
        shutil.rmtree(deploy_dir)
    shutil.copytree(dist_dir, deploy_dir)
    prepare_deploy_extras(deploy_dir)

    exe = dist_dir / f"{APP_NAME}.exe"
    print()
    print("=" * 50)
    print("  빌드 완료")
    print("=" * 50)
    print(f"  EXE: {exe}")
    print(f"  USB 복사용: {deploy_dir}")
    print()
    print("다른 PC 배포:")
    print(f"  1) '{deploy_dir.name}' 폴더 전체를 USB로 복사")
    print("  2) 다른 PC에서 매출분석.exe 실행 (Python 설치 불필요)")
    print("  3) (1) 판매 CSV + (2) 구매 CSV(선택) 불러오기 → 분석")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
