from decimal import Decimal

from django.test import TestCase

from sales_analysis.services.welfare_service import get_welfare_group_labels, welfare_group_for_item
from sales_analysis.models import SalesRecord
from sales_analysis.services.aggregation import build_sales_report, remap_bucket_for_welfare


class WelfareReportTest(TestCase):
    def test_welfare_group_mapping(self):
        self.assertEqual(welfare_group_for_item("o"), "facility")
        self.assertEqual(welfare_group_for_item("a"), "office")
        self.assertEqual(welfare_group_for_item("c"), "clothing")
        self.assertEqual(welfare_group_for_item("b"), "living")
        self.assertEqual(welfare_group_for_item("g"), "living")
        self.assertEqual(welfare_group_for_item("z"), "etc")

    def test_welfare_report_groups_items(self):
        SalesRecord.objects.create(
            year=2025,
            month=1,
            voucher_no="v1",
            item_code="o001",
            item_category_code="o",
            customer_category_code="a",
            quantity=Decimal("2"),
            total=Decimal("10000"),
        )
        SalesRecord.objects.create(
            year=2025,
            month=1,
            voucher_no="v2",
            item_code="q001",
            item_category_code="q",
            customer_category_code="a",
            quantity=Decimal("3"),
            total=Decimal("20000"),
        )

        qs = SalesRecord.objects.filter(year=2025, month=1)
        report = build_sales_report(qs, 2025, 1, 1, welfare=True)
        self.assertTrue(report.is_welfare)
        facility_rows = [
            r
            for r in report.rows
            if r.row_type == "item"
            and r.customer_code == "a"
            and r.item_code == "facility"
        ]
        self.assertEqual(len(facility_rows), 1)
        self.assertEqual(facility_rows[0].item_label, get_welfare_group_labels()["facility"])
        self.assertEqual(facility_rows[0].total.count, 2)
        self.assertEqual(facility_rows[0].total.quantity, Decimal("5"))

    def test_welfare_report_has_output_rows(self):
        qs = SalesRecord.objects.filter(year=2025, month=1)
        report = build_sales_report(qs, 2025, 1, 1, welfare=True)
        item_rows = [r for r in report.rows if r.row_type == "item" and r.customer_code == "a"]
        self.assertEqual(len(item_rows), 12)

    def test_remap_bucket_for_welfare(self):
        from sales_analysis.services.aggregation import MonthMetrics, aggregate_from_queryset

        SalesRecord.objects.create(
            year=2025,
            month=1,
            voucher_no="v1",
            item_code="f001",
            item_category_code="f",
            customer_category_code="b",
            quantity=Decimal("1"),
            total=Decimal("5000"),
        )
        SalesRecord.objects.create(
            year=2025,
            month=1,
            voucher_no="v2",
            item_code="n001",
            item_category_code="n",
            customer_category_code="b",
            quantity=Decimal("2"),
            total=Decimal("7000"),
        )
        bucket = aggregate_from_queryset(SalesRecord.objects.all())
        welfare_bucket = remap_bucket_for_welfare(bucket)
        metrics = welfare_bucket.get(("b", "print_ad", 1))
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.count, 2)
        self.assertEqual(metrics.amount_won, Decimal("12000"))
