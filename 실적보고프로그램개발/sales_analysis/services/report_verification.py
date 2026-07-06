"""
보고서 생성 시 집계 검증
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Count, Q, QuerySet, Sum

from sales_analysis.constants import (
    FINAL_CUSTOMER_ORDER,
    SIMPLE_CUSTOMER_ORDER,
    WELFARE_ETC_GROUP_ID,
)
from sales_analysis.models import SalesRecord
from sales_analysis.services.welfare_service import welfare_group_for_item
from sales_analysis.services.aggregation import (
    ReportCell,
    SALES_ETC_SUMMARY_CODE,
    SalesReport,
    aggregate_from_queryset,
    effective_customer_code,
    effective_final_customer_code,
    remap_bucket_for_final,
    remap_bucket_for_simple,
    remap_bucket_for_welfare,
)
from sales_analysis.services.master_service import (
    get_customer_category_map,
    get_customer_category_order,
    get_item_category_map,
    get_item_category_order,
)


@dataclass
class VerificationCheck:
    check_id: str
    label: str
    passed: bool
    detail: str


@dataclass
class ReportVerificationResult:
    passed: bool
    checks: list[VerificationCheck] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    db_row_count: int = 0
    standard_row_count: int = 0
    unclassified_row_count: int = 0
    report_grand_count: int = 0
    report_grand_amount_thousand: int = 0
    missing_months: list[int] = field(default_factory=list)


def _report_trailing_etc_key(report: SalesReport) -> str:
    if report.is_welfare or report.is_final:
        return WELFARE_ETC_GROUP_ID
    return "z"


def _report_customer_codes(report: SalesReport) -> list[str]:
    if report.is_final:
        return FINAL_CUSTOMER_ORDER
    if report.is_simple or report.is_welfare:
        return SIMPLE_CUSTOMER_ORDER
    return get_customer_category_order()


def _etc_bucket_slice(
    manual: dict[tuple[str, str, int], dict],
    *,
    cust_code: str,
    month: int,
    trailing_etc: str,
    include_unclassified_items: bool,
    item_categories: dict[str, str],
) -> dict:
    result = {
        "row_count": 0,
        "amount_won": Decimal(0),
        "quantity_sum": Decimal(0),
    }
    base = manual.get((cust_code, trailing_etc, month))
    if base:
        result["row_count"] += base["row_count"]
        result["amount_won"] += base["amount_won"]
        result["quantity_sum"] += base["quantity_sum"]
    if include_unclassified_items:
        for (cust, item, bucket_month), data in manual.items():
            if cust != cust_code or bucket_month != month:
                continue
            if item in item_categories or item == trailing_etc:
                continue
            result["row_count"] += data["row_count"]
            result["amount_won"] += data["amount_won"]
            result["quantity_sum"] += data["quantity_sum"]
    return result


def _expected_global_etc_for_month(
    manual: dict[tuple[str, str, int], dict],
    *,
    month: int,
    customer_codes: list[str],
    trailing_etc: str,
    include_unclassified_items: bool,
    item_categories: dict[str, str],
) -> dict:
    result = {
        "row_count": 0,
        "amount_won": Decimal(0),
        "quantity_sum": Decimal(0),
    }
    for cust_code in customer_codes:
        slice_data = _etc_bucket_slice(
            manual,
            cust_code=cust_code,
            month=month,
            trailing_etc=trailing_etc,
            include_unclassified_items=include_unclassified_items,
            item_categories=item_categories,
        )
        result["row_count"] += slice_data["row_count"]
        result["amount_won"] += slice_data["amount_won"]
        result["quantity_sum"] += slice_data["quantity_sum"]
    return result


def _manual_group_counts(qs: QuerySet[SalesRecord]) -> dict[tuple[str, str, int], dict]:
    result: dict[tuple[str, str, int], dict] = {}
    for row in qs.values("customer_category_code", "item_category_code", "month").annotate(
        row_count=Count("id"),
        amount_won=Sum("total"),
        quantity_sum=Sum("quantity"),
    ):
        key = (
            str(row["customer_category_code"] or ""),
            str(row["item_category_code"] or ""),
            int(row["month"]),
        )
        result[key] = {
            "row_count": int(row["row_count"]),
            "amount_won": Decimal(str(row["amount_won"] or 0)),
            "quantity_sum": Decimal(str(row["quantity_sum"] or 0)),
        }
    return result


def _remap_manual_for_simple(manual: dict[tuple[str, str, int], dict]) -> dict[tuple[str, str, int], dict]:
    from collections import defaultdict

    merged: dict[tuple[str, str, int], dict] = defaultdict(
        lambda: {"row_count": 0, "amount_won": Decimal(0), "quantity_sum": Decimal(0)}
    )
    for (cust, item, month), m in manual.items():
        new_cust = effective_customer_code(cust, item, simple=True)
        key = (new_cust, item, month)
        merged[key]["row_count"] += m["row_count"]
        merged[key]["amount_won"] += m["amount_won"]
        merged[key]["quantity_sum"] += m["quantity_sum"]
    return dict(merged)


def _remap_manual_for_final(manual: dict[tuple[str, str, int], dict]) -> dict[tuple[str, str, int], dict]:
    from collections import defaultdict

    merged: dict[tuple[str, str, int], dict] = defaultdict(
        lambda: {"row_count": 0, "amount_won": Decimal(0), "quantity_sum": Decimal(0)}
    )
    for (cust, item, month), m in manual.items():
        new_cust = effective_final_customer_code(cust)
        key = (new_cust, item, month)
        merged[key]["row_count"] += m["row_count"]
        merged[key]["amount_won"] += m["amount_won"]
        merged[key]["quantity_sum"] += m["quantity_sum"]
    return dict(merged)


def _remap_manual_for_welfare(manual: dict[tuple[str, str, int], dict]) -> dict[tuple[str, str, int], dict]:
    from collections import defaultdict

    merged: dict[tuple[str, str, int], dict] = defaultdict(
        lambda: {"row_count": 0, "amount_won": Decimal(0), "quantity_sum": Decimal(0)}
    )
    for (cust, item, month), m in manual.items():
        welfare_code = welfare_group_for_item(item)
        key = (cust, welfare_code, month)
        merged[key]["row_count"] += m["row_count"]
        merged[key]["amount_won"] += m["amount_won"]
        merged[key]["quantity_sum"] += m["quantity_sum"]
    return dict(merged)


def _amount_to_thousand(amount: Decimal) -> int:
    return int((amount / Decimal("1000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def verify_report(
    qs: QuerySet[SalesRecord],
    report: SalesReport,
    year: int,
    start_month: int,
    end_month: int,
) -> ReportVerificationResult:
    """보고서 기간·집계 결과 검증"""
    result = ReportVerificationResult(passed=True)
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[VerificationCheck] = []

    period_qs = qs.filter(year=year, month__gte=start_month, month__lte=end_month)
    result.db_row_count = period_qs.count()
    result.unclassified_row_count = period_qs.filter(
        Q(is_unclassified_item=True) | Q(is_unclassified_customer=True)
    ).count()
    result.standard_row_count = result.db_row_count - result.unclassified_row_count
    result.report_grand_count = report.rows[0].total.count if report.rows else 0
    result.report_grand_amount_thousand = report.rows[0].total.amount_thousand if report.rows else 0

    months_in_period = list(range(start_month, end_month + 1))
    stored_months = set(
        period_qs.values_list("month", flat=True).distinct()
    )
    result.missing_months = [m for m in months_in_period if m not in stored_months]

    # 1) 기간 내 DB 원자료 존재
    checks.append(
        VerificationCheck(
            check_id="db_rows",
            label="DB 원자료 행 수",
            passed=result.db_row_count > 0,
            detail=f"기간 내 저장 행 {result.db_row_count:,}건",
        )
    )
    if result.db_row_count == 0:
        errors.append("선택 기간에 저장된 매출 데이터가 없습니다.")

    # 2) 누락 월 (경고)
    if result.missing_months:
        months_text = ", ".join(f"{m}월" for m in result.missing_months)
        warnings.append(f"선택 기간 중 데이터가 없는 월: {months_text}")
        checks.append(
            VerificationCheck(
                check_id="missing_months",
                label="기간 월별 데이터",
                passed=True,
                detail=f"누락 {len(result.missing_months)}개월 ({months_text}) — 참고",
            )
        )
    else:
        checks.append(
            VerificationCheck(
                check_id="missing_months",
                label="기간 월별 데이터",
                passed=True,
                detail=f"{start_month}~{end_month}월 전체 존재",
            )
        )

    manual = _manual_group_counts(period_qs)
    service = aggregate_from_queryset(period_qs)
    if report.is_final:
        manual = _remap_manual_for_final(manual)
        service = remap_bucket_for_final(service)
    elif report.is_simple or report.is_welfare:
        manual = _remap_manual_for_simple(manual)
        service = remap_bucket_for_simple(service)
    if report.is_welfare or report.is_final:
        manual = _remap_manual_for_welfare(manual)
        service = remap_bucket_for_welfare(service)

    # 3) 그룹별 행 수 = 집계 서비스
    service_count_ok = True
    service_amount_ok = True
    service_qty_ok = True
    for key in set(manual) | set(service):
        m = manual.get(key, {"row_count": 0, "amount_won": Decimal(0), "quantity_sum": Decimal(0)})
        s = service.get(key)
        s_count = s.count if s else 0
        s_amount = s.amount_won if s else Decimal(0)
        s_qty = s.quantity if s else Decimal(0)
        if m["row_count"] != s_count:
            service_count_ok = False
            errors.append(f"집계 건수 불일치 {key}: DB={m['row_count']} 집계={s_count}")
        if m["amount_won"] != s_amount:
            service_amount_ok = False
            errors.append(f"집계 금액 불일치 {key}: DB={m['amount_won']} 집계={s_amount}")
        if m["quantity_sum"] != s_qty:
            service_qty_ok = False
            errors.append(f"집계 수량 불일치 {key}: DB={m['quantity_sum']} 집계={s_qty}")

    checks.append(
        VerificationCheck(
            check_id="group_count",
            label="그룹별 행 수 집계",
            passed=service_count_ok,
            detail="거래처×품목×월 행 개수 = 집계 엔진 일치"
            if service_count_ok
            else "그룹별 건수 불일치 발견",
        )
    )
    checks.append(
        VerificationCheck(
            check_id="group_amount",
            label="그룹별 금액 집계",
            passed=service_amount_ok,
            detail="합계 금액 = 집계 엔진 일치"
            if service_amount_ok
            else "그룹별 금액 불일치 발견",
        )
    )
    checks.append(
        VerificationCheck(
            check_id="group_quantity",
            label="그룹별 수량 집계",
            passed=service_qty_ok,
            detail="수량 합 = 집계 엔진 일치"
            if service_qty_ok
            else "그룹별 수량 불일치 발견",
        )
    )

    # 4) 보고서 품목 행 건수 = DB 그룹별 행 수
    report_item_ok = True
    trailing_etc = _report_trailing_etc_key(report)
    customer_codes_scope = _report_customer_codes(report)
    item_categories = get_item_category_map()
    include_unclassified_items = not (report.is_welfare or report.is_final or report.is_simple)
    for row in report.rows:
        if row.row_type != "item":
            continue
        for month in report.months:
            if row.customer_code == SALES_ETC_SUMMARY_CODE:
                expected = _expected_global_etc_for_month(
                    manual,
                    month=month,
                    customer_codes=customer_codes_scope,
                    trailing_etc=trailing_etc,
                    include_unclassified_items=include_unclassified_items,
                    item_categories=item_categories,
                )["row_count"]
            else:
                key = (row.customer_code, row.item_code, month)
                expected = manual.get(key, {"row_count": 0})["row_count"]
            cell = row.months.get(month)
            actual = cell.count if cell else 0
            if expected != actual:
                report_item_ok = False
                errors.append(
                    f"보고서 건수 불일치 {row.customer_label}/{row.item_label} {month}월: "
                    f"DB={expected} 보고서={actual}"
                )

    checks.append(
        VerificationCheck(
            check_id="report_items",
            label="보고서 품목 행 건수",
            passed=report_item_ok,
            detail="모든 품목 행 건수 = DB 행 수"
            if report_item_ok
            else "보고서·DB 건수 불일치",
        )
    )

    # 5) 소계 = 하위 품목 합
    subtotal_ok = True
    rows = report.rows
    i = 0
    while i < len(rows):
        row = rows[i]
        if row.row_type == "subtotal" and row.customer_code:
            item_rows = []
            j = i + 1
            while (
                j < len(rows)
                and rows[j].row_type == "item"
                and rows[j].customer_code == row.customer_code
            ):
                item_rows.append(rows[j])
                j += 1
            for month in report.months:
                sub_sum = sum(r.months.get(month, ReportCell()).count for r in item_rows)
                sub_qty = sum(
                    (r.months.get(month, ReportCell()).quantity for r in item_rows),
                    Decimal(0),
                )
                sub_cell = row.months.get(month)
                sub_count = sub_cell.count if sub_cell else 0
                sub_quantity = sub_cell.quantity if sub_cell else Decimal(0)
                if row.customer_code == SALES_ETC_SUMMARY_CODE:
                    etc_expected = sub_count
                else:
                    etc_bonus = _etc_bucket_slice(
                        manual,
                        cust_code=row.customer_code,
                        month=month,
                        trailing_etc=trailing_etc,
                        include_unclassified_items=include_unclassified_items,
                        item_categories=item_categories,
                    )
                    etc_expected = sub_sum + etc_bonus["row_count"]
                if etc_expected != sub_count:
                    subtotal_ok = False
                    errors.append(
                        f"소계 불일치 {row.customer_label} {month}월: "
                        f"품목합={sub_sum} 소계={sub_count}"
                    )
                if row.customer_code != SALES_ETC_SUMMARY_CODE:
                    etc_qty_bonus = _etc_bucket_slice(
                        manual,
                        cust_code=row.customer_code,
                        month=month,
                        trailing_etc=trailing_etc,
                        include_unclassified_items=include_unclassified_items,
                        item_categories=item_categories,
                    )["quantity_sum"]
                    if sub_qty + etc_qty_bonus != sub_quantity:
                        subtotal_ok = False
                        errors.append(
                            f"소계 수량 불일치 {row.customer_label} {month}월: "
                            f"품목합={sub_qty} 소계={sub_quantity}"
                        )
        i += 1

    checks.append(
        VerificationCheck(
            check_id="subtotals",
            label="소계 행 합산",
            passed=subtotal_ok,
            detail="소계 = 하위 품목 건수·금액 합"
            if subtotal_ok
            else "소계 합산 불일치",
        )
    )

    # 6) 총계 = 거래처 품목 합
    customer_codes = (
        FINAL_CUSTOMER_ORDER
        if report.is_final
        else SIMPLE_CUSTOMER_ORDER
        if (report.is_simple or report.is_welfare)
        else get_customer_category_order()
    )
    item_rows_std = [
        r
        for r in report.rows
        if r.row_type == "item"
        and (r.customer_code in customer_codes or r.customer_code == SALES_ETC_SUMMARY_CODE)
    ]
    grand_from_items = sum(r.total.count for r in item_rows_std)
    grand_count_ok = result.report_grand_count == grand_from_items
    if not grand_count_ok:
        errors.append(
            f"총계 건수 불일치: 품목합={grand_from_items} 총계행={result.report_grand_count}"
        )

    if report.is_welfare:
        count_detail = (
            f"총계 {result.report_grand_count:,}건 "
            f"(복지부 출력항목·간편 거래처 통합)"
        )
    elif report.is_final:
        count_detail = (
            f"총계 {result.report_grand_count:,}건 "
            f"(최종: 복지부 출력항목 / a~d 통합 / 기타·생산시설·미분류)"
        )
    elif report.is_simple:
        count_detail = (
            f"총계 {result.report_grand_count:,}건 "
            f"(간편: 기타·생산시설·미분류 통합 포함)"
        )
    else:
        count_detail = (
            f"총계 {result.report_grand_count:,}건 "
            f"(표준 분류 {grand_from_items:,}건"
            + (
                f", 미분류 {result.unclassified_row_count:,}건 별도"
                if result.unclassified_row_count
                else ""
            )
            + ")"
        )

    checks.append(
        VerificationCheck(
            check_id="grand_count",
            label="총계 행 건수",
            passed=grand_count_ok,
            detail=count_detail,
        )
    )

    grand_from_items_amount = sum(r.total.amount_thousand for r in item_rows_std)
    grand_amount_ok = result.report_grand_amount_thousand == grand_from_items_amount
    if not grand_amount_ok:
        errors.append(
            f"총계 금액 불일치: 품목합={grand_from_items_amount:,}천원 "
            f"총계행={result.report_grand_amount_thousand:,}천원"
        )

    db_total = period_qs.aggregate(s=Sum("total"))["s"] or Decimal(0)
    if report.is_simple or report.is_welfare or report.is_final:
        std_total = db_total
    else:
        std_qs = period_qs.filter(
            customer_category_code__in=get_customer_category_order(),
            item_category_code__in=get_item_category_order(),
        )
        std_total = std_qs.aggregate(s=Sum("total"))["s"] or Decimal(0)
    db_std_thousand = _amount_to_thousand(std_total)
    rounding_drift = abs(result.report_grand_amount_thousand - db_std_thousand)
    amount_detail = (
        f"보고서 총계 {result.report_grand_amount_thousand:,}천원 = 품목행 합계"
        if grand_amount_ok
        else "총계 금액 불일치"
    )
    if grand_amount_ok and rounding_drift > 0:
        warnings.append(
            f"천원 반올림 차이 참고: 셀별 합 {result.report_grand_amount_thousand:,}천원, "
            f"DB 일괄환산 {db_std_thousand:,}천원 (차이 {rounding_drift:,}천원)"
        )
        amount_detail += f" (DB 일괄환산과 {rounding_drift:,}천원 차이)"

    checks.append(
        VerificationCheck(
            check_id="grand_amount",
            label="총계 행 금액(천원)",
            passed=grand_amount_ok,
            detail=amount_detail,
        )
    )

    # 8) 미분류 안내
    if result.unclassified_row_count:
        if report.is_welfare:
            warnings.append(
                f"미분류 원자료 {result.unclassified_row_count:,}건 - "
                "복지부보고서 「기타·생산시설·미분류」 구간 및 기타 출력항목에 포함됩니다."
            )
        elif report.is_final:
            warnings.append(
                f"미분류 원자료 {result.unclassified_row_count:,}건 - "
                "최종보고서 「기타·생산시설·미분류」 구간 및 기타 출력항목에 포함됩니다."
            )
        elif report.is_simple:
            warnings.append(
                f"미분류 원자료 {result.unclassified_row_count:,}건 - "
                "간편보고서 「기타·생산시설·미분류」 구간에 포함되어 있습니다."
            )
        else:
            warnings.append(
                f"미분류 원자료 {result.unclassified_row_count:,}건 - "
                "총계 행에는 포함되지 않으며 보고서 하단·Excel 별도 시트에 표시됩니다."
            )
        checks.append(
            VerificationCheck(
                check_id="unclassified",
                label="미분류 데이터",
                passed=True,
                detail=f"{result.unclassified_row_count:,}건 (별도 구간 표시)",
            )
        )

    # 9) 전체 행 수 대조
    all_item_count = sum(
        r.total.count for r in report.rows if r.row_type == "item"
    )
    rows_reconciled = all_item_count == result.db_row_count
    checks.append(
        VerificationCheck(
            check_id="row_reconcile",
            label="원자료 행 수 대조",
            passed=rows_reconciled,
            detail=(
                f"DB {result.db_row_count:,}행 = 보고서 전 품목행 합 {all_item_count:,}건"
                if rows_reconciled
                else f"DB {result.db_row_count:,}행 ≠ 보고서 품목합 {all_item_count:,}건"
            ),
        )
    )
    if not rows_reconciled:
        errors.append(
            f"원자료 행 수 불일치: DB={result.db_row_count} 보고서품목합={all_item_count}"
        )

    result.checks = checks
    result.errors = errors
    result.warnings = warnings
    result.passed = len(errors) == 0
    return result
