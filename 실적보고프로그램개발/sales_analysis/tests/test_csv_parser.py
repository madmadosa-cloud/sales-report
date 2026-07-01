from django.test import TestCase

from sales_analysis.constants import CUSTOMER_CATEGORIES, ITEM_CATEGORIES
from sales_analysis.services.classification import (
    extract_customer_category_code,
    extract_item_category_code,
    parse_classification_csv,
    parse_sales_csv,
    parse_voucher_year_month,
    resolve_customer_category_name,
    resolve_item_category_name,
)


class ClassificationTest(TestCase):
    def test_item_category_extraction(self):
        self.assertEqual(extract_item_category_code("b001-2024-3"), "b")
        self.assertEqual(extract_item_category_code("z001-1"), "z")

    def test_customer_category_extraction(self):
        self.assertEqual(extract_customer_category_code("E1-00145"), "e")
        self.assertEqual(extract_customer_category_code("B15-00006"), "b")

    def test_voucher_year_month(self):
        self.assertEqual(parse_voucher_year_month("20250102-1"), (2025, 1))
        self.assertEqual(parse_voucher_year_month("20251231-99"), (2025, 12))

    def test_resolve_names(self):
        self.assertEqual(resolve_item_category_name("b"), ITEM_CATEGORIES["b"])
        self.assertEqual(resolve_customer_category_name("e"), CUSTOMER_CATEGORIES["e"])
        self.assertEqual(resolve_item_category_name("xx"), "미분류")


class CsvParserTest(TestCase):
    def test_parse_sample_header(self):
        sample = (
            "품목코드,품목명(규격),전표별,품목별,거래처별,수량,거래처코드,공급가액,부가세,합계,적요\n"
            "b001-2024-3,핸드타올,20250102-1,핸드타올,테스트,15,E1-00145,495000,0,495000,\n"
            "총합계,,,,,15,,495000,0,495000,\n"
            "2026/07/01 (수)오후 7:18:40,,,,,,,,,,\n"
        ).encode("utf-8-sig")
        records, _ = parse_sales_csv(sample, "test.csv")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["year"], 2025)
        self.assertEqual(records[0]["month"], 1)
        self.assertEqual(records[0]["customer_category_code"], "e")

    def test_parse_classification_csv(self):
        text = (
            "품목코드,\n"
            "a,복사용지\n"
            "b,화장지물티슈\n"
            "\n"
            "\n"
            "거래처코드,\n"
            "a,지방자치단체\n"
            "e,기타\n"
        ).encode("utf-8-sig")
        items, customers = parse_classification_csv(text)
        self.assertEqual(items["a"], "복사용지")
        self.assertEqual(customers["e"], "기타")
