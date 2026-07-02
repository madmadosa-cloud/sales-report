"""
공통 상수 (분류 마스터는 DB 테이블에서 관리)
"""

from __future__ import annotations

# 앱 메타 (푸터·README 등 — 버전 변경 시 이곳만 수정)
APP_VERSION = "1.0.0"
APP_AUTHOR = "madmadosa-cloud"
APP_LICENSE = "MIT License"

UNCLASSIFIED_LABEL = "미분류"

# 간편보고서: 기타(e)·생산시설(z)·미분류 통합 구간
SIMPLE_MERGED_CODE = "merged"
SIMPLE_MERGED_LABEL = "기타·생산시설·미분류"
SIMPLE_CUSTOMER_ORDER = ["a", "b", "c", "d", SIMPLE_MERGED_CODE]
STANDARD_CUSTOMER_CODES = ("a", "b", "c", "d")

# 이익분석 최종보고서: a~d 통합 / e·z·미분류 통합
FINAL_MAIN_MERGED_CODE = "final_main"
FINAL_MAIN_MERGED_LABEL = "지방자치단체+교육기관+국가기관+공공기관"
FINAL_CUSTOMER_ORDER = [FINAL_MAIN_MERGED_CODE, SIMPLE_MERGED_CODE]

REQUIRED_SALES_COLUMNS = [
    "품목코드",
    "품목명(규격)",
    "전표별",
    "품목별",
    "거래처별",
    "수량",
    "거래처코드",
    "공급가액",
    "부가세",
    "합계",
    "적요",
]

REQUIRED_PROFIT_COLUMNS = [
    "품목코드",
]

# 마이그레이션 초기 시드용 (운영 시 DB 마스터가 기준)
SEED_ITEM_CATEGORIES: dict[str, str] = {
    "a": "복사용지",
    "b": "화장지물티슈",
    "c": "장갑피복류",
    "d": "가구",
    "e": "사무용품",
    "f": "인쇄판촉물",
    "g": "세제",
    "h": "식품류",
    "i": "마대비닐봉투",
    "j": "종이컵",
    "k": "서비스용역",
    "l": "마스크",
    "m": "노트북장",
    "n": "종이박스",
    "o": "전기충전기",
    "p": "간판",
    "q": "LED등기구",
    "r": "멀티탭",
    "s": "블라인드",
    "t": "원격수도검침",
    "u": "전기설비발전기",
    "z": "일반품목",
}

SEED_CUSTOMER_CATEGORIES: dict[str, str] = {
    "a": "지방자치단체",
    "b": "교육기관",
    "c": "국가기관",
    "d": "공공기관",
    "e": "기타",
    "z": "생산시설",
}

CATEGORY_CODE_PATTERN = r"^[a-z]$"
CATEGORY_CODE_ERROR = "코드는 영문 소문자 1글자(a~z)만 사용할 수 있습니다."

MASTER_UPLOAD_MODE_MERGE = "merge"
MASTER_UPLOAD_MODE_REPLACE = "replace_all"

# 복지부보고서 출력항목 (id, 출력항목명, 품목코드 첫 영문자)
# 동일 코드가 여러 항목에 있으면 위에서부터 첫 항목에만 배정 (c → 의류침구)
WELFARE_OUTPUT_ITEMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("facility", "시설설비", ("o", "q", "t", "u")),
    ("print_ad", "인쇄광고", ("f", "n", "p")),
    ("office", "사무문구", ("a", "e")),
    ("clothing", "의류침구", ("c",)),
    ("digital", "디지털가전", ("r",)),
    ("living", "생활용품", ("b", "g")),
    ("service", "서비스", ("k",)),
    ("disposable", "일회용품", ("i", "j", "l")),
    ("furniture", "가구", ("d", "m", "s")),
    ("food", "식품", ("h",)),
    ("flowers", "화훼", ()),
    ("crafts", "공예", ()),
    ("etc", "기타", ("z",)),
)

WELFARE_ETC_GROUP_ID = "etc"

# 마이그레이션·초기 시드용 (운영 시 DB가 기준 — welfare_service)
