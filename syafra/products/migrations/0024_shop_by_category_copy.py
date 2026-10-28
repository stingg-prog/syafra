from django.db import migrations, models


CARD_COPY = (
    {
        "target_slug": "womens-top-99",
        "old_slug": "lavender",
        "old_headline": "LAVENDER",
        "headline": "THE VALUE EDIT",
        "title": "₹99 Collection",
        "description": "Everyday Fashion",
    },
    {
        "target_slug": "womens-top-199",
        "old_slug": "womens-top-99",
        "old_headline": "WOMENS TOP 99",
        "headline": "THE STYLE EDIT",
        "title": "₹199 Collection",
        "description": "Trending Fashion",
    },
)


def update_shop_by_category_cards(apps, schema_editor):
    HomepageSection = apps.get_model("products", "HomepageSection")
    ShopByCategoryItem = apps.get_model("products", "ShopByCategoryItem")
    Category = apps.get_model("products", "Category")

    section = (
        HomepageSection.objects.filter(section_type="shop_by_category", is_active=True)
        .order_by("display_order", "pk")
        .first()
    )
    if section is None:
        return

    items = list(
        ShopByCategoryItem.objects.filter(section=section, is_active=True)
        .order_by("display_order", "pk")[:2]
    )
    # Move the second card first so its current WOMENS TOP 99 category is free
    # for the first card's new link target.
    for item, copy in zip(reversed(items), reversed(CARD_COPY)):
        category = Category.objects.filter(slug__iexact=copy["target_slug"]).first()
        if category is None:
            continue
        item.category_id = category.pk
        item.headline = copy["headline"]
        item.display_title = copy["title"]
        item.display_description = copy["description"]
        item.save(
            update_fields=(
                "category",
                "headline",
                "display_title",
                "display_description",
            )
        )


def restore_shop_by_category_cards(apps, schema_editor):
    HomepageSection = apps.get_model("products", "HomepageSection")
    ShopByCategoryItem = apps.get_model("products", "ShopByCategoryItem")
    Category = apps.get_model("products", "Category")

    section = (
        HomepageSection.objects.filter(section_type="shop_by_category", is_active=True)
        .order_by("display_order", "pk")
        .first()
    )
    if section is None:
        return

    items = list(
        ShopByCategoryItem.objects.filter(section=section, is_active=True)
        .order_by("display_order", "pk")[:2]
    )
    for item, copy in zip(items, CARD_COPY):
        category = Category.objects.filter(slug__iexact=copy["old_slug"]).first()
        if category is not None:
            item.category_id = category.pk
        item.headline = copy["old_headline"]
        item.display_title = ""
        item.display_description = ""
        item.save(
            update_fields=(
                "category",
                "headline",
                "display_title",
                "display_description",
            )
        )


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0023_product_material"),
    ]

    operations = [
        migrations.AddField(
            model_name="shopbycategoryitem",
            name="display_title",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="shopbycategoryitem",
            name="display_description",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.RunPython(
            update_shop_by_category_cards,
            restore_shop_by_category_cards,
        ),
    ]
