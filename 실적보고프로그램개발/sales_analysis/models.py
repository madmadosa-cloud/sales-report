from django.db import models





class ItemCategoryMaster(models.Model):

    """품목분류코드 마스터"""



    code = models.CharField("코드", max_length=1, unique=True)

    name = models.CharField("분류명", max_length=64)

    is_active = models.BooleanField("사용", default=True)

    sort_order = models.PositiveSmallIntegerField("정렬", default=0)



    class Meta:

        verbose_name = "품목분류코드"

        verbose_name_plural = "품목분류코드"

        ordering = ["sort_order", "code"]



    def __str__(self):

        return f"{self.code}: {self.name}"





class CustomerCategoryMaster(models.Model):

    """거래처분류코드 마스터"""



    code = models.CharField("코드", max_length=1, unique=True)

    name = models.CharField("분류명", max_length=64)

    is_active = models.BooleanField("사용", default=True)

    sort_order = models.PositiveSmallIntegerField("정렬", default=0)



    class Meta:

        verbose_name = "거래처분류코드"

        verbose_name_plural = "거래처분류코드"

        ordering = ["sort_order", "code"]



    def __str__(self):

        return f"{self.code}: {self.name}"




class WelfareOutputItem(models.Model):
    """복지부보고서 출력항목 (품목코드 합산 그룹)"""

    code = models.CharField("내부코드", max_length=32, unique=True)
    name = models.CharField("출력항목", max_length=64)
    is_active = models.BooleanField("사용", default=True)
    sort_order = models.PositiveSmallIntegerField("정렬", default=0)
    is_fallback = models.BooleanField("미매핑 기본항목", default=False)

    class Meta:
        verbose_name = "복지부 출력항목"
        verbose_name_plural = "복지부 출력항목"
        ordering = ["sort_order", "code"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class WelfareOutputItemMapping(models.Model):
    """출력항목에 합산할 품목분류코드"""

    welfare_item = models.ForeignKey(
        WelfareOutputItem,
        on_delete=models.CASCADE,
        related_name="mappings",
        verbose_name="출력항목",
    )
    item_category_code = models.CharField("품목코드", max_length=1)

    class Meta:
        verbose_name = "복지부 품목코드 매핑"
        verbose_name_plural = "복지부 품목코드 매핑"
        ordering = ["item_category_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["item_category_code"],
                name="unique_welfare_item_category_code",
            ),
        ]

    def __str__(self):
        return f"{self.item_category_code} → {self.welfare_item.name}"




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

    customer_category_code = models.CharField("거래처분류코드", max_length=8, blank=True)



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




class ProfitRecord(models.Model):
    """이익현황 원자료 (품목/거래처 행 단위 스냅샷)"""

    item_code = models.CharField("품목코드", max_length=64, blank=True)
    item_name = models.CharField("품목명", max_length=256, blank=True)
    customer_code = models.CharField("거래처코드", max_length=32, blank=True)
    customer_name = models.CharField("거래처명", max_length=256, blank=True)
    category_label = models.CharField("분류명(원본)", max_length=64, blank=True)
    item_category_code = models.CharField("품목분류코드", max_length=8, blank=True)
    quantity = models.DecimalField("판매수량", max_digits=16, decimal_places=4, default=0)
    cost = models.DecimalField("원가", max_digits=16, decimal_places=2, default=0)
    amount = models.DecimalField("이익금", max_digits=16, decimal_places=2, default=0)
    is_unclassified_item = models.BooleanField("품목 미분류", default=False)
    customer_category_code = models.CharField("거래처분류코드", max_length=8, blank=True)
    is_unclassified_customer = models.BooleanField("거래처 미분류", default=False)
    period_label = models.CharField("조회기간(표시용)", max_length=128, blank=True)
    source_file = models.CharField("원본파일", max_length=256, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "이익 원자료"
        verbose_name_plural = "이익 원자료"
        indexes = [
            models.Index(fields=["item_category_code"]),
            models.Index(fields=["customer_category_code"]),
        ]

    def __str__(self):
        return f"{self.category_label or self.item_category_code} {self.amount}"




class PendingProfitImport(models.Model):
    """이익자료 재업로드 확인 대기"""

    session_key = models.CharField(max_length=40, unique=True, db_index=True)
    records = models.JSONField()
    period_label = models.CharField(max_length=128, blank=True)
    source_files = models.CharField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "대기 중 이익 업로드"

    def __str__(self):
        return f"pending profit {self.session_key}"

