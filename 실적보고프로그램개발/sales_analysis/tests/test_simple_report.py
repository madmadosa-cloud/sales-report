from decimal import Decimal

from django.test import TestCase

from sales_analysis.constants import SIMPLE_MERGED_CODE, SIMPLE_MERGED_LABEL
from sales_analysis.models import SalesRecord
from sales_analysis.services.aggregation import (
    belongs_in_merged_group,
    build_sales_report,
    effective_customer_code,
)


class SimpleReportTest(TestCase):
    def test_belongs_in_merged_group(self):
        self.assertTrue(belongs_in_merged_group("e", "a"))
        self.assertTrue(belongs_in_merged_group("z", "b"))
        self.assertTrue(belongs_in_merged_group("", "a"))
        self.assertTrue(belongs_in_merged_group("b", "xx"))
        self.assertFalse(belongs_in_merged_group("b", "a"))

    def test_effective_customer_code(self):
        self.assertEqual(effective_customer_code("e", "a", True), SIMPLE_MERGED_CODE)
        self.assertEqual(effective_customer_code("a", "a", True), "a")

    def test_simple_report_merges_sections(self):
        rows = [
            ("a", "a", "a", 1, 1000),
            ("e", "b", "b", 2, 2000),
            ("z", "c", "c", 3, 3000),
            ("q", "m", "m", 4, 4000),
        ]
        for cust, item, item_cat, qty, total in rows:
            SalesRecord.objects.create(
                year=2025,
                month=1,
                voucher_no=f"v-{cust}-{item}",
                item_code=f"{item}001",
                item_category_code=item_cat,
                item_category_name="t",
                customer_category_code=cust,
                customer_category_name="t",
                quantity=Decimal(qty),
                total=Decimal(total),
                is_unclassified_customer=cust not in ("a", "b", "c", "d", "e", "z"),
                is_unclassified_item=item_cat not in ("a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "z"),
            )

        qs = SalesRecord.objects.filter(year=2025, month=1)
        report = build_sales_report(qs, 2025, 1, 1, simple=True)
        self.assertTrue(report.is_simple)
        customer_sections = [r for r in report.rows if r.row_type == "subtotal"]
        self.assertEqual(len(customer_sections), 5)
        merged_sub = next(
            r for r in customer_sections if r.customer_label == SIMPLE_MERGED_LABEL
        )
        self.assertEqual(merged_sub.total.count, 3)
        self.assertEqual(customer_sections[0].total.count, 1)
        self.assertEqual(report.rows[0].total.count, 4)
