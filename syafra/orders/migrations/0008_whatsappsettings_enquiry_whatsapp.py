from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0007_whatsappsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='whatsappsettings',
            name='enquiry_whatsapp',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Customer-facing WhatsApp for wa.me links (e.g. 919876543210). Can differ from Twilio sender number.',
                max_length=20,
            ),
        ),
    ]
