"""
매출 집계 및 보고서 피벗 생성
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db.models import Count, Q, QuerySet, Sum

from sales_analysis.constants import (
    CUSTOMER_CATEGORIES,
    CUSTOMER_CATEGORY_ORDER,
    ITEM_CATEGORIES,
    ITEM_CATEGORY_ORDER,
    SIMPLE_CUSTOMER_ORDER,
    SIMPLE_MERGED_CODE,
    SIMPLE_MERGED_LABEL,
    STANDARD_CUSTOMER_CODES,
    UNCLASSIFIED_LABEL,
)
from sales_analysis.models import SalesRecord


@dataclass
class MonthMetrics:
    count: int = 0
    quantity: Decimal = field(default_factory=lambda: Decimal("0"))
    amount_won: Decimal = field(default_factory=lambda: Decimal("0"))

    @property
    def amount_thousand(self) -> int:
        return int((self.amount_won / Decimal("1000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@dataclass
class ReportCell:
    count: int = 0
    quantity: Decimal = field(default_factory=lambda: Decimal("0"))
    amount_thousand: int = 0


@dataclass
class PeriodBlock:
    """6개월 단위 소계 구간 (상반기 1~6월 / 하반기 7~12월)"""

    block_id: str
    label: str
    start_month: int
    end_month: int


@dataclass
class ReportRow:
    customer_label: str
    item_label: str
    row_type: str  # total | subtotal | item
    total: ReportCell
    months: dict[int, ReportCell]
    blocks: dict[str, ReportCell] = field(default_factory=dict)
    customer_code: str = ""
    item_code: str = ""


@dataclass
class SalesReport:
    year: int
    start_month: int
    end_month: int
    period_label: str
    months: list[int]
    period_blocks: list[PeriodBlock]
    rows: list[ReportRow]
    unclassified_count: int = 0
    is_simple: bool = False


def belongs_in_merged_group(cust_code: str, item_code: str) -> bool:
    """간편보고서 통합 구간(기타·생산시설·미분류) 여부"""
    if cust_code in ("e", "z"):
        return True
    if cust_code not in CUSTOMER_CATEGORIES:
        return True
    if item_code not in ITEM_CATEGORIES:
        return True
    if cust_code not in STANDARD_CUSTOMER_CODES:
        return True
    return False


def effective_customer_code(cust_code: str, item_code: str, simple: bool) -> str:
    if not simple:
        return cust_code
    if belongs_in_merged_group(cust_code, item_code):
        return SIMPLE_MERGED_CODE
    return cust_code


def remap_bucket_for_simple(
    bucket: dict[tuple[str, str, int], MonthMetrics],
) -> dict[tuple[str, str, int], MonthMetrics]:
    merged: dict[tuple[str, str, int], MonthMetrics] = defaultdict(MonthMetrics)
    for (cust, item, month), metrics in bucket.items():
        new_cust = effective_customer_code(cust, item, simple=True)
        key = (new_cust, item, month)
        prev = merged[key]
        merged[key] = MonthMetrics(
            count=prev.count + metrics.count,
            quantity=prev.quantity + metrics.quantity,
            amount_won=prev.amount_won + metrics.amount_won,
        )
    return dict(merged)


def _customer_order(simple: bool) -> list[str]:
    return SIMPLE_CUSTOMER_ORDER if simple else CUSTOMER_CATEGORY_ORDER


def _customer_label(cust_code: str, simple: bool) -> str:
    if simple and cust_code == SIMPLE_MERGED_CODE:
        return SIMPLE_MERGED_LABEL
    return CUSTOMER_CATEGORIES.get(cust_code, UNCLASSIFIED_LABEL)


def get_period_blocks(start_month: int, end_month: int) -> list[PeriodBlock]:
    """선택 기간을 6개월 단위(1~6월 / 7~12월)로 나눈 소계 구간"""
    blocks: list[PeriodBlock] = []
    if start_month <= 6:
        b_start = start_month
        b_end = min(end_month, 6)
        if b_start <= b_end:
            label = "상반기 소계" if b_start == 1 and b_end == 6 else f"{b_start}~{b_end}월 소계"
            blocks.append(PeriodBlock("h1", label, b_start, b_end))
    if end_month >= 7:
        b_start = max(start_month, 7)
        b_end = end_month
        if b_start <= b_end:
            label = "하반기 소계" if b_start == 7 and b_end == 12 else f"{b_start}~{b_end}월 소계"
            blocks.append(PeriodBlock("h2", label, b_start, b_end))
    return blocks


def aggregate_from_queryset(qs: QuerySet[SalesRecord]) -> dict[tuple[str, str, int], MonthMetrics]:
    """
    거래처분류 × 품목분류 × 월 집계.
    건수 = 행 개수, 수량 = 수량 합, 금액 = 합계 sum.
    """
    bucket: dict[tuple[str, str, int], MonthMetrics] = defaultdict(MonthMetrics)

    for row in (
        qs.values("customer_category_code", "item_category_code", "month")
        .annotate(
            amount_won=Sum("total"),
            quantity_sum=Sum("quantity"),
            row_count=Count("id"),
        )
    ):
        key = (
            str(row["customer_category_code"] or ""),
            str(row["item_category_code"] or ""),
            int(row["month"]),
        )
        bucket[key].amount_won = Decimal(str(row["amount_won"] or 0))
        bucket[key].quantity = Decimal(str(row["quantity_sum"] or 0))
        bucket[key].count = int(row["row_count"] or 0)

    return dict(bucket)


def _empty_cell() -> ReportCell:
    return ReportCell()


def _sum_cells(cells: list[ReportCell]) -> ReportCell:
    return ReportCell(
        count=sum(c.count for c in cells),
        quantity=sum((c.quantity for c in cells), Decimal("0")),
        amount_thousand=sum(c.amount_thousand for c in cells),
    )


def _metrics_to_cell(m: MonthMetrics) -> ReportCell:
    return ReportCell(count=m.count, quantity=m.quantity, amount_thousand=m.amount_thousand)


def _blocks_from_months(
    months: dict[int, ReportCell],
    period_blocks: list[PeriodBlock],
) -> dict[str, ReportCell]:
    blocks: dict[str, ReportCell] = {}
    for block in period_blocks:
        cells = [
            months[m]
            for m in range(block.start_month, block.end_month + 1)
            if m in months
        ]
        blocks[block.block_id] = _sum_cells(cells) if cells else _empty_cell()
    return blocks


def _accumulate_month_cell(target: dict[int, ReportCell], month: int, cell: ReportCell) -> None:
    prev = target.get(month, _empty_cell())
    target[month] = ReportCell(
        count=prev.count + cell.count,
        quantity=prev.quantity + cell.quantity,
        amount_thousand=prev.amount_thousand + cell.amount_thousand,
    )


def build_sales_report(
    qs: QuerySet[SalesRecord],
    year: int,
    start_month: int,
    end_month: int,
    period_label: str = "",
    simple: bool = False,
) -> SalesReport:
    months = list(range(start_month, end_month + 1))
    period_blocks = get_period_blocks(start_month, end_month)
    filtered = qs.filter(month__gte=start_month, month__lte=end_month)
    bucket = aggregate_from_queryset(filtered)
    if simple:
        bucket = remap_bucket_for_simple(bucket)

    unclassified_count = filtered.filter(
        Q(is_unclassified_item=True) | Q(is_unclassified_customer=True)
    ).count()

    report_rows: list[ReportRow] = []
    grand_month_cells: dict[int, ReportCell] = {m: _empty_cell() for m in months}
    all_item_cells_for_total: list[ReportCell] = []

    for cust_code in _customer_order(simple):
        cust_name = _customer_label(cust_code, simple)
        sub_month_cells: dict[int, ReportCell] = {m: _empty_cell() for m in months}
        section_rows: list[ReportRow] = []

        for item_code in ITEM_CATEGORY_ORDER:
            item_name = ITEM_CATEGORIES[item_code]
            month_cells: dict[int, ReportCell] = {}
            row_period_cells: list[ReportCell] = []

            for m in months:
                metrics = bucket.get((cust_code, item_code, m), MonthMetrics())
                cell = _metrics_to_cell(metrics)
                month_cells[m] = cell
                row_period_cells.append(cell)
                _accumulate_month_cell(sub_month_cells, m, cell)
                _accumulate_month_cell(grand_month_cells, m, cell)

            row_total = _sum_cells(row_period_cells)
            all_item_cells_for_total.append(row_total)
            section_rows.append(
                ReportRow(
                    customer_label=cust_name,
                    item_label=item_name,
                    row_type="item",
                    total=row_total,
                    months=month_cells,
                    blocks=_blocks_from_months(month_cells, period_blocks),
                    customer_code=cust_code,
                    item_code=item_code,
                )
            )

        subtotal_row = ReportRow(
            customer_label=cust_name,
            item_label="소계",
            row_type="subtotal",
            total=_sum_cells(list(sub_month_cells.values())),
            months=sub_month_cells,
            blocks=_blocks_from_months(sub_month_cells, period_blocks),
            customer_code=cust_code,
        )
        report_rows.append(subtotal_row)
        report_rows.extend(section_rows)

    if not simple:
        unclassified_rows = _build_unclassified_section(bucket, months, period_blocks)
        if unclassified_rows:
            report_rows.extend(unclassified_rows)

    grand_total = _sum_cells(all_item_cells_for_total)
    total_row = ReportRow(
        customer_label="총계",
        item_label="",
        row_type="total",
        total=grand_total,
        months=grand_month_cells,
        blocks=_blocks_from_months(grand_month_cells, period_blocks),
    )

    label = period_label or _default_period_label(year, start_month, end_month)
    if simple and "(간편)" not in label:
        label = f"{label} (간편)"

    return SalesReport(
        year=year,
        start_month=start_month,
        end_month=end_month,
        period_label=label,
        months=months,
        period_blocks=period_blocks,
        rows=[total_row] + report_rows,
        unclassified_count=unclassified_count,
        is_simple=simple,
    )


def _build_unclassified_section(
    bucket: dict[tuple[str, str, int], MonthMetrics],
    months: list[int],
    period_blocks: list[PeriodBlock],
) -> list[ReportRow]:
    unclassified_keys = [
        k
        for k in bucket
        if k[0] not in CUSTOMER_CATEGORIES or k[1] not in ITEM_CATEGORIES
    ]
    if not unclassified_keys:
        return []

    sub_month_cells: dict[int, ReportCell] = {m: _empty_cell() for m in months}
    rows: list[ReportRow] = []
    seen_combos = {(k[0], k[1]) for k in unclassified_keys}

    for cust_code, item_code in sorted(seen_combos):
        cust_name = CUSTOMER_CATEGORIES.get(cust_code, UNCLASSIFIED_LABEL)
        item_name = ITEM_CATEGORIES.get(item_code, UNCLASSIFIED_LABEL)
        month_cells: dict[int, ReportCell] = {}
        row_period: list[ReportCell] = []
        for m in months:
            metrics = bucket.get((cust_code, item_code, m), MonthMetrics())
            cell = _metrics_to_cell(metrics)
            month_cells[m] = cell
            row_period.append(cell)
            _accumulate_month_cell(sub_month_cells, m, cell)
        rows.append(
            ReportRow(
                customer_label=cust_name,
                item_label=item_name,
                row_type="item",
                total=_sum_cells(row_period),
                months=month_cells,
                blocks=_blocks_from_months(month_cells, period_blocks),
                customer_code=cust_code,
                item_code=item_code,
            )
        )

    rows.insert(
        0,
        ReportRow(
            customer_label=UNCLASSIFIED_LABEL,
            item_label="소계",
            row_type="subtotal",
            total=_sum_cells(list(sub_month_cells.values())),
            months=sub_month_cells,
            blocks=_blocks_from_months(sub_month_cells, period_blocks),
        ),
    )
    return rows


def _default_period_label(year: int, start_month: int, end_month: int) -> str:
    if start_month == 1 and end_month == 6:
        return f"{year}년 상반기"
    if start_month == 7 and end_month == 12:
        return f"{year}년 하반기"
    if start_month == 1 and end_month == 12:
        return f"{year}년 연간"
    return f"{year}년 {start_month}월~{end_month}월"


def get_unclassified_records(qs: QuerySet[SalesRecord]) -> list[dict[str, Any]]:
    records = qs.filter(
        Q(is_unclassified_item=True) | Q(is_unclassified_customer=True)
    ).order_by("year", "month", "voucher_no")
    return [
        {
            "연도": r.year,
            "월": r.month,
            "전표별": r.voucher_no,
            "품목코드": r.item_code,
            "품목분류": r.item_category_name,
            "거래처코드": r.customer_code,
            "거래처분류": r.customer_category_name,
            "수량": r.quantity,
            "합계": int(r.total),
        }
        for r in records
    ]
