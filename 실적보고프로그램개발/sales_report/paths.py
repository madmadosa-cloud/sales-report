"""개발 환경 / PyInstaller 패키징 경로 분기"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_bundle_dir() -> Path:
    """읽기 전용 번들(templates, staticfiles, Python 패키지) 위치"""
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def get_data_dir() -> Path:
    """쓰기 가능 데이터(DB, media, 로그) 위치 — exe와 같은 폴더"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BUNDLE_DIR = get_bundle_dir()
DATA_DIR = get_data_dir()
