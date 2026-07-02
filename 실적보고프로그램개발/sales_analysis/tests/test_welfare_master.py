from django.test import TestCase
from django.urls import reverse

from sales_analysis.services.welfare_service import (
    create_welfare_output_item,
    list_welfare_items_with_mappings,
    update_welfare_output_item,
    welfare_group_for_item,
)


class WelfareMasterTest(TestCase):
    def test_seed_data_matches_image_mapping(self):
        rows = {row["name"]: row["item_codes"] for row in list_welfare_items_with_mappings()}
        self.assertEqual(rows["시설설비"], "o, q, t, u")
        self.assertEqual(rows["인쇄광고"], "f, n, p")
        self.assertEqual(rows["사무문구"], "a, e")
        self.assertEqual(rows["의류침구"], "c")
        self.assertEqual(rows["디지털가전"], "r")
        self.assertEqual(rows["생활용품"], "b, g")
        self.assertEqual(rows["서비스"], "k")
        self.assertEqual(rows["일회용품"], "i, j, l")
        self.assertEqual(rows["가구"], "d, m, s")
        self.assertEqual(rows["식품"], "h")
        self.assertEqual(rows["화훼"], "")
        self.assertEqual(rows["공예"], "")
        self.assertEqual(rows["기타"], "z")

    def test_create_and_update_output_item(self):
        create_welfare_output_item("test_group", "테스트항목", "x")
        self.assertEqual(welfare_group_for_item("x"), "test_group")

        update_welfare_output_item("test_group", "테스트항목수정", "y")
        self.assertEqual(welfare_group_for_item("y"), "test_group")
        self.assertEqual(welfare_group_for_item("x"), "etc")

    def test_welfare_master_page_loads(self):
        response = self.client.get(reverse("sales_analysis:welfare_category_master"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "복지부 분류코드 관리")
        self.assertContains(response, "시설설비")
