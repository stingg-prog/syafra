from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0020_alter_order_status_add_failed"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="tracking_id",
            field=models.CharField(blank=True, db_index=True, default="", max_length=100),
        ),
    ]
