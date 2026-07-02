from django.db import migrations, models

from sales_analysis.constants import WELFARE_ETC_GROUP_ID, WELFARE_OUTPUT_ITEMS


def seed_welfare_output_items(apps, schema_editor):
    WelfareOutputItem = apps.get_model("sales_analysis", "WelfareOutputItem")
    WelfareOutputItemMapping = apps.get_model("sales_analysis", "WelfareOutputItemMapping")
    if WelfareOutputItem.objects.exists():
        return
    for index, (code, name, codes) in enumerate(WELFARE_OUTPUT_ITEMS):
        item = WelfareOutputItem.objects.create(
            code=code,
            name=name,
            is_active=True,
            sort_order=index,
            is_fallback=(code == WELFARE_ETC_GROUP_ID),
        )
        WelfareOutputItemMapping.objects.bulk_create(
            [
                WelfareOutputItemMapping(welfare_item=item, item_category_code=c)
                for c in codes
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("sales_analysis", "0002_category_masters"),
    ]

    operations = [
        migrations.CreateModel(
            name="WelfareOutputItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=32, unique=True, verbose_name="내부코드")),
                ("name", models.CharField(max_length=64, verbose_name="출력항목")),
                ("is_active", models.BooleanField(default=True, verbose_name="사용")),
                ("sort_order", models.PositiveSmallIntegerField(default=0, verbose_name="정렬")),
                ("is_fallback", models.BooleanField(default=False, verbose_name="미매핑 기본항목")),
            ],
            options={
                "verbose_name": "복지부 출력항목",
                "verbose_name_plural": "복지부 출력항목",
                "ordering": ["sort_order", "code"],
            },
        ),
        migrations.CreateModel(
            name="WelfareOutputItemMapping",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("item_category_code", models.CharField(max_length=1, verbose_name="품목코드")),
                (
                    "welfare_item",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="mappings",
                        to="sales_analysis.welfareoutputitem",
                        verbose_name="출력항목",
                    ),
                ),
            ],
            options={
                "verbose_name": "복지부 품목코드 매핑",
                "verbose_name_plural": "복지부 품목코드 매핑",
                "ordering": ["item_category_code"],
            },
        ),
        migrations.AddConstraint(
            model_name="welfareoutputitemmapping",
            constraint=models.UniqueConstraint(
                fields=("item_category_code",),
                name="unique_welfare_item_category_code",
            ),
        ),
        migrations.RunPython(seed_welfare_output_items, migrations.RunPython.noop),
    ]
