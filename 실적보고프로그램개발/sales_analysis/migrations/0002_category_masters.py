# Generated manually for category master migration

import django.db.models.deletion
from django.db import migrations, models


SEED_ITEM_CATEGORIES = {
    "a": "복사용지",
    "b": "화장지물티슈",
    "c": "장갑피복류",
    "d": "가구",
    "e": "사무용품",
    "f": "인쇄판촉물",
    "g": "세제",
    "h": "식품류",
    "i": "마대비닐봉투",
    "j": "종이컵",
    "k": "서비스용역",
    "l": "마스크",
    "m": "노트북장",
    "n": "종이박스",
    "o": "전기충전기",
    "p": "간판",
    "q": "LED등기구",
    "r": "멀티탭",
    "s": "블라인드",
    "t": "원격수도검침",
    "u": "전기설비발전기",
    "z": "일반품목",
}

SEED_CUSTOMER_CATEGORIES = {
    "a": "지방자치단체",
    "b": "교육기관",
    "c": "국가기관",
    "d": "공공기관",
    "e": "기타",
    "z": "생산시설",
}


def seed_masters(apps, schema_editor):
    ItemCategoryMaster = apps.get_model("sales_analysis", "ItemCategoryMaster")
    CustomerCategoryMaster = apps.get_model("sales_analysis", "CustomerCategoryMaster")
    for idx, (code, name) in enumerate(SEED_ITEM_CATEGORIES.items()):
        ItemCategoryMaster.objects.get_or_create(
            code=code,
            defaults={"name": name, "sort_order": idx, "is_active": True},
        )
    for idx, (code, name) in enumerate(SEED_CUSTOMER_CATEGORIES.items()):
        CustomerCategoryMaster.objects.get_or_create(
            code=code,
            defaults={"name": name, "sort_order": idx, "is_active": True},
        )


def clear_pending_imports(apps, schema_editor):
    PendingSalesImport = apps.get_model("sales_analysis", "PendingSalesImport")
    PendingSalesImport.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("sales_analysis", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ItemCategoryMaster",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=1, unique=True, verbose_name="코드")),
                ("name", models.CharField(max_length=64, verbose_name="분류명")),
                ("is_active", models.BooleanField(default=True, verbose_name="사용")),
                ("sort_order", models.PositiveSmallIntegerField(default=0, verbose_name="정렬")),
            ],
            options={
                "verbose_name": "품목분류코드",
                "verbose_name_plural": "품목분류코드",
                "ordering": ["sort_order", "code"],
            },
        ),
        migrations.CreateModel(
            name="CustomerCategoryMaster",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=1, unique=True, verbose_name="코드")),
                ("name", models.CharField(max_length=64, verbose_name="분류명")),
                ("is_active", models.BooleanField(default=True, verbose_name="사용")),
                ("sort_order", models.PositiveSmallIntegerField(default=0, verbose_name="정렬")),
            ],
            options={
                "verbose_name": "거래처분류코드",
                "verbose_name_plural": "거래처분류코드",
                "ordering": ["sort_order", "code"],
            },
        ),
        migrations.RunPython(seed_masters, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="salesrecord",
            name="customer_category_name",
        ),
        migrations.RemoveField(
            model_name="salesrecord",
            name="item_category_name",
        ),
        migrations.RunPython(clear_pending_imports, migrations.RunPython.noop),
    ]

