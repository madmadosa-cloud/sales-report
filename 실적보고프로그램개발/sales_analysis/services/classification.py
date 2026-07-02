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



from sales_analysis.constants import REQUIRED_SALES_COLUMNS

from sales_analysis.services.master_service import (

    is_known_customer_code,

    is_known_item_code,

    normalize_category_code,

    summarize_unknown_codes,

)



logger = logging.getLogger(__name__)



ITEM_CODE_PATTERN = re.compile(r"^[a-zA-Z]+", re.ASCII)

CUSTOMER_PREFIX_PATTERN = re.compile(r"^([a-zA-Z])", re.ASCII)

VALID_ITEM_ROW_PATTERN = re.compile(r"^[a-zA-Z]+", re.ASCII)





def extract_item_category_code(item_code: str) -> str:

    if not item_code:

        return ""

    match = ITEM_CODE_PATTERN.match(str(item_code).strip())

    return match.group(0).lower() if match else ""





def extract_customer_category_code(customer_code: str) -> str:

    if not customer_code:

        return ""

    match = CUSTOMER_PREFIX_PATTERN.match(str(customer_code).strip())

    return match.group(1).lower() if match else ""





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

            code = normalize_category_code(parts[0])

            item_map[code] = parts[1].strip()



    customer_map: dict[str, str] = {}

    for line in lines[split_idx + 1 :]:

        line = line.strip()

        if not line:

            continue

        parts = line.split(",", 1)

        if len(parts) == 2 and parts[0].strip():

            code = normalize_category_code(parts[0])

            customer_map[code] = parts[1].strip()



    return item_map, customer_map





def parse_master_csv(content: bytes, kind: str) -> list[tuple[str, str]]:

    """품목 또는 거래처 분류코드 CSV 파싱 (kind: item | customer)"""

    item_map, customer_map = parse_classification_csv(content)

    if kind == "item":

        return [(code, name) for code, name in item_map.items()]

    return [(code, name) for code, name in customer_map.items()]





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

    unknown_item_codes: set[str] = set()

    unknown_customer_codes: set[str] = set()



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



        is_unclassified_item = not is_known_item_code(item_cat_code)

        is_unclassified_customer = not is_known_customer_code(cust_cat_code)

        if is_unclassified_item and item_cat_code:

            unknown_item_codes.add(item_cat_code)

        if is_unclassified_customer and cust_cat_code:

            unknown_customer_codes.add(cust_cat_code)



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

                "customer_category_code": cust_cat_code,

                "is_unclassified_item": is_unclassified_item,

                "is_unclassified_customer": is_unclassified_customer,

                "source_file": source_filename,

            }

        )



    if not records:

        raise ValueError(f"유효한 데이터 행이 없습니다 ({source_filename})")



    warnings.extend(summarize_unknown_codes(unknown_item_codes, unknown_customer_codes))

    return records, warnings




def parse_profit_csv(content: bytes, source_filename: str = "") -> tuple[list[dict], list[str]]:
    """이익현황 CSV 파싱 — 품목코드, 판매 수량, 원가, 이익금 사용"""
    warnings: list[str] = []
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"UTF-8 인코딩이 아닙니다 ({source_filename})") from exc

    raw_rows = list(csv.reader(io.StringIO(text)))
    if not raw_rows:
        raise ValueError(f"CSV 데이터가 없습니다 ({source_filename})")

    header_idx, header, sub_header = _find_profit_header_rows(raw_rows)
    if header is None:
        raise ValueError(f"'품목코드' 헤더 행을 찾을 수 없습니다 ({source_filename})")

    col_map = _map_profit_columns(header, sub_header)
    if "item_code" not in col_map:
        raise ValueError(f"품목코드 컬럼을 찾을 수 없습니다 ({source_filename})")
    if "sale_qty" not in col_map:
        raise ValueError(f"판매 수량 컬럼을 찾을 수 없습니다 ({source_filename})")
    if "profit_amount" not in col_map:
        raise ValueError(f"이익 금액 컬럼을 찾을 수 없습니다 ({source_filename})")

    records: list[dict] = []
    unknown_codes: set[str] = set()
    unknown_customer_codes: set[str] = set()

    data_start = header_idx + 1 + (1 if sub_header else 0)

    for row in raw_rows[data_start :]:
        if not row or not any(str(c).strip() for c in row):
            continue
        item_code = _cell(row, col_map.get("item_code"))
        if not item_code:
            continue
        if not VALID_ITEM_ROW_PATTERN.match(item_code):
            continue

        quantity = parse_number(_cell(row, col_map.get("sale_qty")))
        cost_amount = parse_number(_cell(row, col_map.get("cost_amount")))
        profit_amount = parse_number(_cell(row, col_map.get("profit_amount")))
        if profit_amount is None and cost_amount is None and not quantity:
            continue

        quantity = quantity or Decimal(0)
        cost_amount = cost_amount or Decimal(0)
        profit_amount = profit_amount or Decimal(0)

        item_cat_code = extract_item_category_code(item_code)
        is_unclassified_item = not is_known_item_code(item_cat_code)
        if is_unclassified_item and item_cat_code:
            unknown_codes.add(item_cat_code)

        item_name = _cell(row, col_map.get("item_name")) or ""
        customer_code = _cell(row, col_map.get("customer_code")) or ""
        customer_name = _cell(row, col_map.get("customer_name")) or ""
        customer_cat_code = extract_customer_category_code(customer_code)
        is_unclassified_customer = not is_known_customer_code(customer_cat_code)
        if is_unclassified_customer and customer_cat_code:
            unknown_customer_codes.add(customer_cat_code)

        records.append(
            {
                "item_code": item_code,
                "item_name": item_name,
                "customer_code": customer_code,
                "customer_name": customer_name,
                "category_label": item_name,
                "item_category_code": item_cat_code,
                "customer_category_code": customer_cat_code,
                "quantity": str(quantity or 0),
                "cost": str(cost_amount or 0),
                "amount": str(profit_amount),
                "is_unclassified_item": is_unclassified_item,
                "is_unclassified_customer": is_unclassified_customer,
                "source_file": source_filename,
            }
        )

    if not records:
        raise ValueError(f"유효한 데이터 행이 없습니다 ({source_filename})")

    if unknown_codes or unknown_customer_codes:
        warnings.extend(summarize_unknown_codes(unknown_codes, unknown_customer_codes))

    return records, warnings




def _is_profit_sub_header(row: list[str]) -> bool:
    cells = [_normalize_profit_detail_cell(c) for c in row]
    return any(c == "단가" for c in cells) and any(c == "금액" for c in cells)


def _find_profit_header_rows(
    raw_rows: list[list[str]],
) -> tuple[int | None, list[str] | None, list[str] | None]:
    for idx, row in enumerate(raw_rows):
        normalized = [(c or "").strip() for c in row]
        if any("품목코드" in cell for cell in normalized):
            sub_header = None
            if idx + 1 < len(raw_rows) and _is_profit_sub_header(raw_rows[idx + 1]):
                sub_header = [(c or "").strip() for c in raw_rows[idx + 1]]
            return idx, normalized, sub_header
    return None, None, None


def _normalize_profit_detail_cell(cell: str) -> str:
    text = (cell or "").strip()
    if text.startswith("단가"):
        return "단가"
    if text.startswith("금액"):
        return "금액"
    if text == "수량" or text.startswith("수량"):
        return "수량"
    return text


def _find_group_amount_index(
    header: list[str],
    sub_header: list[str] | None,
    *,
    group_label: str,
    amount_ordinal: int,
) -> int | None:
    """병합 헤더(판매/원가/이익) 아래 '금액' 열 인덱스. 단가 열은 사용하지 않음."""
    if sub_header:
        for i, raw in enumerate(header):
            cell = (raw or "").strip()
            if group_label not in cell:
                continue
            if group_label == "이익" and "이익율" in cell:
                continue
            # 원가/이익 구간: 단가 다음 열의 금액을 사용
            for j in range(i, min(i + 3, len(sub_header))):
                left = _normalize_profit_detail_cell(sub_header[j])
                right = _normalize_profit_detail_cell(sub_header[j + 1]) if j + 1 < len(sub_header) else ""
                if left == "단가" and right == "금액":
                    return j + 1
                if left == "금액" and j > i:
                    return j

    detail = sub_header if sub_header else header
    amount_cols = [
        i for i, cell in enumerate(detail) if _normalize_profit_detail_cell(cell) == "금액"
    ]
    if len(amount_cols) >= amount_ordinal:
        return amount_cols[amount_ordinal - 1]
    return None


def _amount_indices_from_unit_pairs(detail: list[str]) -> list[int]:
    """단가+금액 쌍마다 금액 열 인덱스 (판매·원가·이익 순)."""
    amounts: list[int] = []
    i = 0
    while i < len(detail):
        cell = _normalize_profit_detail_cell(detail[i])
        next_cell = _normalize_profit_detail_cell(detail[i + 1]) if i + 1 < len(detail) else ""
        if cell == "단가" and next_cell == "금액":
            amounts.append(i + 1)
            i += 2
            continue
        i += 1
    return amounts


def _map_metric_columns(detail: list[str]) -> dict[str, int]:
    """하위 헤더(수량·단가·금액) 행 기준 — 원가/이익은 단가가 아닌 금액 열."""
    indices: dict[str, int] = {}
    qty_cols = [
        i for i, cell in enumerate(detail) if _normalize_profit_detail_cell(cell) == "수량"
    ]
    if qty_cols:
        indices["sale_qty"] = qty_cols[0]

    pair_amounts = _amount_indices_from_unit_pairs(detail)
    if len(pair_amounts) >= 2:
        indices["cost_amount"] = pair_amounts[1]
    if len(pair_amounts) >= 3:
        indices["profit_amount"] = pair_amounts[2]
    elif len(pair_amounts) == 2:
        indices["profit_amount"] = pair_amounts[1]
    elif len(pair_amounts) == 1:
        indices["profit_amount"] = pair_amounts[0]

    if "cost_amount" not in indices:
        amount_cols = [
            i for i, cell in enumerate(detail) if _normalize_profit_detail_cell(cell) == "금액"
        ]
        if len(amount_cols) >= 2:
            indices["cost_amount"] = amount_cols[1]
        if "profit_amount" not in indices and len(amount_cols) >= 3:
            indices["profit_amount"] = amount_cols[2]

    return indices


def _find_sale_qty_index(header: list[str], sub_header: list[str] | None) -> int | None:
    detail = sub_header if sub_header else header
    qty_cols = [
        i for i, cell in enumerate(detail) if _normalize_profit_detail_cell(cell) == "수량"
    ]

    if sub_header:
        for i, raw in enumerate(header):
            if "판매" in (raw or ""):
                for j in range(i, min(i + 3, len(sub_header))):
                    if _normalize_profit_detail_cell(sub_header[j]) == "수량":
                        return j

    return qty_cols[0] if qty_cols else None


def _map_profit_columns(header: list[str], sub_header: list[str] | None = None) -> dict[str, int]:
    """헤더 매핑 — 판매 수량, 원가 금액(단가 아님), 이익 금액(단가 아님)"""
    indices: dict[str, int] = {}

    for i, raw in enumerate(header):
        cell = (raw or "").strip()
        if "품목코드" in cell:
            indices["item_code"] = i
        elif cell in ("품목명(규격)", "품목명[규격]", "품목명") or cell.startswith("품목명"):
            indices["item_name"] = i
        elif "거래처코드" in cell:
            indices["customer_code"] = i
        elif "거래처명" in cell or cell == "거래처별":
            indices["customer_name"] = i

    sale_qty = _find_sale_qty_index(header, sub_header)
    if sale_qty is not None:
        indices["sale_qty"] = sale_qty

    detail = sub_header if sub_header else header
    metric_cols = _map_metric_columns(detail)
    indices.update(metric_cols)

    cost_idx = _find_group_amount_index(header, sub_header, group_label="원가", amount_ordinal=2)
    profit_idx = _find_group_amount_index(header, sub_header, group_label="이익", amount_ordinal=3)
    if cost_idx is not None:
        indices["cost_amount"] = cost_idx
    if profit_idx is not None:
        indices["profit_amount"] = profit_idx

    # ERP 위치 기반 폴백 (품목코드, 품목명, 거래처코드, 거래처명, 수량, 단가, 금액, …)
    if len(header) >= 11:
        indices.setdefault("item_code", 0)
        indices.setdefault("item_name", 1)
        indices.setdefault("customer_code", 2)
        indices.setdefault("customer_name", 3)
        indices.setdefault("sale_qty", 4)
        indices.setdefault("cost_amount", 8)
        indices.setdefault("profit_amount", 10)

    return indices




def _cell(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return str(row[index]).strip()

