from decimal import Decimal



from django.test import TestCase



from sales_analysis.models import SalesRecord

from sales_analysis.services.aggregation import (

    aggregate_from_queryset,

    build_sales_report,

    get_period_blocks,

)

from sales_analysis.services.master_service import get_item_category_order





class AggregationTest(TestCase):

    def setUp(self):

        rows = [

            ("20250102-1", "b001-1", "b", "e", 10, 100000),

            ("20250102-2", "a001-1", "a", "b", 2, 50000),

            ("20250103-10", "a003-1", "a", "b", 29, 762700),

            ("20250103-10", "a003-2", "a", "b", 1, 54000),

            ("20250103-10", "a003-3", "a", "b", 1, 38000),

        ]

        for voucher, item_code, item_cat_code, cust_cat_code, qty, total in rows:

            SalesRecord.objects.create(

                year=2025,

                month=1,

                voucher_no=voucher,

                item_code=item_code,

                item_category_code=item_cat_code,

                customer_category_code=cust_cat_code,

                quantity=Decimal(qty),

                total=Decimal(total),

            )



    def test_row_count_and_quantity(self):

        bucket = aggregate_from_queryset(SalesRecord.objects.all())

        metrics = bucket.get(("b", "a", 1))

        self.assertIsNotNone(metrics)

        self.assertEqual(metrics.count, 4)

        self.assertEqual(metrics.quantity, Decimal("33"))

        self.assertEqual(metrics.amount_won, Decimal("904700"))



    def test_period_blocks_first_half(self):

        blocks = get_period_blocks(1, 6)

        self.assertEqual(len(blocks), 1)

        self.assertEqual(blocks[0].label, "상반기 소계")



    def test_period_blocks_full_year(self):

        blocks = get_period_blocks(1, 12)

        self.assertEqual(len(blocks), 2)

        self.assertEqual(blocks[0].label, "상반기 소계")

        self.assertEqual(blocks[1].label, "하반기 소계")



    def test_report_block_equals_total_for_half_year(self):

        qs = SalesRecord.objects.filter(year=2025, month=1)

        report = build_sales_report(qs, 2025, 1, 1)

        total_row = report.rows[0]

        block = total_row.blocks.get("h1")

        self.assertIsNotNone(block)

        self.assertEqual(block.count, total_row.total.count)

        self.assertEqual(block.quantity, total_row.total.quantity)



    def test_report_has_all_item_rows(self):

        qs = SalesRecord.objects.filter(year=2025, month=1)

        report = build_sales_report(qs, 2025, 1, 1)

        item_rows = [r for r in report.rows if r.row_type == "item" and r.customer_code == "b"]

        self.assertEqual(len(item_rows), len(get_item_category_order()))



    def test_report_total_row_first(self):

        qs = SalesRecord.objects.filter(year=2025, month=1)

        report = build_sales_report(qs, 2025, 1, 1)

        self.assertEqual(report.rows[0].row_type, "total")



    def test_report_uses_updated_master_name(self):

        from sales_analysis.models import ItemCategoryMaster



        ItemCategoryMaster.objects.filter(code="b").update(name="위생용품")

        qs = SalesRecord.objects.filter(year=2025, month=1)

        report = build_sales_report(qs, 2025, 1, 1)

        item_rows = [r for r in report.rows if r.row_type == "item" and r.item_code == "b"]

        self.assertTrue(item_rows)

        self.assertEqual(item_rows[0].item_label, "위생용품")


