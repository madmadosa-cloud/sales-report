"""
CSV 업로드 → DB 저장
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.db import transaction

from sales_analysis.models import PendingSalesImport, SalesRecord
from sales_analysis.services.classification import parse_sales_csv


def parse_uploaded_files(files) -> tuple[list[dict], list[str], dict[tuple[int, int], set[str]]]:
    """
    복수 CSV 파일 파싱.
    반환: (all_records, warnings, period_files)
    period_files: {(year, month): {filename, ...}}
    """
    all_records: list[dict] = []
    warnings: list[str] = []
    period_files: dict[tuple[int, int], set[str]] = defaultdict(set)

    for uploaded in files:
        name = uploaded.name or "unknown.csv"
        if not name.lower().endswith(".csv"):
            raise ValueError(f"CSV 파일만 업로드할 수 있습니다: {name}")

        content = uploaded.read()
        records, file_warnings = parse_sales_csv(content, name)
        warnings.extend(file_warnings)
        all_records.extend(records)
        for rec in records:
            period_files[(rec["year"], rec["month"])].add(name)

    return all_records, warnings, period_files


def find_existing_periods(periods: set[tuple[int, int]]) -> list[tuple[int, int]]:
    """DB에 이미 존재하는 연/월 목록"""
    existing = []
    for year, month in sorted(periods):
        if SalesRecord.objects.filter(year=year, month=month).exists():
            existing.append((year, month))
    return existing


def save_pending_import(session_key: str, records: list[dict], period_files: dict) -> None:
    """확인 대기 데이터를 PendingSalesImport에 저장"""
    PendingSalesImport.objects.filter(session_key=session_key).delete()

    by_period: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for rec in records:
        by_period[(rec["year"], rec["month"])].append(rec)

    for (year, month), period_records in by_period.items():
        files = ", ".join(sorted(period_files.get((year, month), set())))
        PendingSalesImport.objects.create(
            session_key=session_key,
            year=year,
            month=month,
            records=period_records,
            source_files=files,
        )


def commit_pending_import(session_key: str) -> int:
    """대기 중 데이터를 SalesRecord로 저장 (기존 동일 연월 삭제 후)"""
    pending_list = list(PendingSalesImport.objects.filter(session_key=session_key))
    if not pending_list:
        return 0

    total_saved = 0
    with transaction.atomic():
        for pending in pending_list:
            SalesRecord.objects.filter(year=pending.year, month=pending.month).delete()
            objects = [_dict_to_model(r) for r in pending.records]
            SalesRecord.objects.bulk_create(objects, batch_size=500)
            total_saved += len(objects)
            pending.delete()

    return total_saved


def save_records_directly(records: list[dict]) -> int:
    """확인 없이 바로 저장 (신규 연월)"""
    by_period: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for rec in records:
        by_period[(rec["year"], rec["month"])].append(rec)

    total = 0
    with transaction.atomic():
        for (year, month), period_records in by_period.items():
            objects = [_dict_to_model(r) for r in period_records]
            SalesRecord.objects.bulk_create(objects, batch_size=500)
            total += len(objects)
    return total


def process_upload(session_key: str, files, confirmed: bool = False) -> dict:
    """업로드 처리 통합 진입점"""
    if confirmed:
        pending_exists = PendingSalesImport.objects.filter(session_key=session_key).exists()
        if not pending_exists:
            return {"status": "no_pending"}
        periods = list(
            PendingSalesImport.objects.filter(session_key=session_key).values_list("year", "month")
        )
        count = commit_pending_import(session_key)
        return {"status": "ok", "count": count, "replaced": periods}

    records, warnings, period_files = parse_uploaded_files(files)
    periods = {(r["year"], r["month"]) for r in records}
    existing = find_existing_periods(periods)

    if existing and not confirmed:
        save_pending_import(session_key, records, period_files)
        return {
            "status": "confirm_needed",
            "existing": existing,
            "warnings": warnings,
            "total_rows": len(records),
        }

    PendingSalesImport.objects.filter(session_key=session_key).delete()
    count = save_records_directly(records)
    return {"status": "ok", "count": count, "warnings": warnings}


def _dict_to_model(data: dict) -> SalesRecord:
    return SalesRecord(
        year=data["year"],
        month=data["month"],
        item_code=data["item_code"],
        item_name=data["item_name"],
        voucher_no=data["voucher_no"],
        item_label=data["item_label"],
        customer_name=data["customer_name"],
        customer_code=data["customer_code"],
        quantity=Decimal(data["quantity"]),
        supply_amount=Decimal(data["supply_amount"]),
        vat=Decimal(data["vat"]),
        total=Decimal(data["total"]),
        memo=data.get("memo", ""),
        item_category_code=data["item_category_code"],
        customer_category_code=data["customer_category_code"],
        is_unclassified_item=data["is_unclassified_item"],
        is_unclassified_customer=data["is_unclassified_customer"],
        source_file=data.get("source_file", ""),
    )


def get_stored_periods() -> list[dict]:
    """저장된 연월 목록 (UI 표시용)"""
    from django.db.models import Count

    qs = (
        SalesRecord.objects.values("year", "month")
        .annotate(row_count=Count("id"))
        .order_by("year", "month")
    )
    return list(qs)
