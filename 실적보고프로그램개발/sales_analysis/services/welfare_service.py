"""복지부 출력항목·품목코드 매핑 조회·CRUD"""

from __future__ import annotations

import re

from django.db import transaction
from django.db.models import Prefetch

from sales_analysis.constants import (
    CATEGORY_CODE_ERROR,
    CATEGORY_CODE_PATTERN,
    WELFARE_ETC_GROUP_ID,
    WELFARE_OUTPUT_ITEMS,
)
from sales_analysis.models import WelfareOutputItem, WelfareOutputItemMapping

_CODE_RE = re.compile(CATEGORY_CODE_PATTERN)
_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_cache: dict[str, object] = {}


def invalidate_welfare_cache() -> None:
    _cache.clear()


def _active_items_qs():
    return WelfareOutputItem.objects.filter(is_active=True).order_by("sort_order", "code")


def parse_item_codes(raw: str) -> list[str]:
    if not raw or not str(raw).strip():
        return []
    parts = re.split(r"[,;\s]+", str(raw).strip().lower())
    codes: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if not part:
            continue
        if not _CODE_RE.match(part):
            raise ValueError(f"품목코드 '{part}'는 {CATEGORY_CODE_ERROR}")
        if part in seen:
            continue
        seen.add(part)
        codes.append(part)
    return codes


def _validate_slug(code: str) -> str:
    slug = (code or "").strip().lower()
    if not _SLUG_RE.match(slug):
        raise ValueError("내부코드는 영문 소문자로 시작하고, 영문·숫자·밑줄만 사용할 수 있습니다.")
    return slug


@transaction.atomic
def create_welfare_output_item(
    code: str,
    name: str,
    item_codes: str,
    *,
    is_active: bool = True,
    sort_order: int | None = None,
    is_fallback: bool = False,
) -> WelfareOutputItem:
    slug = _validate_slug(code)
    label = (name or "").strip()
    if not label:
        raise ValueError("출력항목명을 입력하세요.")
    if WelfareOutputItem.objects.filter(code=slug).exists():
        raise ValueError(f"내부코드 '{slug}'가 이미 있습니다.")
    if is_fallback and WelfareOutputItem.objects.filter(is_fallback=True).exists():
        raise ValueError("미매핑 기본항목은 하나만 지정할 수 있습니다.")

    if sort_order is None:
        last = WelfareOutputItem.objects.order_by("-sort_order").first()
        sort_order = (last.sort_order + 1) if last else 0

    item = WelfareOutputItem.objects.create(
        code=slug,
        name=label,
        is_active=is_active,
        sort_order=sort_order,
        is_fallback=is_fallback,
    )
    _replace_mappings(item, parse_item_codes(item_codes))
    invalidate_welfare_cache()
    return item


@transaction.atomic
def update_welfare_output_item(
    code: str,
    name: str,
    item_codes: str,
    *,
    is_active: bool = True,
    sort_order: int | None = None,
) -> WelfareOutputItem:
    slug = _validate_slug(code)
    item = WelfareOutputItem.objects.filter(code=slug).first()
    if not item:
        raise ValueError(f"출력항목 '{slug}'를 찾을 수 없습니다.")

    label = (name or "").strip()
    if not label:
        raise ValueError("출력항목명을 입력하세요.")

    item.name = label
    item.is_active = is_active
    if sort_order is not None:
        item.sort_order = sort_order
    item.save()
    _replace_mappings(item, parse_item_codes(item_codes))
    invalidate_welfare_cache()
    return item


@transaction.atomic
def delete_welfare_output_item(code: str) -> None:
    slug = _validate_slug(code)
    item = WelfareOutputItem.objects.filter(code=slug).first()
    if not item:
        raise ValueError(f"출력항목 '{slug}'를 찾을 수 없습니다.")
    if item.is_fallback:
        raise ValueError("미매핑 기본항목(기타)은 삭제할 수 없습니다.")
    item.delete()
    invalidate_welfare_cache()


def _replace_mappings(item: WelfareOutputItem, codes: list[str]) -> None:
    conflicts = (
        WelfareOutputItemMapping.objects.filter(item_category_code__in=codes)
        .exclude(welfare_item=item)
        .select_related("welfare_item")
    )
    if conflicts.exists():
        row = conflicts.first()
        assert row is not None
        raise ValueError(
            f"품목코드 '{row.item_category_code}'는 이미 '{row.welfare_item.name}'에 배정되어 있습니다."
        )

    item.mappings.all().delete()
    WelfareOutputItemMapping.objects.bulk_create(
        [
            WelfareOutputItemMapping(welfare_item=item, item_category_code=code)
            for code in codes
        ]
    )


def list_welfare_items_with_mappings() -> list[dict]:
    items = WelfareOutputItem.objects.prefetch_related(
        Prefetch(
            "mappings",
            queryset=WelfareOutputItemMapping.objects.order_by("item_category_code"),
        )
    ).order_by("sort_order", "code")
    rows: list[dict] = []
    for item in items:
        codes = [m.item_category_code for m in item.mappings.all()]
        rows.append(
            {
                "code": item.code,
                "name": item.name,
                "item_codes": ", ".join(codes),
                "item_codes_list": codes,
                "is_active": item.is_active,
                "sort_order": item.sort_order,
                "is_fallback": item.is_fallback,
            }
        )
    return rows


def seed_welfare_output_items() -> None:
    if WelfareOutputItem.objects.exists():
        return
    for index, (code, name, codes) in enumerate(WELFARE_OUTPUT_ITEMS):
        item = WelfareOutputItem.objects.create(
            code=code,
            name=name,
            is_active=True,
            sort_order=index,
            is_fallback=(code == WELFARE_ETC_GROUP_ID),
        )
        WelfareOutputItemMapping.objects.bulk_create(
            [
                WelfareOutputItemMapping(welfare_item=item, item_category_code=c)
                for c in codes
            ]
        )
    invalidate_welfare_cache()


def _build_item_to_group() -> dict[str, str]:
    mapping: dict[str, str] = {}
    items = WelfareOutputItem.objects.filter(is_active=True).order_by("sort_order", "code")
    for item in items.prefetch_related("mappings"):
        for m in item.mappings.all():
            code = m.item_category_code
            if code not in mapping:
                mapping[code] = item.code
    return mapping


def get_welfare_fallback_code() -> str:
    if "fallback" not in _cache:
        item = WelfareOutputItem.objects.filter(is_fallback=True, is_active=True).first()
        _cache["fallback"] = item.code if item else WELFARE_ETC_GROUP_ID
    return str(_cache["fallback"])


def get_welfare_group_order() -> list[str]:
    if "order" not in _cache:
        _cache["order"] = list(
            WelfareOutputItem.objects.filter(is_active=True)
            .order_by("sort_order", "code")
            .values_list("code", flat=True)
        )
    return list(_cache["order"])  # type: ignore[arg-type]


def get_welfare_group_labels() -> dict[str, str]:
    if "labels" not in _cache:
        _cache["labels"] = {
            row["code"]: row["name"]
            for row in WelfareOutputItem.objects.filter(is_active=True).values("code", "name")
        }
    return dict(_cache["labels"])  # type: ignore[arg-type]


def get_welfare_item_to_group() -> dict[str, str]:
    if "item_to_group" not in _cache:
        _cache["item_to_group"] = _build_item_to_group()
    return dict(_cache["item_to_group"])  # type: ignore[arg-type]


def welfare_group_for_item(item_category_code: str) -> str:
    code = (item_category_code or "").strip().lower()
    if not code:
        return get_welfare_fallback_code()
    return get_welfare_item_to_group().get(code, get_welfare_fallback_code())
