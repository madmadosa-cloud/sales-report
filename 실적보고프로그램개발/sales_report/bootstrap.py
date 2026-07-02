"""exe 최초 실행 시 DB·폴더 초기화 (마이그레이션에 시드 데이터 포함)"""

from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings
from django.core.management import call_command


def ensure_runtime_dirs() -> None:
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    log_dir: Path = settings.LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)


def configure_logging() -> None:
    log_dir: Path = settings.LOG_DIR
    log_file = log_dir / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def initialize_database() -> None:
    call_command("migrate", interactive=False, verbosity=1)
