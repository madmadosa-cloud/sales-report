"""
분류코드 추출 및 CSV 파싱 유틸
"""

from __future__ import annotations

import csv
import io
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from sales_analysis.constants import (
    CUSTOMER_CATEGORIES,
    ITEM_CATEGORIES,
    REQUIRED_SALES_COLUMNS,
    UNCLASSIFIED_LABEL,
)

logger = logging.getLogger(__name__)

ITEM_CODE_PATTERN = re.compile(r"^[a-z]+", re.ASCII)
CUSTOMER_PREFIX_PATTERN = re.compile(r"^([A-Z])")
VALID_ITEM_ROW_PATTERN = re.compile(r"^[a-z]+", re.ASCII)


def extract_item_category_code(item_code: str) -> str:
    if not item_code:
        return ""
    match = ITEM_CODE_PATTERN.match(str(item_code).strip())
    return match.group(0) if match else ""


def extract_customer_category_code(customer_code: str) -> str:
    if not customer_code:
        return ""
    match = CUSTOMER_PREFIX_PATTERN.match(str(customer_code).strip())
    return match.group(1).lower() if match else ""


def resolve_item_category_name(code: str) -> str:
    if not code:
        return UNCLASSIFIED_LABEL
    return ITEM_CATEGORIES.get(code, UNCLASSIFIED_LABEL)


def resolve_customer_category_name(code: str) -> str:
    if not code:
        return UNCLASSIFIED_LABEL
    return CUSTOMER_CATEGORIES.get(code, UNCLASSIFIED_LABEL)


def parse_number(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in ("nan", "none", "-"):
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def parse_voucher_year_month(voucher_no: str) -> tuple[int | None, int | None]:
    if not voucher_no:
        return None, None
    text = str(voucher_no).strip()
    date_part = text.split("-")[0]
    if len(date_part) < 6 or not date_part[:6].isdigit():
        return None, None
    year = int(date_part[:4])
    month = int(date_part[4:6])
    if month < 1 or month > 12:
        return None, None
    return year, month


def parse_classification_csv(content: bytes) -> tuple[dict[str, str], dict[str, str]]:
    text = content.decode("utf-8-sig")
    lines = text.splitlines()
    split_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("거래처코드"):
            split_idx = i
            break
    if split_idx is None:
        raise ValueError("분류코드 CSV에서 '거래처코드,' 헤더를 찾을 수 없습니다.")

    item_map: dict[str, str] = {}
    for line in lines[1:split_idx]:
        line = line.strip()
        if not line or line.startswith("품목코드"):
            continue
        parts = line.split(",", 1)
        if len(parts) == 2 and parts[0].strip():
            item_map[parts[0].strip()] = parts[1].strip()

    customer_map: dict[str, str] = {}
    for line in lines[split_idx + 1 :]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(",", 1)
        if len(parts) == 2 and parts[0].strip():
            customer_map[parts[0].strip()] = parts[1].strip()

    return item_map, customer_map


def parse_sales_csv(content: bytes, source_filename: str = "") -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"UTF-8 인코딩이 아닙니다 ({source_filename})") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError(f"CSV 헤더가 없습니다 ({source_filename})")

    fieldnames = [f.strip() for f in reader.fieldnames]
    missing = [c for c in REQUIRED_SALES_COLUMNS if c not in fieldnames]
    if missing:
        raise ValueError(f"필수 컬럼이 없습니다: {', '.join(missing)}")

    records: list[dict] = []
    for idx, row in enumerate(reader, start=2):
        item_code = str(row.get("품목코드", "")).strip()
        if not VALID_ITEM_ROW_PATTERN.match(item_code):
            continue

        voucher_no = str(row.get("전표별", "")).strip()
        year, month = parse_voucher_year_month(voucher_no)
        if year is None or month is None:
            warnings.append(f"행 {idx}: 전표별 형식 오류 ({voucher_no}) — 건너뜀")
            continue

        quantity = parse_number(row.get("수량"))
        supply_amount = parse_number(row.get("공급가액"))
        vat = parse_number(row.get("부가세"))
        total = parse_number(row.get("합계"))

        if total is None:
            warnings.append(f"행 {idx}: 합계 파싱 실패 — 건너뜀")
            logger.warning("Skip row %s: invalid total in %s", idx, source_filename)
            continue

        item_cat_code = extract_item_category_code(item_code)
        cust_code_raw = str(row.get("거래처코드", "")).strip()
        cust_cat_code = extract_customer_category_code(cust_code_raw)

        item_cat_name = resolve_item_category_name(item_cat_code)
        cust_cat_name = resolve_customer_category_name(cust_cat_code)

        records.append(
            {
                "year": year,
                "month": month,
                "item_code": item_code,
                "item_name": str(row.get("품목명(규격)", "")).strip(),
                "voucher_no": voucher_no,
                "item_label": str(row.get("품목별", "")).strip(),
                "customer_name": str(row.get("거래처별", "")).strip(),
                "quantity": str(quantity) if quantity is not None else "0",
                "customer_code": cust_code_raw,
                "supply_amount": str(supply_amount or 0),
                "vat": str(vat or 0),
                "total": str(total),
                "memo": str(row.get("적요", "")).strip(),
                "item_category_code": item_cat_code,
                "item_category_name": item_cat_name,
                "customer_category_code": cust_cat_code,
                "customer_category_name": cust_cat_name,
                "is_unclassified_item": item_cat_name == UNCLASSIFIED_LABEL,
                "is_unclassified_customer": cust_cat_name == UNCLASSIFIED_LABEL,
                "source_file": source_filename,
            }
        )

    if not records:
        raise ValueError(f"유효한 데이터 행이 없습니다 ({source_filename})")

    return records, warnings
