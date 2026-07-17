"""Replace SendGrid with Resend as email provider.

- Remove old unique constraint on sendgrid_event_id
- Rename sendgrid_* fields to provider_* in EmailLog and EmailWebhookEvent
- Change provider default from 'sendgrid' to 'resend'
- Add new unique constraint on provider_event_id
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_emaillog_event_type"),
    ]

    operations = [
        # Remove old unique constraint BEFORE renaming the field
        migrations.RemoveConstraint(
            model_name="emailwebhookevent",
            name="email_webhook_events_unique_sendgrid_event_id",
        ),
        # EmailLog: rename sendgrid_message_id -> provider_message_id
        migrations.RenameField(
            model_name="emaillog",
            old_name="sendgrid_message_id",
            new_name="provider_message_id",
        ),
        # EmailLog: rename sendgrid_response_status -> provider_response_status
        migrations.RenameField(
            model_name="emaillog",
            old_name="sendgrid_response_status",
            new_name="provider_response_status",
        ),
        # EmailLog: change provider default
        migrations.AlterField(
            model_name="emaillog",
            name="provider",
            field=models.CharField(
                db_index=True, default="resend", max_length=32
            ),
        ),
        # EmailWebhookEvent: rename sendgrid_event_id -> provider_event_id
        migrations.RenameField(
            model_name="emailwebhookevent",
            old_name="sendgrid_event_id",
            new_name="provider_event_id",
        ),
        # EmailWebhookEvent: rename sendgrid_message_id -> provider_message_id
        migrations.RenameField(
            model_name="emailwebhookevent",
            old_name="sendgrid_message_id",
            new_name="provider_message_id",
        ),
        # EmailWebhookEvent: change provider default
        migrations.AlterField(
            model_name="emailwebhookevent",
            name="provider",
            field=models.CharField(
                db_index=True, default="resend", max_length=32
            ),
        ),
        # Add new unique constraint
        migrations.AddConstraint(
            model_name="emailwebhookevent",
            constraint=models.UniqueConstraint(
                condition=models.Q(("provider_event_id", ""), _negated=True),
                fields=("provider_event_id",),
                name="email_webhook_events_unique_provider_event_id",
            ),
        ),
    ]
