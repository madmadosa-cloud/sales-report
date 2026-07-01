"""특정 그룹(예: 지방자치단체×복사용지) 행 수 수동 대조"""
import os, sys
from pathlib import Path
import django
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sales_report.settings")
django.setup()

from django.db.models import Count, Sum
from sales_analysis.models import SalesRecord
from sales_analysis.services.classification import parse_sales_csv
from sales_analysis.services.aggregation import build_sales_report

YEAR, MONTH = 2025, 1
CUST, ITEM = "a", "a"  # 지방자치단체 × 복사용지

qs = SalesRecord.objects.filter(
    year=YEAR, month=MONTH,
    customer_category_code=CUST,
    item_category_code=ITEM,
)
db_count = qs.count()
db_amount = qs.aggregate(s=Sum("total"))["s"]

# CSV 직접 카운트
csv_path = Path(r"c:\Users\user\Desktop\2026-07-01_2025년1월전표별품목별매출자료.csv")
records, _ = parse_sales_csv(csv_path.read_bytes(), csv_path.name)
csv_rows = [
    r for r in records
    if r["year"] == YEAR and r["month"] == MONTH
    and r["customer_category_code"] == CUST
    and r["item_category_code"] == ITEM
]

report = build_sales_report(
    SalesRecord.objects.filter(year=YEAR, month=MONTH),
    YEAR, MONTH, MONTH,
)
report_row = next(
    (r for r in report.rows
     if r.row_type == "item" and r.customer_code == CUST and r.item_code == ITEM),
    None,
)
report_count = report_row.months[MONTH].count if report_row else None
report_amount_k = report_row.months[MONTH].amount_thousand if report_row else None

print(f"=== {YEAR}년 {MONTH}월 지방자치단체(a) × 복사용지(a) ===")
print(f"원본 CSV 해당 행:     {len(csv_rows):,}")
print(f"DB 저장 행:           {db_count:,}")
print(f"보고서 표시 건수:     {report_count:,}")
print(f"DB 합계(원):          {int(db_amount):,}")
print(f"보고서 금액(천원):    {report_amount_k:,}")
print()
print("일치 여부:")
print(f"  CSV == DB:      {len(csv_rows) == db_count}")
print(f"  DB == 보고서:   {db_count == report_count}")

# 월별 전체 대조
print(f"\n=== {YEAR}년 월별 CSV(1월파일) vs DB ===")
from collections import defaultdict
csv_by_month = defaultdict(int)
for r in records:
    if r["year"] == YEAR:
        csv_by_month[r["month"]] += 1
for m in range(1, 13):
    if m in csv_by_month or SalesRecord.objects.filter(year=YEAR, month=m).exists():
        db_n = SalesRecord.objects.filter(year=YEAR, month=m).count()
        csv_n = csv_by_month.get(m, 0)
        mark = "OK" if csv_n == db_n or csv_n == 0 else "DIFF"
        if db_n or csv_n:
            print(f"  {m:2}월  CSV={csv_n:4}  DB={db_n:4}  [{mark}]")
