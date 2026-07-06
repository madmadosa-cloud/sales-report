"""
매출 집계 및 보고서 피벗 생성

Author: madmadosa-cloud
License: MIT
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db.models import Count, Q, QuerySet, Sum

from sales_analysis.constants import (
    FINAL_CUSTOMER_ORDER,
    FINAL_MAIN_MERGED_CODE,
    FINAL_MAIN_MERGED_LABEL,
    SIMPLE_CUSTOMER_ORDER,
    SIMPLE_MERGED_CODE,
    SIMPLE_MERGED_LABEL,
    STANDARD_CUSTOMER_CODES,
    UNCLASSIFIED_LABEL,
    WELFARE_ETC_GROUP_ID,
)
from sales_analysis.models import SalesRecord
from sales_analysis.services.master_service import (
    get_customer_category_map,
    get_customer_category_order,
    get_item_category_map,
    get_item_category_order,
    resolve_customer_category_name,
    resolve_item_category_name,
)
from sales_analysis.services.welfare_service import (
    get_welfare_group_labels,
    get_welfare_group_order,
    welfare_group_for_item,
)


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
    is_welfare: bool = False
    is_final: bool = False


SALES_ETC_SUMMARY_CODE = "__sales_etc_summary__"


def belongs_in_merged_group(
    cust_code: str,
    item_code: str,
    customer_categories: dict[str, str] | None = None,
    item_categories: dict[str, str] | None = None,
) -> bool:
    """간편보고서 통합 구간(기타·생산시설·미분류) 여부"""
    if customer_categories is None:
        customer_categories = get_customer_category_map()
    if item_categories is None:
        item_categories = get_item_category_map()
    if cust_code in ("e", "z"):
        return True
    if cust_code not in customer_categories:
        return True
    if item_code not in item_categories:
        return True
    if cust_code not in STANDARD_CUSTOMER_CODES:
        return True
    return False


def effective_final_customer_code(cust_code: str) -> str:
    if cust_code in STANDARD_CUSTOMER_CODES:
        return FINAL_MAIN_MERGED_CODE
    return SIMPLE_MERGED_CODE


def remap_bucket_for_final(
    bucket: dict[tuple[str, str, int], MonthMetrics],
) -> dict[tuple[str, str, int], MonthMetrics]:
    merged: dict[tuple[str, str, int], MonthMetrics] = defaultdict(MonthMetrics)
    for (cust, item, month), metrics in bucket.items():
        new_cust = effective_final_customer_code(cust)
        key = (new_cust, item, month)
        prev = merged[key]
        merged[key] = MonthMetrics(
            count=prev.count + metrics.count,
            quantity=prev.quantity + metrics.quantity,
            amount_won=prev.amount_won + metrics.amount_won,
        )
    return dict(merged)


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


def remap_bucket_for_welfare(
    bucket: dict[tuple[str, str, int], MonthMetrics],
) -> dict[tuple[str, str, int], MonthMetrics]:
    """품목분류코드를 복지부 출력항목으로 합산"""
    merged: dict[tuple[str, str, int], MonthMetrics] = defaultdict(MonthMetrics)
    for (cust, item, month), metrics in bucket.items():
        welfare_code = welfare_group_for_item(item)
        key = (cust, welfare_code, month)
        prev = merged[key]
        merged[key] = MonthMetrics(
            count=prev.count + metrics.count,
            quantity=prev.quantity + metrics.quantity,
            amount_won=prev.amount_won + metrics.amount_won,
        )
    return dict(merged)


def _customer_order(*, simple: bool, final: bool) -> list[str]:
    if final:
        return FINAL_CUSTOMER_ORDER
    if simple:
        return SIMPLE_CUSTOMER_ORDER
    return get_customer_category_order()


def _customer_label(
    cust_code: str,
    *,
    simple: bool,
    final: bool,
    customer_categories: dict[str, str],
) -> str:
    if final and cust_code == FINAL_MAIN_MERGED_CODE:
        return FINAL_MAIN_MERGED_LABEL
    if (simple or final) and cust_code == SIMPLE_MERGED_CODE:
        return SIMPLE_MERGED_LABEL
    return customer_categories.get(cust_code, UNCLASSIFIED_LABEL)


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


def _sales_trailing_etc_key(*, welfare: bool, final: bool) -> str:
    if welfare or final:
        return WELFARE_ETC_GROUP_ID
    return "z"


def _split_item_order(item_order: list[str], etc_key: str) -> tuple[list[str], str | None]:
    if etc_key not in item_order:
        return item_order, None
    main_order = [code for code in item_order if code != etc_key]
    return main_order, etc_key


def _merge_month_metrics(target: MonthMetrics, source: MonthMetrics) -> None:
    target.count += source.count
    target.quantity += source.quantity
    target.amount_won += source.amount_won


def _accumulate_trailing_item_for_customer(
    *,
    cust_code: str,
    trailing_key: str,
    bucket: dict[tuple[str, str, int], MonthMetrics],
    months: list[int],
    sub_month_cells: dict[int, ReportCell],
    global_etc_month_cells: dict[int, ReportCell],
) -> list[ReportCell]:
    period_cells: list[ReportCell] = []
    for month in months:
        metrics = bucket.get((cust_code, trailing_key, month), MonthMetrics())
        cell = _metrics_to_cell(metrics)
        period_cells.append(cell)
        _accumulate_month_cell(sub_month_cells, month, cell)
        _accumulate_month_cell(global_etc_month_cells, month, cell)
    return period_cells


def _accumulate_unclassified_items_for_customer(
    *,
    cust_code: str,
    trailing_key: str,
    bucket: dict[tuple[str, str, int], MonthMetrics],
    months: list[int],
    item_categories: dict[str, str],
    sub_month_cells: dict[int, ReportCell],
    global_etc_month_cells: dict[int, ReportCell],
) -> list[ReportCell]:
    period_cells: list[ReportCell] = []
    for month in months:
        combined = MonthMetrics()
        for (cust, item, bucket_month), metrics in bucket.items():
            if cust != cust_code or bucket_month != month:
                continue
            if item in item_categories or item == trailing_key:
                continue
            _merge_month_metrics(combined, metrics)
        cell = _metrics_to_cell(combined)
        period_cells.append(cell)
        _accumulate_month_cell(sub_month_cells, month, cell)
        _accumulate_month_cell(global_etc_month_cells, month, cell)
    return period_cells


def _append_global_etc_section(
    *,
    report_rows: list[ReportRow],
    global_etc_month_cells: dict[int, ReportCell],
    period_blocks: list[PeriodBlock],
    trailing_etc_key: str,
) -> None:
    etc_total = _sum_cells(list(global_etc_month_cells.values()))
    if not (etc_total.count or etc_total.quantity or etc_total.amount_thousand):
        return

    etc_label = "기타"
    report_rows.append(
        ReportRow(
            customer_label=etc_label,
            item_label="소계",
            row_type="subtotal",
            total=etc_total,
            months=global_etc_month_cells,
            blocks=_blocks_from_months(global_etc_month_cells, period_blocks),
            customer_code=SALES_ETC_SUMMARY_CODE,
        )
    )
    report_rows.append(
        ReportRow(
            customer_label=etc_label,
            item_label=etc_label,
            row_type="item",
            total=etc_total,
            months=global_etc_month_cells,
            blocks=_blocks_from_months(global_etc_month_cells, period_blocks),
            customer_code=SALES_ETC_SUMMARY_CODE,
            item_code=trailing_etc_key,
        )
    )


def build_sales_report(
    qs: QuerySet[SalesRecord],
    year: int,
    start_month: int,
    end_month: int,
    period_label: str = "",
    simple: bool = False,
    welfare: bool = False,
    final: bool = False,
) -> SalesReport:
    months = list(range(start_month, end_month + 1))
    period_blocks = get_period_blocks(start_month, end_month)
    filtered = qs.filter(month__gte=start_month, month__lte=end_month)
    bucket = aggregate_from_queryset(filtered)

    use_simple_customers = (simple or welfare) and not final
    if final:
        bucket = remap_bucket_for_final(bucket)
    elif use_simple_customers:
        bucket = remap_bucket_for_simple(bucket)
    if welfare or final:
        bucket = remap_bucket_for_welfare(bucket)

    item_categories = get_item_category_map()
    customer_categories = get_customer_category_map()
    use_welfare_axis = welfare or final
    item_order = get_welfare_group_order() if use_welfare_axis else get_item_category_order()
    trailing_etc_key = _sales_trailing_etc_key(welfare=welfare, final=final)
    main_item_order, trailing_item_key = _split_item_order(item_order, trailing_etc_key)

    unclassified_count = filtered.filter(
        Q(is_unclassified_item=True) | Q(is_unclassified_customer=True)
    ).count()

    report_rows: list[ReportRow] = []
    grand_month_cells: dict[int, ReportCell] = {m: _empty_cell() for m in months}
    all_item_cells_for_total: list[ReportCell] = []
    global_etc_month_cells: dict[int, ReportCell] = {m: _empty_cell() for m in months}

    for cust_code in _customer_order(simple=use_simple_customers, final=final):
        cust_name = _customer_label(
            cust_code,
            simple=use_simple_customers,
            final=final,
            customer_categories=customer_categories,
        )
        sub_month_cells: dict[int, ReportCell] = {m: _empty_cell() for m in months}
        section_rows: list[ReportRow] = []

        for item_code in main_item_order:
            if use_welfare_axis:
                item_name = get_welfare_group_labels()[item_code]
            else:
                item_name = item_categories[item_code]
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

        if trailing_item_key:
            etc_period_cells = _accumulate_trailing_item_for_customer(
                cust_code=cust_code,
                trailing_key=trailing_item_key,
                bucket=bucket,
                months=months,
                sub_month_cells=sub_month_cells,
                global_etc_month_cells=global_etc_month_cells,
            )
            for m, cell in zip(months, etc_period_cells):
                _accumulate_month_cell(grand_month_cells, m, cell)

        if not use_welfare_axis:
            unclassified_period_cells = _accumulate_unclassified_items_for_customer(
                cust_code=cust_code,
                trailing_key=trailing_item_key or "z",
                bucket=bucket,
                months=months,
                item_categories=item_categories,
                sub_month_cells=sub_month_cells,
                global_etc_month_cells=global_etc_month_cells,
            )
            for m, cell in zip(months, unclassified_period_cells):
                _accumulate_month_cell(grand_month_cells, m, cell)

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

    if not use_simple_customers and not final:
        unclassified_rows = _build_unclassified_section(
            bucket, months, period_blocks, item_categories, customer_categories
        )
        if unclassified_rows:
            report_rows.extend(unclassified_rows)
            for row in unclassified_rows:
                if row.row_type != "item":
                    continue
                all_item_cells_for_total.append(row.total)
                for month, cell in row.months.items():
                    _accumulate_month_cell(grand_month_cells, month, cell)

    global_etc_total = _sum_cells(list(global_etc_month_cells.values()))
    if global_etc_total.count or global_etc_total.quantity or global_etc_total.amount_thousand:
        all_item_cells_for_total.append(global_etc_total)
        _append_global_etc_section(
            report_rows=report_rows,
            global_etc_month_cells=global_etc_month_cells,
            period_blocks=period_blocks,
            trailing_etc_key=trailing_item_key or trailing_etc_key,
        )

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
    if welfare and "(복지부)" not in label:
        label = f"{label} (복지부)"
    elif final and "(최종)" not in label:
        label = f"{label} (최종)"
    elif simple and not welfare and "(간편)" not in label:
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
        is_simple=use_simple_customers,
        is_welfare=welfare,
        is_final=final,
    )


def _build_unclassified_section(
    bucket: dict[tuple[str, str, int], MonthMetrics],
    months: list[int],
    period_blocks: list[PeriodBlock],
    item_categories: dict[str, str],
    customer_categories: dict[str, str],
) -> list[ReportRow]:
    unclassified_keys = [
        k
        for k in bucket
        if k[0] not in customer_categories
    ]
    if not unclassified_keys:
        return []

    sub_month_cells: dict[int, ReportCell] = {m: _empty_cell() for m in months}
    rows: list[ReportRow] = []
    seen_combos = {(k[0], k[1]) for k in unclassified_keys}

    for cust_code, item_code in sorted(seen_combos):
        cust_name = customer_categories.get(cust_code, UNCLASSIFIED_LABEL)
        item_name = item_categories.get(item_code, UNCLASSIFIED_LABEL)
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
            "품목분류": resolve_item_category_name(r.item_category_code),
            "거래처코드": r.customer_code,
            "거래처분류": resolve_customer_category_name(r.customer_category_code),
            "수량": r.quantity,
            "합계": int(r.total),
        }
        for r in records
    ]
