from django.db import models


class SalesRecord(models.Model):
    """매출 원자료 (전표별 품목 행 단위)"""

    year = models.PositiveSmallIntegerField("연도", db_index=True)
    month = models.PositiveSmallIntegerField("월", db_index=True)
    item_code = models.CharField("품목코드", max_length=64)
    item_name = models.CharField("품목명", max_length=256, blank=True)
    voucher_no = models.CharField("전표별", max_length=32, db_index=True)
    item_label = models.CharField("품목별", max_length=256, blank=True)
    customer_name = models.CharField("거래처별", max_length=256, blank=True)
    customer_code = models.CharField("거래처코드", max_length=32, blank=True)
    quantity = models.DecimalField("수량", max_digits=16, decimal_places=4, default=0)
    supply_amount = models.DecimalField("공급가액", max_digits=16, decimal_places=2, default=0)
    vat = models.DecimalField("부가세", max_digits=16, decimal_places=2, default=0)
    total = models.DecimalField("합계", max_digits=16, decimal_places=2, default=0)
    memo = models.CharField("적요", max_length=512, blank=True)

    item_category_code = models.CharField("품목분류코드", max_length=8, blank=True)
    item_category_name = models.CharField("품목분류", max_length=64)
    customer_category_code = models.CharField("거래처분류코드", max_length=8, blank=True)
    customer_category_name = models.CharField("거래처분류", max_length=64)

    is_unclassified_item = models.BooleanField("품목 미분류", default=False)
    is_unclassified_customer = models.BooleanField("거래처 미분류", default=False)
    source_file = models.CharField("원본파일", max_length=256, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "매출 원자료"
        verbose_name_plural = "매출 원자료"
        indexes = [
            models.Index(fields=["year", "month"]),
            models.Index(fields=["year", "month", "customer_category_code", "item_category_code"]),
        ]

    def __str__(self):
        return f"{self.year}-{self.month:02d} {self.voucher_no} {self.item_code}"


class PendingSalesImport(models.Model):
    """재업로드 확인 대기 중인 임시 import 데이터"""

    session_key = models.CharField(max_length=40, db_index=True)
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    records = models.JSONField()
    source_files = models.CharField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "대기 중 업로드"
        unique_together = [("session_key", "year", "month")]

    def __str__(self):
        return f"pending {self.year}-{self.month:02d}"
