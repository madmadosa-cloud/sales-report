"""
빌드된 exe 스모크 테스트 (개발 PC에서 실행)

사용법:
  .venv\\Scripts\\python build_support\\test_dist.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_EXE = PROJECT_ROOT / "dist" / "매출분석프로그램" / "매출분석프로그램.exe"


def wait_for_server(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.5)
    return False


def main() -> int:
    if not DIST_EXE.is_file():
        print(f"exe not found: {DIST_EXE}")
        print("Run build_support/build.py first.")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        test_dir = Path(tmp) / "test_run"
        shutil.copytree(DIST_EXE.parent, test_dir)
        exe = test_dir / DIST_EXE.name

        print(f"Starting: {exe}")
        proc = subprocess.Popen(
            [str(exe)],
            cwd=test_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ, "PACKAGING_TEST": "1"},
        )

        url = "http://127.0.0.1:8000/"
        if not wait_for_server(url):
            out = proc.stdout.read(4000) if proc.stdout else ""
            proc.kill()
            print("FAIL: server did not start")
            print(out)
            return 1

        print("OK: homepage responds")
        with urllib.request.urlopen(url, timeout=5) as response:
            html = response.read().decode("utf-8", errors="replace")
        if "매출 분석" not in html:
            print("FAIL: unexpected homepage content")
            proc.kill()
            return 1
        print("OK: homepage content")

        master_url = "http://127.0.0.1:8000/master/"
        with urllib.request.urlopen(master_url, timeout=5) as response:
            master_html = response.read().decode("utf-8", errors="replace")
        if "품목분류코드" not in master_html:
            print("FAIL: master page")
            proc.kill()
            return 1
        print("OK: master page with seeded categories")

        db_path = test_dir / "db.sqlite3"
        if not db_path.is_file():
            print("FAIL: db.sqlite3 not created in exe folder")
            proc.kill()
            return 1
        print(f"OK: database created at {db_path}")

        proc.kill()
        proc.wait(timeout=10)

        if not db_path.is_file():
            print("FAIL: database disappeared after stop")
            return 1
        print("OK: database persists after stop")

    print()
    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
