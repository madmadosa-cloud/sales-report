"""
업로드된 DB 데이터 기준 행 개수 집계 검증 (CLI).

보고서 생성 시 웹 UI에서 동일한 verify_report()가 실행됩니다.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import django

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sales_report.settings")
django.setup()

from django.db.models import Count  # noqa: E402

from sales_analysis.models import SalesRecord  # noqa: E402
from sales_analysis.services.aggregation import build_sales_report  # noqa: E402
from sales_analysis.services.report_verification import verify_report  # noqa: E402


def main() -> int:
    total = SalesRecord.objects.count()
    print("=" * 60)
    print("매출 행 개수 집계 검증")
    print("=" * 60)
    print(f"\nDB 총 저장 행: {total:,}")

    if total == 0:
        print("\nDB가 비어 있습니다. CSV 업로드 후 다시 실행하세요.")
        return 1

    periods = list(
        SalesRecord.objects.values("year", "month")
        .annotate(n=Count("id"))
        .order_by("year", "month")
    )
    print("\n=== 연월별 저장 행 ===")
    for p in periods:
        print(f"  {p['year']}년 {p['month']}월: {p['n']:,}행")

    year = periods[0]["year"]
    months_in_db = [p["month"] for p in periods if p["year"] == year]
    start_month, end_month = min(months_in_db), max(months_in_db)

    qs = SalesRecord.objects.filter(year=year, month__gte=start_month, month__lte=end_month)
    period_label = f"{year}년 {start_month}~{end_month}월"
    report = build_sales_report(qs, year, start_month, end_month, period_label)
    result = verify_report(qs, report, year, start_month, end_month)

    print(f"\n검증 대상: {period_label}")
    print("\n=== 검증 항목 ===")
    for check in result.checks:
        mark = "OK" if check.passed else "NG"
        print(f"  [{mark}] {check.label}: {check.detail}")

    if result.warnings:
        print("\n=== 참고 ===")
        for w in result.warnings:
            print(f"  ! {w}")

    print("\n" + "=" * 60)
    if result.passed:
        print("검증 통과")
        print(f"  총계 건수: {result.report_grand_count:,}")
        print(f"  총계 금액(천원): {result.report_grand_amount_thousand:,}")
        return 0

    print("검증 실패")
    for e in result.errors:
        print(f"  x {e}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
