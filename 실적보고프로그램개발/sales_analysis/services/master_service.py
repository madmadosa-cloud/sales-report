"""
분류코드 마스터 조회·CRUD·엑셀 일괄 업로드
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from django.db import transaction
from django.db.models import Count

from sales_analysis.constants import (
    CATEGORY_CODE_ERROR,
    CATEGORY_CODE_PATTERN,
    MASTER_UPLOAD_MODE_MERGE,
    MASTER_UPLOAD_MODE_REPLACE,
    SEED_CUSTOMER_CATEGORIES,
    SEED_ITEM_CATEGORIES,
    UNCLASSIFIED_LABEL,
)
from sales_analysis.models import CustomerCategoryMaster, ItemCategoryMaster, SalesRecord

CategoryKind = Literal["item", "customer"]

_CODE_RE = re.compile(CATEGORY_CODE_PATTERN)


@dataclass
class CategoryUsage:
    code: str
    count: int


@dataclass
class MasterUploadPreview:
    kind: CategoryKind
    mode: str
    rows: list[tuple[str, str]]
    new_codes: list[str]
    updated_codes: list[str]
    removed_codes: list[str]


def invalidate_category_cache() -> None:
    """마스터 변경 후 캐시 무효화 (향후 캐시 도입 시 사용)"""
    return


def normalize_category_code(raw: str) -> str:
    return str(raw or "").strip().lower()


def validate_category_code(raw: str) -> str:
    code = normalize_category_code(raw)
    if not _CODE_RE.match(code):
        raise ValueError(CATEGORY_CODE_ERROR)
    return code


def get_item_category_map(active_only: bool = True) -> dict[str, str]:
    qs = ItemCategoryMaster.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    return {row.code: row.name for row in qs.order_by("sort_order", "code")}


def get_customer_category_map(active_only: bool = True) -> dict[str, str]:
    qs = CustomerCategoryMaster.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    return {row.code: row.name for row in qs.order_by("sort_order", "code")}


def get_item_category_order(active_only: bool = True) -> list[str]:
    return list(get_item_category_map(active_only).keys())


def get_customer_category_order(active_only: bool = True) -> list[str]:
    return list(get_customer_category_map(active_only).keys())


def get_all_item_codes() -> set[str]:
    return set(ItemCategoryMaster.objects.values_list("code", flat=True))


def get_all_customer_codes() -> set[str]:
    return set(CustomerCategoryMaster.objects.values_list("code", flat=True))


def resolve_item_category_name(code: str, active_only: bool = True) -> str:
    if not code:
        return UNCLASSIFIED_LABEL
    name = get_item_category_map(active_only).get(normalize_category_code(code))
    return name or UNCLASSIFIED_LABEL


def resolve_customer_category_name(code: str, active_only: bool = True) -> str:
    if not code:
        return UNCLASSIFIED_LABEL
    name = get_customer_category_map(active_only).get(normalize_category_code(code))
    return name or UNCLASSIFIED_LABEL


def is_known_item_code(code: str) -> bool:
    if not code:
        return False
    return normalize_category_code(code) in get_item_category_map(active_only=True)


def is_known_customer_code(code: str) -> bool:
    if not code:
        return False
    return normalize_category_code(code) in get_customer_category_map(active_only=True)


def classify_record_flags(item_code: str, customer_code: str) -> tuple[str, str, bool, bool]:
    item_cat = normalize_category_code(item_code) if item_code else ""
    cust_cat = normalize_category_code(customer_code) if customer_code else ""
    # extract prefix from full product/customer codes handled by classification.py
    return item_cat, cust_cat, not is_known_item_code(item_cat), not is_known_customer_code(cust_cat)


def get_item_usage(code: str) -> int:
    return SalesRecord.objects.filter(item_category_code=normalize_category_code(code)).count()


def get_customer_usage(code: str) -> int:
    return SalesRecord.objects.filter(customer_category_code=normalize_category_code(code)).count()


def _next_sort_order(model) -> int:
    last = model.objects.order_by("-sort_order").values_list("sort_order", flat=True).first()
    return (last or 0) + 1


def create_item_category(code: str, name: str, is_active: bool = True) -> ItemCategoryMaster:
    code = validate_category_code(code)
    name = name.strip()
    if not name:
        raise ValueError("분류명을 입력하세요.")
    if ItemCategoryMaster.objects.filter(code=code).exists():
        raise ValueError(f"코드 '{code}'는 이미 등록되어 있습니다. 수정만 가능합니다.")
    obj = ItemCategoryMaster.objects.create(
        code=code,
        name=name,
        is_active=is_active,
        sort_order=_next_sort_order(ItemCategoryMaster),
    )
    invalidate_category_cache()
    return obj


def create_customer_category(code: str, name: str, is_active: bool = True) -> CustomerCategoryMaster:
    code = validate_category_code(code)
    name = name.strip()
    if not name:
        raise ValueError("분류명을 입력하세요.")
    if CustomerCategoryMaster.objects.filter(code=code).exists():
        raise ValueError(f"코드 '{code}'는 이미 등록되어 있습니다. 수정만 가능합니다.")
    obj = CustomerCategoryMaster.objects.create(
        code=code,
        name=name,
        is_active=is_active,
        sort_order=_next_sort_order(CustomerCategoryMaster),
    )
    invalidate_category_cache()
    return obj


def update_item_category(code: str, name: str, is_active: bool) -> ItemCategoryMaster:
    code = validate_category_code(code)
    obj = ItemCategoryMaster.objects.filter(code=code).first()
    if not obj:
        raise ValueError(f"코드 '{code}'를 찾을 수 없습니다.")
    name = name.strip()
    if not name:
        raise ValueError("분류명을 입력하세요.")
    obj.name = name
    obj.is_active = is_active
    obj.save(update_fields=["name", "is_active"])
    invalidate_category_cache()
    return obj


def update_customer_category(code: str, name: str, is_active: bool) -> CustomerCategoryMaster:
    code = validate_category_code(code)
    obj = CustomerCategoryMaster.objects.filter(code=code).first()
    if not obj:
        raise ValueError(f"코드 '{code}'를 찾을 수 없습니다.")
    name = name.strip()
    if not name:
        raise ValueError("분류명을 입력하세요.")
    obj.name = name
def get_item_category_name_to_code(active_only: bool = True) -> dict[str, str]:
    result: dict[str, str] = {}
    for code, name in get_item_category_map(active_only).items():
        key = name.strip()
        if key:
            result[key] = code
            result[key.lower()] = code
    return result




def resolve_item_category_code_from_label(label: str, active_only: bool = True) -> tuple[str, bool]:
    """분류명(또는 코드) → (품목분류코드, 미분류 여부)"""
    text = (label or "").strip()
    if not text:
        return "", True
    code = normalize_category_code(text)
    if _CODE_RE.match(code) and is_known_item_code(code):
        return code, False
    name_map = get_item_category_name_to_code(active_only)
    matched = name_map.get(text) or name_map.get(text.lower())
    if matched:
        return matched, False
    return "", True



    obj.is_active = is_active
    obj.save(update_fields=["name", "is_active"])
    invalidate_category_cache()
    return obj


def delete_item_category(code: str, force: bool = False) -> None:
    code = validate_category_code(code)
    usage = get_item_usage(code)
    if usage and not force:
        raise ValueError(f"이 코드는 {usage:,}건의 매출 데이터에서 사용 중입니다.")
    with transaction.atomic():
        if usage and force:
            SalesRecord.objects.filter(item_category_code=code).update(is_unclassified_item=True)
        ItemCategoryMaster.objects.filter(code=code).delete()
    invalidate_category_cache()


def delete_customer_category(code: str, force: bool = False) -> None:
    code = validate_category_code(code)
    usage = get_customer_usage(code)
    if usage and not force:
        raise ValueError(f"이 코드는 {usage:,}건의 매출 데이터에서 사용 중입니다.")
    with transaction.atomic():
        if usage and force:
            SalesRecord.objects.filter(customer_category_code=code).update(is_unclassified_customer=True)
        CustomerCategoryMaster.objects.filter(code=code).delete()
    invalidate_category_cache()


def preview_master_upload(
    kind: CategoryKind,
    rows: list[tuple[str, str]],
    mode: str,
) -> MasterUploadPreview:
    normalized: list[tuple[str, str]] = []
    for raw_code, raw_name in rows:
        code = validate_category_code(raw_code)
        name = str(raw_name).strip()
        if not name:
            raise ValueError(f"코드 '{code}'의 분류명이 비어 있습니다.")
        normalized.append((code, name))

    model = ItemCategoryMaster if kind == "item" else CustomerCategoryMaster
    existing = {row.code: row.name for row in model.objects.all()}
    upload_codes = {code for code, _ in normalized}

    new_codes = sorted(upload_codes - set(existing))
    updated_codes = sorted(
        code for code, name in normalized if code in existing and existing[code] != name
    )
    removed_codes: list[str] = []
    if mode == MASTER_UPLOAD_MODE_REPLACE:
        removed_codes = sorted(set(existing) - upload_codes)

    return MasterUploadPreview(
        kind=kind,
        mode=mode,
        rows=normalized,
        new_codes=new_codes,
        updated_codes=updated_codes,
        removed_codes=removed_codes,
    )


def apply_master_upload(kind: CategoryKind, rows: list[tuple[str, str]], mode: str) -> dict:
    preview = preview_master_upload(kind, rows, mode)
    model = ItemCategoryMaster if kind == "item" else CustomerCategoryMaster

    with transaction.atomic():
        if mode == MASTER_UPLOAD_MODE_REPLACE:
            for code in preview.removed_codes:
                if kind == "item":
                    delete_item_category(code, force=True)
                else:
                    delete_customer_category(code, force=True)

        for idx, (code, name) in enumerate(preview.rows):
            obj = model.objects.filter(code=code).first()
            if obj:
                obj.name = name
                obj.is_active = True
                obj.sort_order = idx
                obj.save(update_fields=["name", "is_active", "sort_order"])
            else:
                model.objects.create(
                    code=code,
                    name=name,
                    is_active=True,
                    sort_order=idx,
                )

    invalidate_category_cache()
    return {
        "created": len(preview.new_codes),
        "updated": len(preview.updated_codes),
        "removed": len(preview.removed_codes),
        "total": len(preview.rows),
    }


def seed_initial_categories() -> None:
    """마스터가 비어 있을 때 초기 시드"""
    if not ItemCategoryMaster.objects.exists():
        for idx, (code, name) in enumerate(SEED_ITEM_CATEGORIES.items()):
            ItemCategoryMaster.objects.create(code=code, name=name, sort_order=idx)
    if not CustomerCategoryMaster.objects.exists():
        for idx, (code, name) in enumerate(SEED_CUSTOMER_CATEGORIES.items()):
            CustomerCategoryMaster.objects.create(code=code, name=name, sort_order=idx)


def summarize_unknown_codes(
    item_codes: set[str],
    customer_codes: set[str],
) -> list[str]:
    warnings: list[str] = []
    known_items = get_item_category_map()
    known_customers = get_customer_category_map()
    unknown_items = sorted(c for c in item_codes if c and c not in known_items)
    unknown_customers = sorted(c for c in customer_codes if c and c not in known_customers)
    if unknown_items:
        warnings.append(f"마스터에 없는 품목분류코드: {', '.join(unknown_items)}")
    if unknown_customers:
        warnings.append(f"마스터에 없는 거래처분류코드: {', '.join(unknown_customers)}")
    return warnings


def list_item_categories_with_usage() -> list[dict]:
    usage_map = dict(
        SalesRecord.objects.values("item_category_code")
        .annotate(cnt=Count("id"))
        .values_list("item_category_code", "cnt")
    )
    rows = []
    for obj in ItemCategoryMaster.objects.all():
        rows.append(
            {
                "code": obj.code,
                "name": obj.name,
                "is_active": obj.is_active,
                "sort_order": obj.sort_order,
                "usage_count": usage_map.get(obj.code, 0),
            }
        )
    return rows


def list_customer_categories_with_usage() -> list[dict]:
    usage_map = dict(
        SalesRecord.objects.values("customer_category_code")
        .annotate(cnt=Count("id"))
        .values_list("customer_category_code", "cnt")
    )
    rows = []
    for obj in CustomerCategoryMaster.objects.all():
        rows.append(
            {
                "code": obj.code,
                "name": obj.name,
                "is_active": obj.is_active,
                "sort_order": obj.sort_order,
                "usage_count": usage_map.get(obj.code, 0),
            }
        )
    return rows

