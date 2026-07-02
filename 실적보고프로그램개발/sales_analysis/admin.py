from django.contrib import admin



from sales_analysis.models import (
    CustomerCategoryMaster,
    ItemCategoryMaster,
    PendingProfitImport,
    PendingSalesImport,
    ProfitRecord,
    SalesRecord,
    WelfareOutputItem,
    WelfareOutputItemMapping,
)





@admin.register(ItemCategoryMaster)

class ItemCategoryMasterAdmin(admin.ModelAdmin):

    list_display = ("code", "name", "is_active", "sort_order")

    list_editable = ("name", "is_active", "sort_order")

    ordering = ("sort_order", "code")





@admin.register(CustomerCategoryMaster)

class CustomerCategoryMasterAdmin(admin.ModelAdmin):

    list_display = ("code", "name", "is_active", "sort_order")

    list_editable = ("name", "is_active", "sort_order")

    ordering = ("sort_order", "code")





@admin.register(SalesRecord)

class SalesRecordAdmin(admin.ModelAdmin):

    list_display = (

        "year",

        "month",

        "voucher_no",

        "item_code",

        "item_category_code",

        "customer_category_code",

        "total",

        "is_unclassified_item",

        "is_unclassified_customer",

    )

    list_filter = ("year", "month", "item_category_code", "customer_category_code")

    search_fields = ("voucher_no", "item_code", "customer_code", "customer_name")

    list_per_page = 50





@admin.register(ProfitRecord)
class ProfitRecordAdmin(admin.ModelAdmin):
    list_display = (
        "item_code",
        "item_name",
        "item_category_code",
        "quantity",
        "amount",
        "period_label",
        "is_unclassified_item",
    )
    list_filter = ("is_unclassified_item",)
    search_fields = ("category_label", "item_category_code")


@admin.register(PendingProfitImport)
class PendingProfitImportAdmin(admin.ModelAdmin):
    list_display = ("session_key", "period_label", "created_at")


@admin.register(PendingSalesImport)
class PendingSalesImportAdmin(admin.ModelAdmin):

    list_display = ("session_key", "year", "month", "created_at")

    list_filter = ("year", "month")


class WelfareOutputItemMappingInline(admin.TabularInline):
    model = WelfareOutputItemMapping
    extra = 1


@admin.register(WelfareOutputItem)
class WelfareOutputItemAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "sort_order", "is_fallback")
    list_editable = ("is_active", "sort_order")
    ordering = ("sort_order", "code")
    inlines = [WelfareOutputItemMappingInline]


@admin.register(WelfareOutputItemMapping)
class WelfareOutputItemMappingAdmin(admin.ModelAdmin):
    list_display = ("item_category_code", "welfare_item")
    list_filter = ("welfare_item",)
