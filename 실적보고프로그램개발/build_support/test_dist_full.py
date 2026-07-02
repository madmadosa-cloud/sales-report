"""
빌드된 exe 통합 테스트 — CSV 업로드, 보고서, Excel/PDF 다운로드

사용법:
  .venv\\Scripts\\python build_support\\test_dist_full.py
"""

from __future__ import annotations

import http.cookiejar
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_EXE = PROJECT_ROOT / "dist" / "매출분석프로그램" / "매출분석프로그램.exe"
BASE = "http://127.0.0.1:8000"

SAMPLE_CSV = (
    "품목코드,품목명(규격),전표별,품목별,거래처별,수량,거래처코드,공급가액,부가세,합계,적요\n"
    "B001-2024-3,핸드타올,20250102-1,핸드타올,테스트,15,e1-00145,495000,0,495000,\n"
    "O001-2024-1,충전기,20250115-2,충전기,테스트2,2,a1-00001,100000,0,100000,\n"
).encode("utf-8-sig")


class Client:
    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def get(self, path: str) -> tuple[int, bytes, dict[str, str]]:
        req = urllib.request.Request(BASE + path, method="GET")
        with self.opener.open(req, timeout=15) as response:
            return response.status, response.read(), dict(response.headers)

    def post_multipart(self, path: str, fields: dict, files: dict) -> tuple[int, bytes]:
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        body = bytearray()
        for key, value in fields.items():
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
            body.extend(f"{value}\r\n".encode())
        for key, (filename, content, content_type) in files.items():
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(
                f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'.encode()
            )
            body.extend(f"Content-Type: {content_type}\r\n\r\n".encode())
            body.extend(content)
            body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode())

        req = urllib.request.Request(
            BASE + path,
            data=bytes(body),
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with self.opener.open(req, timeout=30) as response:
            return response.status, response.read()

    def post_form(self, path: str, fields: dict) -> tuple[int, bytes]:
        data = urlencode(fields).encode()
        req = urllib.request.Request(
            BASE + path,
            data=data,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with self.opener.open(req, timeout=30) as response:
            return response.status, response.read()


def csrf_from_html(html: str) -> str:
    match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
    if not match:
        raise RuntimeError("CSRF token not found")
    return match.group(1)


def wait_for_server(timeout: float = 40.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BASE + "/", timeout=2) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.5)
    return False


def main() -> int:
    if not DIST_EXE.is_file():
        print(f"exe not found: {DIST_EXE}")
        return 1

    test_dir = Path(tempfile.mkdtemp(prefix="sales_dist_test_"))
    try:
        shutil.copytree(DIST_EXE.parent, test_dir / "app")
        exe = test_dir / "app" / DIST_EXE.name
        proc = subprocess.Popen(
            [str(exe)],
            cwd=exe.parent,
            env={**os.environ, "PACKAGING_TEST": "1"},
        )
        if not wait_for_server():
            print("FAIL: server start")
            return 1
        print("OK: server started")

        client = Client()
        _, home_html, _ = client.get("/")
        token = csrf_from_html(home_html.decode("utf-8", errors="replace"))

        status, _ = client.post_multipart(
            "/upload/",
            {"csrfmiddlewaretoken": token, "year": "2025", "month": "1"},
            {"files": ("sample.csv", SAMPLE_CSV, "text/csv")},
        )
        if status != 200:
            print(f"FAIL: upload status {status}")
            return 1
        print("OK: CSV upload")

        _, home_html2, _ = client.get("/")
        token = csrf_from_html(home_html2.decode("utf-8", errors="replace"))
        status, report_html = client.post_form(
            "/report/generate/",
            {
                "csrfmiddlewaretoken": token,
                "year": "2025",
                "preset": "first_half",
                "start_month": "1",
                "end_month": "6",
            },
        )
        if status != 200 or "매출분석" not in report_html.decode("utf-8", errors="replace"):
            print("FAIL: report generation")
            return 1
        print("OK: report preview")

        status, xlsx_data, _ = client.get("/report/download/excel/")
        if status != 200 or not xlsx_data.startswith(b"PK"):
            print(f"FAIL: excel download (status={status}, size={len(xlsx_data)})")
            return 1
        print(f"OK: excel download ({len(xlsx_data)} bytes)")

        try:
            status, pdf_data, _ = client.get("/report/download/pdf/")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            print(f"FAIL: pdf download ({exc.code}): {body}")
            return 1
        if status != 200 or not pdf_data.startswith(b"%PDF"):
            print(f"FAIL: pdf download (status={status}, head={pdf_data[:20]!r})")
            return 1
        print(f"OK: pdf download ({len(pdf_data)} bytes)")

        db_path = exe.parent / "db.sqlite3"
        if not db_path.is_file():
            print("FAIL: db missing")
            return 1

        proc.kill()
        proc.wait(timeout=10)

        size1 = db_path.stat().st_size
        proc2 = subprocess.Popen(
            [str(exe)],
            cwd=exe.parent,
            env={**os.environ, "PACKAGING_TEST": "1"},
        )
        if not wait_for_server():
            print("FAIL: second server start")
            return 1
        proc2.kill()
        proc2.wait(timeout=10)
        size2 = db_path.stat().st_size
        if size2 < size1:
            print("FAIL: database shrank on restart")
            return 1
        print("OK: data persists across restarts")

        print()
        print("Full integration test passed.")
        return 0
    finally:
        if "proc" in locals() and proc.poll() is None:
            proc.kill()
        if "proc2" in locals() and proc2.poll() is None:
            proc2.kill()
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
