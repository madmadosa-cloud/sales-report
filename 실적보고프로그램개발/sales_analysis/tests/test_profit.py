from decimal import Decimal



from django.test import TestCase

from django.urls import reverse



from sales_analysis.constants import (
    FINAL_MAIN_MERGED_CODE,
    FINAL_MAIN_MERGED_LABEL,
    SEED_CUSTOMER_CATEGORIES,
    SEED_ITEM_CATEGORIES,
    SIMPLE_MERGED_CODE,
    SIMPLE_MERGED_LABEL,
)

from sales_analysis.models import ProfitRecord

from sales_analysis.services.classification import parse_profit_csv

from sales_analysis.services.profit_aggregation import build_profit_report

from sales_analysis.services.profit_import_service import process_profit_upload

from sales_analysis.services.welfare_service import get_welfare_group_order





ERP_CSV_HEADER = (

    "품목코드,품목명(규격),거래처코드,거래처명,수량,단가,금액,단가,금액,단가,금액,이익율\n"

)





class ProfitCsvParserTest(TestCase):

    def test_parse_erp_profit_csv(self):

        sample = (

            ERP_CSV_HEADER

            + "a001-2024-1,복사용지,A10-00036,거창군청,1,27000,27000,24300,24300,2700,2700,10%\n"

            + "b001-2024-3,화장지,B15-00006,교육기관,5,10000,50000,9000,45000,1000,5000,10%\n"

        ).encode("utf-8-sig")

        records, _ = parse_profit_csv(sample, "profit.csv")

        self.assertEqual(len(records), 2)

        self.assertEqual(records[0]["item_category_code"], "a")

        self.assertEqual(records[0]["customer_category_code"], "a")

        self.assertEqual(records[0]["quantity"], "1")

        self.assertEqual(records[0]["cost"], "24300")

        self.assertEqual(records[0]["amount"], "2700")

        self.assertEqual(records[1]["item_category_code"], "b")

        self.assertEqual(records[1]["customer_category_code"], "b")

        self.assertEqual(records[1]["amount"], "5000")



    def test_parse_merged_header_uses_cost_amount_not_unit_price(self):
        sample = (
            "품목코드,품목명(규격),거래처코드,거래처명,판매,판매,판매,원가,원가,이익,이익,이익율\n"
            ",,,,수량,단가,금액,단가,금액,단가,금액,\n"
            "a001-2024-1,품목,A1,거래처,1,100,1000,99,888888,9,77,10%\n"
        ).encode("utf-8-sig")
        records, _ = parse_profit_csv(sample, "profit.csv")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["cost"], "888888")
        self.assertEqual(records[0]["amount"], "77")
        self.assertEqual(records[0]["quantity"], "1")



    def test_parse_includes_row_when_profit_empty_but_cost_exists(self):
        sample = (
            ERP_CSV_HEADER
            + "a001-2024-1,품목,A1,거래처,1,100,1000,99,5000,,10%\n"
        ).encode("utf-8-sig")
        records, _ = parse_profit_csv(sample, "profit.csv")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["cost"], "5000")
        self.assertEqual(records[0]["amount"], "0")



    def test_parse_rejects_file_without_valid_rows(self):

        sample = (

            ERP_CSV_HEADER + "9999,잘못된코드,A1,거래처,1,1,1,1,1,1,100,10%\n"

        ).encode("utf-8-sig")

        with self.assertRaises(ValueError):

            parse_profit_csv(sample, "profit.csv")





class ProfitReportTest(TestCase):

    def _seed_records(self):

        ProfitRecord.objects.create(

            item_code="a001-2024-1",

            item_name=SEED_ITEM_CATEGORIES["a"],

            customer_code="A10-00036",

            customer_category_code="a",

            item_category_code="a",

            quantity=Decimal("10"),

            cost=Decimal("90000"),

            amount=Decimal("10000"),

            period_label="2026/01/01~06/30",

        )

        ProfitRecord.objects.create(

            item_code="o001-2024-1",

            item_name="충전기",

            customer_code="B15-00006",

            customer_category_code="b",

            item_category_code="o",

            quantity=Decimal("3"),

            cost=Decimal("54000"),

            amount=Decimal("6000"),

            period_label="2026/01/01~06/30",

        )

        ProfitRecord.objects.create(

            item_code="q001-2024-1",

            item_name="LED",

            customer_code="B15-00006",

            customer_category_code="b",

            item_category_code="q",

            quantity=Decimal("2"),

            cost=Decimal("36000"),

            amount=Decimal("4000"),

            period_label="2026/01/01~06/30",

        )



    def test_report_grand_total_matches_db_sum(self):
        self._seed_records()
        from django.db.models import Sum

        db = ProfitRecord.objects.aggregate(
            quantity=Sum("quantity"),
            cost=Sum("cost"),
            amount=Sum("amount"),
        )
        report = build_profit_report(welfare=False)
        total = report.rows[0]
        self.assertEqual(total.quantity, db["quantity"])
        self.assertEqual(total.cost, db["cost"])
        self.assertEqual(total.amount, db["amount"])



    def test_build_profit_report_by_customer_and_item(self):

        self._seed_records()

        report = build_profit_report(welfare=False)

        total = report.rows[0]

        self.assertEqual(total.customer_label, "총계")

        self.assertEqual(total.amount, Decimal("20000"))

        self.assertEqual(total.cost, Decimal("180000"))

        self.assertEqual(total.amount_thousand, 20)

        self.assertEqual(total.cost_thousand, 180)



        a_item = next(

            r

            for r in report.rows

            if r.row_type == "item" and r.customer_code == "a" and r.item_code == "a"

        )

        self.assertEqual(a_item.customer_label, SEED_CUSTOMER_CATEGORIES["a"])

        self.assertEqual(a_item.item_label, SEED_ITEM_CATEGORIES["a"])

        self.assertEqual(a_item.quantity, Decimal("10"))
        self.assertEqual(a_item.cost_thousand, 90)



        b_subtotal = next(

            r for r in report.rows if r.row_type == "subtotal" and r.customer_code == "b"

        )

        self.assertEqual(b_subtotal.quantity, Decimal("5"))

        self.assertEqual(b_subtotal.amount, Decimal("10000"))



    def test_build_profit_welfare_report_merges_etc_and_facility_customers(self):
        ProfitRecord.objects.create(
            item_code="a001-2024-1",
            item_name=SEED_ITEM_CATEGORIES["a"],
            customer_code="E10-00001",
            customer_category_code="e",
            item_category_code="a",
            quantity=Decimal("1"),
            cost=Decimal("9000"),
            amount=Decimal("1000"),
            period_label="2026/01/01~06/30",
        )
        ProfitRecord.objects.create(
            item_code="b001-2024-1",
            item_name=SEED_ITEM_CATEGORIES["b"],
            customer_code="Z10-00001",
            customer_category_code="z",
            item_category_code="b",
            quantity=Decimal("2"),
            cost=Decimal("18000"),
            amount=Decimal("2000"),
            period_label="2026/01/01~06/30",
        )

        report = build_profit_report(welfare=True)
        merged_subtotal = next(
            r
            for r in report.rows
            if r.row_type == "subtotal" and r.customer_code == SIMPLE_MERGED_CODE
        )
        self.assertEqual(merged_subtotal.customer_label, SIMPLE_MERGED_LABEL)
        self.assertEqual(merged_subtotal.quantity, Decimal("3"))
        self.assertEqual(merged_subtotal.cost, Decimal("27000"))
        self.assertEqual(merged_subtotal.amount, Decimal("3000"))
        self.assertFalse(any(r.customer_code == "e" for r in report.rows))
        self.assertFalse(any(r.customer_code == "z" for r in report.rows))

    def test_build_profit_final_report_merges_customer_groups(self):
        ProfitRecord.objects.create(
            item_code="a001-2024-1",
            item_name=SEED_ITEM_CATEGORIES["a"],
            customer_code="A10-00036",
            customer_category_code="a",
            item_category_code="a",
            quantity=Decimal("10"),
            cost=Decimal("90000"),
            amount=Decimal("10000"),
            period_label="2026/01/01~06/30",
        )
        ProfitRecord.objects.create(
            item_code="a001-2024-1",
            item_name=SEED_ITEM_CATEGORIES["a"],
            customer_code="B15-00006",
            customer_category_code="b",
            item_category_code="a",
            quantity=Decimal("5"),
            cost=Decimal("45000"),
            amount=Decimal("5000"),
            period_label="2026/01/01~06/30",
        )
        ProfitRecord.objects.create(
            item_code="b001-2024-1",
            item_name=SEED_ITEM_CATEGORIES["b"],
            customer_code="E10-00001",
            customer_category_code="e",
            item_category_code="b",
            quantity=Decimal("2"),
            cost=Decimal("18000"),
            amount=Decimal("2000"),
            period_label="2026/01/01~06/30",
        )

        report = build_profit_report(final=True)
        self.assertTrue(report.is_final)
        self.assertFalse(report.is_welfare)

        main_sub = next(
            r
            for r in report.rows
            if r.row_type == "subtotal" and r.customer_code == FINAL_MAIN_MERGED_CODE
        )
        self.assertEqual(main_sub.customer_label, FINAL_MAIN_MERGED_LABEL)
        self.assertEqual(main_sub.quantity, Decimal("15"))
        self.assertEqual(main_sub.amount, Decimal("15000"))

        other_sub = next(
            r
            for r in report.rows
            if r.row_type == "subtotal" and r.customer_code == SIMPLE_MERGED_CODE
        )
        self.assertEqual(other_sub.customer_label, SIMPLE_MERGED_LABEL)
        self.assertEqual(other_sub.quantity, Decimal("2"))
        self.assertEqual(other_sub.amount, Decimal("2000"))

        subtotals = [r for r in report.rows if r.row_type == "subtotal"]
        self.assertEqual(len(subtotals), 2)
        self.assertFalse(any(r.customer_code == "a" for r in report.rows))
        self.assertFalse(any(r.customer_code == "b" for r in report.rows))
        self.assertFalse(any(r.customer_code == "e" for r in report.rows))

    def test_build_profit_welfare_report(self):

        self._seed_records()

        report = build_profit_report(welfare=True)

        self.assertTrue(report.is_welfare)

        facility = next(

            r

            for r in report.rows

            if r.row_type == "item"

            and r.customer_code == "b"

            and r.item_label == "시설설비"

        )

        self.assertEqual(facility.quantity, Decimal("5"))

        self.assertEqual(facility.amount, Decimal("10000"))

        welfare_items_per_customer = len(get_welfare_group_order())

        b_items = [

            r

            for r in report.rows

            if r.row_type == "item" and r.customer_code == "b"

        ]

        self.assertEqual(len(b_items), welfare_items_per_customer)



    def test_profit_upload_replace_flow(self):

        ProfitRecord.objects.all().delete()

        session = "test-session"

        csv1 = (

            ERP_CSV_HEADER + "a001-2024-1,복사용지,A1,거래처,1,1,1,1,1,1,1000,10%\n"

        ).encode("utf-8-sig")



        class FakeFile:

            name = "p1.csv"



            def read(self):

                return csv1



        result = process_profit_upload(session, [FakeFile()], "1분기", confirmed=False)

        self.assertEqual(result["status"], "ok")

        self.assertEqual(ProfitRecord.objects.count(), 1)

        saved = ProfitRecord.objects.first()

        self.assertEqual(saved.customer_category_code, "a")

        self.assertEqual(saved.cost, Decimal("1"))



        csv2 = (

            ERP_CSV_HEADER + "d001-2024-1,가구,A1,거래처,2,1,2,1,2,1,2000,10%\n"

        ).encode("utf-8-sig")



        class FakeFile2:

            name = "p2.csv"



            def read(self):

                return csv2



        result2 = process_profit_upload(session, [FakeFile2()], "2분기", confirmed=False)

        self.assertEqual(result2["status"], "confirm_needed")



        result3 = process_profit_upload(session, [], "", confirmed=True)

        self.assertEqual(result3["status"], "ok")

        self.assertEqual(ProfitRecord.objects.count(), 1)

        self.assertEqual(ProfitRecord.objects.first().item_category_code, "d")



    def test_profit_page_loads(self):

        response = self.client.get(reverse("sales_analysis:profit_index"))

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "이익분석")
        self.assertContains(response, "최종보고서")

