from decimal import Decimal



from django.test import TestCase



from sales_analysis.constants import (
    FINAL_MAIN_MERGED_CODE,
    FINAL_MAIN_MERGED_LABEL,
    SIMPLE_MERGED_CODE,
    SIMPLE_MERGED_LABEL,
)

from sales_analysis.models import SalesRecord

from sales_analysis.services.aggregation import (
    SALES_ETC_SUMMARY_CODE,
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

                customer_category_code=cust,

                quantity=Decimal(qty),

                total=Decimal(total),

                is_unclassified_customer=cust not in ("a", "b", "c", "d", "e", "z"),

                is_unclassified_item=item_cat not in get_seed_item_codes(),

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

    def test_final_report_merges_customer_groups(self):
        rows = [
            ("a", "a", "a", 1, 1000),
            ("b", "a", "a", 2, 2000),
            ("e", "b", "b", 3, 3000),
            ("z", "c", "c", 4, 4000),
        ]
        for cust, item, item_cat, qty, total in rows:
            SalesRecord.objects.create(
                year=2025,
                month=1,
                voucher_no=f"v-{cust}-{item}",
                item_code=f"{item}001",
                item_category_code=item_cat,
                customer_category_code=cust,
                quantity=Decimal(qty),
                total=Decimal(total),
                is_unclassified_customer=cust not in ("a", "b", "c", "d", "e", "z"),
                is_unclassified_item=item_cat not in get_seed_item_codes(),
            )

        qs = SalesRecord.objects.filter(year=2025, month=1)
        report = build_sales_report(qs, 2025, 1, 1, final=True)

        self.assertTrue(report.is_final)
        self.assertFalse(report.is_simple)
        self.assertFalse(report.is_welfare)

        customer_sections = [r for r in report.rows if r.row_type == "subtotal"]
        self.assertEqual(len(customer_sections), 2)

        main_sub = next(
            r for r in customer_sections if r.customer_code == FINAL_MAIN_MERGED_CODE
        )
        self.assertEqual(main_sub.customer_label, FINAL_MAIN_MERGED_LABEL)
        self.assertEqual(main_sub.total.count, 2)

        merged_sub = next(
            r for r in customer_sections if r.customer_code == SIMPLE_MERGED_CODE
        )
        self.assertEqual(merged_sub.customer_label, SIMPLE_MERGED_LABEL)
        self.assertEqual(merged_sub.total.count, 2)
        self.assertEqual(report.rows[0].total.count, 4)
        final_item_rows = [r for r in report.rows if r.row_type == "item"]
        self.assertTrue(final_item_rows)
        self.assertNotIn("a", {r.item_code for r in final_item_rows})
        self.assertIn("office", {r.item_code for r in final_item_rows})
        self.assertIn("사무문구", {r.item_label for r in final_item_rows})

    def test_sales_etc_aggregated_at_bottom(self):
        rows = [
            ("a", "a", "a", 1, 1000),
            ("b", "z", "z", 2, 2000),
            ("e", "z", "z", 3, 3000),
        ]
        for cust, item, item_cat, qty, total in rows:
            SalesRecord.objects.create(
                year=2025,
                month=1,
                voucher_no=f"v-{cust}-{item}",
                item_code=f"{item}001",
                item_category_code=item_cat,
                customer_category_code=cust,
                quantity=Decimal(qty),
                total=Decimal(total),
                is_unclassified_customer=cust not in ("a", "b", "c", "d", "e", "z"),
                is_unclassified_item=item_cat not in get_seed_item_codes(),
            )

        qs = SalesRecord.objects.filter(year=2025, month=1)
        for report in (
            build_sales_report(qs, 2025, 1, 1),
            build_sales_report(qs, 2025, 1, 1, simple=True),
            build_sales_report(qs, 2025, 1, 1, welfare=True),
            build_sales_report(qs, 2025, 1, 1, final=True),
        ):
            etc_rows = [r for r in report.rows if r.customer_code == SALES_ETC_SUMMARY_CODE]
            self.assertEqual(len(etc_rows), 2, report.period_label)
            self.assertEqual(etc_rows[1].total.count, 2)
            self.assertEqual(etc_rows[1].total.amount_thousand, 5)
            self.assertEqual(report.rows[-1].customer_code, SALES_ETC_SUMMARY_CODE)
            self.assertFalse(
                any(
                    r.row_type == "item"
                    and r.item_code in ("z", "etc")
                    and r.customer_code != SALES_ETC_SUMMARY_CODE
                    for r in report.rows
                )
            )


def get_seed_item_codes():

    from sales_analysis.constants import SEED_ITEM_CATEGORIES



    return set(SEED_ITEM_CATEGORIES.keys())


