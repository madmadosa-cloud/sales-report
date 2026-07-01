from django.contrib import admin

from sales_analysis.models import PendingSalesImport, SalesRecord


@admin.register(SalesRecord)
class SalesRecordAdmin(admin.ModelAdmin):
    list_display = (
        "year",
        "month",
        "voucher_no",
        "item_code",
        "item_category_name",
        "customer_category_name",
        "total",
        "is_unclassified_item",
        "is_unclassified_customer",
    )
    list_filter = ("year", "month", "customer_category_name", "item_category_name")
    search_fields = ("voucher_no", "item_code", "customer_code", "customer_name")
    list_per_page = 50


@admin.register(PendingSalesImport)
class PendingSalesImportAdmin(admin.ModelAdmin):
    list_display = ("session_key", "year", "month", "created_at")
    list_filter = ("year", "month")
