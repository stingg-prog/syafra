from django.db import migrations


def forwards(apps, schema_editor):
    WhatsAppSettings = apps.get_model('orders', 'WhatsAppSettings')
    if WhatsAppSettings.objects.exists():
        return
    WhatsAppSettings.objects.create()


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0008_whatsappsettings_enquiry_whatsapp'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
