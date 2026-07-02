from decimal import Decimal

from django.test import TestCase

from sales_analysis.models import SalesRecord
from sales_analysis.services.aggregation import build_sales_report
from sales_analysis.services.report_verification import verify_report


class ReportVerificationTest(TestCase):
    def setUp(self):
        for voucher, item_code, item_cat, cust_cat, total in [
            ("20250102-1", "a001-1", "a", "a", 10000),
            ("20250103-10", "a003-1", "a", "b", 5000),
            ("20250103-10", "a003-2", "a", "b", 3000),
        ]:
            SalesRecord.objects.create(
                year=2025,
                month=1,
                voucher_no=voucher,
                item_code=item_code,
                item_category_code=item_cat,
                customer_category_code=cust_cat,
                quantity=Decimal("1"),
                total=Decimal(total),
            )

    def test_verification_passes(self):
        qs = SalesRecord.objects.filter(year=2025, month=1)
        report = build_sales_report(qs, 2025, 1, 1)
        result = verify_report(qs, report, 2025, 1, 1)
        self.assertTrue(result.passed)
        self.assertEqual(result.db_row_count, 3)
        self.assertTrue(any(c.check_id == "group_count" and c.passed for c in result.checks))

    def test_verification_fails_on_empty_period(self):
        qs = SalesRecord.objects.filter(year=2025, month=2)
        report = build_sales_report(qs, 2025, 2, 2)
        result = verify_report(qs, report, 2025, 2, 2)
        self.assertFalse(result.passed)
