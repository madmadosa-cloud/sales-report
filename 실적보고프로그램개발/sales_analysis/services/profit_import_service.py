"""이익현황 CSV 업로드 → DB 저장"""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from sales_analysis.models import PendingProfitImport, ProfitRecord
from sales_analysis.services.classification import parse_profit_csv


def parse_profit_files(files) -> tuple[list[dict], list[str], list[str]]:
    all_records: list[dict] = []
    warnings: list[str] = []
    source_files: list[str] = []

    for uploaded in files:
        name = uploaded.name or "unknown.csv"
        if not name.lower().endswith(".csv"):
            raise ValueError(f"CSV 파일만 업로드할 수 있습니다: {name}")
        content = uploaded.read()
        records, file_warnings = parse_profit_csv(content, name)
        warnings.extend(file_warnings)
        all_records.extend(records)
        source_files.append(name)

    return all_records, warnings, source_files


def has_existing_profit_data() -> bool:
    return ProfitRecord.objects.exists()


def get_stored_profit_summary() -> dict | None:
    count = ProfitRecord.objects.count()
    if not count:
        return None
    latest = ProfitRecord.objects.order_by("-created_at").first()
    return {
        "row_count": count,
        "period_label": latest.period_label if latest else "",
    }


def save_pending_profit_import(
    session_key: str,
    records: list[dict],
    period_label: str,
    source_files: list[str],
) -> None:
    PendingProfitImport.objects.update_or_create(
        session_key=session_key,
        defaults={
            "records": records,
            "period_label": period_label,
            "source_files": ", ".join(source_files),
        },
    )


def commit_pending_profit_import(session_key: str) -> int:
    pending = PendingProfitImport.objects.filter(session_key=session_key).first()
    if not pending:
        return 0

    with transaction.atomic():
        ProfitRecord.objects.all().delete()
        objects = [_dict_to_model(r, pending.period_label) for r in pending.records]
        ProfitRecord.objects.bulk_create(objects, batch_size=500)
        pending.delete()
        return len(objects)


def save_profit_records_directly(records: list[dict], period_label: str) -> int:
    with transaction.atomic():
        ProfitRecord.objects.all().delete()
        objects = [_dict_to_model(r, period_label) for r in records]
        ProfitRecord.objects.bulk_create(objects, batch_size=500)
        return len(objects)


def process_profit_upload(
    session_key: str,
    files,
    period_label: str,
    confirmed: bool = False,
) -> dict:
    if confirmed:
        pending = PendingProfitImport.objects.filter(session_key=session_key).first()
        if not pending:
            return {"status": "no_pending"}
        count = commit_pending_profit_import(session_key)
        return {"status": "ok", "count": count, "replaced": True}

    records, warnings, source_files = parse_profit_files(files)
    label = (period_label or "").strip()

    if has_existing_profit_data():
        save_pending_profit_import(session_key, records, label, source_files)
        return {
            "status": "confirm_needed",
            "warnings": warnings,
            "total_rows": len(records),
            "period_label": label,
        }

    PendingProfitImport.objects.filter(session_key=session_key).delete()
    count = save_profit_records_directly(records, label)
    return {"status": "ok", "count": count, "warnings": warnings}


def _dict_to_model(data: dict, period_label: str) -> ProfitRecord:
    return ProfitRecord(
        item_code=data.get("item_code", ""),
        item_name=data.get("item_name", ""),
        customer_code=data.get("customer_code", ""),
        customer_name=data.get("customer_name", ""),
        category_label=data.get("category_label", ""),
        item_category_code=data.get("item_category_code", ""),
        customer_category_code=data.get("customer_category_code", ""),
        quantity=Decimal(data["quantity"]),
        cost=Decimal(data.get("cost", 0)),
        amount=Decimal(data["amount"]),
        is_unclassified_item=data.get("is_unclassified_item", False),
        is_unclassified_customer=data.get("is_unclassified_customer", False),
        period_label=period_label,
        source_file=data.get("source_file", ""),
    )
