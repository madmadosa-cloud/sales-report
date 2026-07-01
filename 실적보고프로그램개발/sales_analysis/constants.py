"""
품목·거래처 분류코드 마스터 (품목및거래처분류코드.csv 기준)
"""

from __future__ import annotations

# 품목분류 21개 — CSV 순서 유지
ITEM_CATEGORIES: dict[str, str] = {
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

# 거래처분류 6개 — CSV 순서 유지
CUSTOMER_CATEGORIES: dict[str, str] = {
    "a": "지방자치단체",
    "b": "교육기관",
    "c": "국가기관",
    "d": "공공기관",
    "e": "기타",
    "z": "생산시설",
}

UNCLASSIFIED_LABEL = "미분류"

# 간편보고서: 기타(e)·생산시설(z)·미분류 통합 구간
SIMPLE_MERGED_CODE = "merged"
SIMPLE_MERGED_LABEL = "기타·생산시설·미분류"
SIMPLE_CUSTOMER_ORDER = ["a", "b", "c", "d", SIMPLE_MERGED_CODE]
STANDARD_CUSTOMER_CODES = ("a", "b", "c", "d")

ITEM_CATEGORY_ORDER = list(ITEM_CATEGORIES.keys())
CUSTOMER_CATEGORY_ORDER = list(CUSTOMER_CATEGORIES.keys())

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
