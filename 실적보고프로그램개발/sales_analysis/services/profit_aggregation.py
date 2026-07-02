"""이익현황 거래처분류·품목분류별 집계"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Q, QuerySet, Sum

from sales_analysis.constants import (
    FINAL_CUSTOMER_ORDER,
    FINAL_MAIN_MERGED_CODE,
    FINAL_MAIN_MERGED_LABEL,
    SIMPLE_CUSTOMER_ORDER,
    SIMPLE_MERGED_CODE,
    SIMPLE_MERGED_LABEL,
    STANDARD_CUSTOMER_CODES,
    UNCLASSIFIED_LABEL,
)
from sales_analysis.models import ProfitRecord
from sales_analysis.services.aggregation import effective_customer_code
from sales_analysis.services.classification import extract_customer_category_code
from sales_analysis.services.master_service import (
    get_customer_category_map,
    get_customer_category_order,
    get_item_category_map,
    get_item_category_order,
    is_known_customer_code,
    is_known_item_code,
    resolve_customer_category_name,
    resolve_item_category_name,
)
from sales_analysis.services.welfare_service import (
    get_welfare_group_labels,
    get_welfare_group_order,
    welfare_group_for_item,
)

UNCLASSIFIED_CUSTOMER_KEY = "__unclassified_customer__"
UNCLASSIFIED_ITEM_KEY = "__unclassified_item__"


def _empty_bucket_cell() -> dict:
    return {"quantity": Decimal("0"), "cost": Decimal("0"), "amount": Decimal("0")}


@dataclass
class ProfitRow:
    customer_label: str
    item_label: str
    quantity: Decimal
    cost: Decimal
    cost_thousand: int
    amount: Decimal
    amount_thousand: int
    row_type: str = "item"
    customer_code: str = ""
    item_code: str = ""


@dataclass
class ProfitReport:
    period_label: str
    rows: list[ProfitRow]
    is_welfare: bool = False
    is_final: bool = False
    unclassified_count: int = 0

    @property
    def axis_label(self) -> str:
        return "출력항목" if self.is_welfare else "품목분류"


def _aggregate_profit_totals(qs: QuerySet[ProfitRecord]) -> dict[str, Decimal]:
    row = qs.aggregate(
        quantity=Sum("quantity"),
        cost=Sum("cost"),
        amount=Sum("amount"),
    )
    return {
        "quantity": Decimal(str(row["quantity"] or 0)),
        "cost": Decimal(str(row["cost"] or 0)),
        "amount": Decimal(str(row["amount"] or 0)),
    }


def _to_thousand(amount: Decimal) -> int:
    return int((amount / Decimal("1000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def get_profit_period_label() -> str:
    latest = ProfitRecord.objects.order_by("-created_at").first()
    return (latest.period_label if latest and latest.period_label else "이익분석").strip()


def _resolve_customer_code(record: ProfitRecord) -> str:
    code = (record.customer_category_code or "").strip().lower()
    if code and is_known_customer_code(code):
        return code
    derived = extract_customer_category_code(record.customer_code)
    if derived and is_known_customer_code(derived):
        return derived
    if record.is_unclassified_customer or not derived:
        return UNCLASSIFIED_CUSTOMER_KEY
    return derived


def _resolve_item_key(record: ProfitRecord) -> str:
    code = (record.item_category_code or "").strip().lower()
    if record.is_unclassified_item or not code or not is_known_item_code(code):
        return UNCLASSIFIED_ITEM_KEY
    return code


def _build_raw_bucket(qs: QuerySet[ProfitRecord]) -> dict[tuple[str, str], dict]:
    buckets: dict[tuple[str, str], dict] = defaultdict(_empty_bucket_cell)
    for record in qs.iterator():
        cust_key = _resolve_customer_code(record)
        item_key = _resolve_item_key(record)
        bucket = buckets[(cust_key, item_key)]
        bucket["quantity"] += record.quantity
        bucket["cost"] += record.cost
        bucket["amount"] += record.amount
    return buckets


def _remap_bucket_for_simple_customers(
    bucket: dict[tuple[str, str], dict],
) -> dict[tuple[str, str], dict]:
    merged: dict[tuple[str, str], dict] = defaultdict(_empty_bucket_cell)
    for (cust, item), metrics in bucket.items():
        new_cust = effective_customer_code(cust, item, simple=True)
        cell = merged[(new_cust, item)]
        cell["quantity"] += metrics["quantity"]
        cell["cost"] += metrics["cost"]
        cell["amount"] += metrics["amount"]
    return dict(merged)


def _remap_bucket_for_welfare_items(
    bucket: dict[tuple[str, str], dict],
) -> dict[tuple[str, str], dict]:
    merged: dict[tuple[str, str], dict] = defaultdict(_empty_bucket_cell)
    for (cust, item), metrics in bucket.items():
        welfare_key = welfare_group_for_item(item if item != UNCLASSIFIED_ITEM_KEY else "")
        cell = merged[(cust, welfare_key)]
        cell["quantity"] += metrics["quantity"]
        cell["cost"] += metrics["cost"]
        cell["amount"] += metrics["amount"]
    return dict(merged)


def _remap_bucket_for_final_customers(
    bucket: dict[tuple[str, str], dict],
) -> dict[tuple[str, str], dict]:
    merged: dict[tuple[str, str], dict] = defaultdict(_empty_bucket_cell)
    for (cust, item), metrics in bucket.items():
        if cust in STANDARD_CUSTOMER_CODES:
            new_cust = FINAL_MAIN_MERGED_CODE
        else:
            new_cust = SIMPLE_MERGED_CODE
        cell = merged[(new_cust, item)]
        cell["quantity"] += metrics["quantity"]
        cell["cost"] += metrics["cost"]
        cell["amount"] += metrics["amount"]
    return dict(merged)


def _build_bucket(
    qs: QuerySet[ProfitRecord], *, welfare: bool, final: bool = False
) -> dict[tuple[str, str], dict]:
    bucket = _build_raw_bucket(qs)
    if welfare:
        bucket = _remap_bucket_for_simple_customers(bucket)
        bucket = _remap_bucket_for_welfare_items(bucket)
    elif final:
        bucket = _remap_bucket_for_final_customers(bucket)
    return bucket


def _item_label(item_key: str, *, welfare: bool, item_categories: dict[str, str]) -> str:
    if welfare:
        return get_welfare_group_labels().get(item_key, item_key)
    if item_key == UNCLASSIFIED_ITEM_KEY:
        return UNCLASSIFIED_LABEL
    return item_categories.get(item_key, resolve_item_category_name(item_key))


def build_profit_report(
    qs: QuerySet[ProfitRecord] | None = None,
    *,
    welfare: bool = False,
    final: bool = False,
) -> ProfitReport:
    if qs is None:
        qs = ProfitRecord.objects.all()

    period_label = get_profit_period_label()
    bucket = _build_bucket(qs, welfare=welfare, final=final)
    customer_categories = get_customer_category_map()
    item_categories = get_item_category_map()
    item_order = get_welfare_group_order() if welfare else get_item_category_order()
    if final:
        customer_order = FINAL_CUSTOMER_ORDER
    elif welfare:
        customer_order = SIMPLE_CUSTOMER_ORDER
    else:
        customer_order = get_customer_category_order()

    unclassified_count = qs.filter(
        Q(is_unclassified_item=True) | Q(is_unclassified_customer=True)
    ).count()

    report_rows: list[ProfitRow] = []
    db_totals = _aggregate_profit_totals(qs)

    def append_section(cust_key: str, cust_name: str) -> None:
        section_qty = Decimal("0")
        section_cost = Decimal("0")
        section_amount = Decimal("0")
        section_items: list[ProfitRow] = []

        for item_key in item_order:
            cell = bucket.get((cust_key, item_key), {})
            qty = cell.get("quantity", Decimal("0"))
            cost = cell.get("cost", Decimal("0"))
            amount = cell.get("amount", Decimal("0"))
            section_qty += qty
            section_cost += cost
            section_amount += amount
            section_items.append(
                ProfitRow(
                    customer_label=cust_name,
                    item_label=_item_label(item_key, welfare=welfare, item_categories=item_categories),
                    quantity=qty,
                    cost=cost,
                    cost_thousand=_to_thousand(cost),
                    amount=amount,
                    amount_thousand=_to_thousand(amount),
                    row_type="item",
                    customer_code=cust_key,
                    item_code=item_key,
                )
            )

        if not welfare:
            unitem = bucket.get((cust_key, UNCLASSIFIED_ITEM_KEY), {})
            uqty = unitem.get("quantity", Decimal("0"))
            ucost = unitem.get("cost", Decimal("0"))
            uamount = unitem.get("amount", Decimal("0"))
            if uqty or ucost or uamount:
                section_qty += uqty
                section_cost += ucost
                section_amount += uamount
                section_items.append(
                    ProfitRow(
                        customer_label=cust_name,
                        item_label=UNCLASSIFIED_LABEL,
                        quantity=uqty,
                        cost=ucost,
                        cost_thousand=_to_thousand(ucost),
                        amount=uamount,
                        amount_thousand=_to_thousand(uamount),
                        row_type="item",
                        customer_code=cust_key,
                        item_code=UNCLASSIFIED_ITEM_KEY,
                    )
                )

        report_rows.append(
            ProfitRow(
                customer_label=cust_name,
                item_label="소계",
                quantity=section_qty,
                cost=section_cost,
                cost_thousand=_to_thousand(section_cost),
                amount=section_amount,
                amount_thousand=_to_thousand(section_amount),
                row_type="subtotal",
                customer_code=cust_key,
            )
        )
        report_rows.extend(section_items)

    for cust_code in customer_order:
        if final and cust_code == FINAL_MAIN_MERGED_CODE:
            cust_name = FINAL_MAIN_MERGED_LABEL
        elif (welfare or final) and cust_code == SIMPLE_MERGED_CODE:
            cust_name = SIMPLE_MERGED_LABEL
        else:
            cust_name = customer_categories.get(
                cust_code, resolve_customer_category_name(cust_code)
            )
        append_section(cust_code, cust_name)

    if not welfare and not final:
        uncust = any(
            cust_key == UNCLASSIFIED_CUSTOMER_KEY
            and (v["quantity"] or v["cost"] or v["amount"])
            for (cust_key, _), v in bucket.items()
        )
        if uncust:
            append_section(UNCLASSIFIED_CUSTOMER_KEY, UNCLASSIFIED_LABEL)

    total_row = ProfitRow(
        customer_label="총계",
        item_label="",
        quantity=db_totals["quantity"],
        cost=db_totals["cost"],
        cost_thousand=_to_thousand(db_totals["cost"]),
        amount=db_totals["amount"],
        amount_thousand=_to_thousand(db_totals["amount"]),
        row_type="total",
    )

    title = period_label
    if welfare:
        title = f"{period_label} (복지부)"
    elif final:
        title = f"{period_label} (최종)"

    return ProfitReport(
        period_label=title,
        rows=[total_row, *report_rows],
        is_welfare=welfare,
        is_final=final,
        unclassified_count=unclassified_count,
    )
