from django.test import TestCase

from sales_analysis.constants import MASTER_UPLOAD_MODE_MERGE, MASTER_UPLOAD_MODE_REPLACE
from sales_analysis.models import ItemCategoryMaster, SalesRecord
from sales_analysis.services.master_service import (
    create_item_category,
    delete_item_category,
    get_item_usage,
    preview_master_upload,
    update_item_category,
    validate_category_code,
)


class MasterServiceTest(TestCase):
    def test_validate_category_code(self):
        self.assertEqual(validate_category_code("A"), "a")
        with self.assertRaises(ValueError):
            validate_category_code("ab")
        with self.assertRaises(ValueError):
            validate_category_code("1")

    def test_create_duplicate_code_rejected(self):
        create_item_category("y", "테스트품목")
        with self.assertRaises(ValueError):
            create_item_category("y", "중복")

    def test_update_master_name(self):
        update_item_category("b", "위생용품", True)
        obj = ItemCategoryMaster.objects.get(code="b")
        self.assertEqual(obj.name, "위생용품")

    def test_delete_in_use_blocked(self):
        SalesRecord.objects.create(
            year=2025,
            month=1,
            voucher_no="v1",
            item_code="b001",
            item_category_code="b",
            customer_category_code="a",
            total=1000,
        )
        self.assertGreater(get_item_usage("b"), 0)
        with self.assertRaises(ValueError):
            delete_item_category("b", force=False)

    def test_force_delete_marks_records_unclassified(self):
        SalesRecord.objects.create(
            year=2025,
            month=1,
            voucher_no="v1",
            item_code="y001",
            item_category_code="y",
            customer_category_code="a",
            total=1000,
        )
        create_item_category("y", "임시품목")
        delete_item_category("y", force=True)
        record = SalesRecord.objects.get(voucher_no="v1")
        self.assertTrue(record.is_unclassified_item)

    def test_preview_replace_lists_removed_codes(self):
        preview = preview_master_upload(
            "item",
            [("a", "복사용지"), ("b", "위생용품")],
            MASTER_UPLOAD_MODE_REPLACE,
        )
        self.assertIn("c", preview.removed_codes)

    def test_merge_keeps_existing_codes(self):
        preview = preview_master_upload(
            "item",
            [("a", "복사용지"), ("y", "신규품목")],
            MASTER_UPLOAD_MODE_MERGE,
        )
        self.assertEqual(preview.new_codes, ["y"])
        self.assertEqual(preview.removed_codes, [])

