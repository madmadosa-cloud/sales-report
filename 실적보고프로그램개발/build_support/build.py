"""
매출분석 프로그램 Windows exe 빌드 스크립트

사용법 (프로젝트 루트에서):
  .venv\\Scripts\\python build_support\\build.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HTMX_URL = "https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js"
HTMX_PATH = PROJECT_ROOT / "static" / "sales_analysis" / "js" / "htmx.min.js"
DIST_DIR = PROJECT_ROOT / "dist" / "매출분석프로그램"
BUILD_DIR = PROJECT_ROOT / "build"


def run(cmd: list[str], **kwargs) -> None:
    print(">", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT, **kwargs)


def ensure_htmx() -> None:
    HTMX_PATH.parent.mkdir(parents=True, exist_ok=True)
    if HTMX_PATH.is_file() and HTMX_PATH.stat().st_size > 1000:
        print(f"HTMX already present: {HTMX_PATH}")
        return
    print(f"Downloading HTMX -> {HTMX_PATH}")
    urllib.request.urlretrieve(HTMX_URL, HTMX_PATH)


def collect_static() -> None:
    staticfiles = PROJECT_ROOT / "staticfiles"
    if staticfiles.exists():
        shutil.rmtree(staticfiles)
    run([sys.executable, "manage.py", "collectstatic", "--noinput", "--clear"])


def pyinstaller_build() -> None:
    spec = PROJECT_ROOT / "build_support" / "sales_app.spec"
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            str(spec),
            "--distpath",
            str(PROJECT_ROOT / "dist"),
            "--workpath",
            str(BUILD_DIR),
        ]
    )


def copy_distribution_docs() -> None:
    if not DIST_DIR.is_dir():
        raise FileNotFoundError(f"Build output not found: {DIST_DIR}")

    for name in ("README_설치방법.txt", "LICENSE"):
        src = PROJECT_ROOT / name
        if src.is_file():
            shutil.copy2(src, DIST_DIR / name)


def create_zip() -> Path:
    copy_distribution_docs()
    zip_base = PROJECT_ROOT / "dist" / "매출분석프로그램_배포"
    if Path(f"{zip_base}.zip").exists():
        Path(f"{zip_base}.zip").unlink()
    shutil.make_archive(str(zip_base), "zip", root_dir=DIST_DIR.parent, base_dir=DIST_DIR.name)
    return Path(f"{zip_base}.zip")


def main() -> int:
    ensure_htmx()
    collect_static()
    pyinstaller_build()
    zip_path = create_zip()
    print()
    print("=" * 60)
    print(" 빌드 완료")
    print(f" 실행 폴더: {DIST_DIR}")
    print(f" 배포 zip:  {zip_path}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
