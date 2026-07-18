from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0014_contactmessage_contentpage'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='InstagramPost',
            new_name='InstagramFeedItem',
        ),
        migrations.AlterModelOptions(
            name='instagramfeeditem',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Instagram Feed Item',
                'verbose_name_plural': 'Instagram Feed Items',
            },
        ),
        migrations.AddField(
            model_name='product',
            name='short_description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='product',
            name='slug',
            field=models.SlugField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='product',
            name='is_published',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='websitesettings',
            name='instagram_auto_publish',
            field=models.BooleanField(
                default=False,
                help_text='Automatically publish products to Instagram when marked as Published.',
            ),
        ),
        migrations.CreateModel(
            name='InstagramPost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('container_id', models.CharField(blank=True, default='', max_length=255)),
                ('post_id', models.CharField(blank=True, default='', max_length=255)),
                ('caption', models.TextField(blank=True, default='')),
                ('status', models.CharField(
                    choices=[
                        ('not_published', 'Not Published'),
                        ('publishing', 'Publishing'),
                        ('published', 'Published'),
                        ('failed', 'Failed'),
                    ],
                    default='not_published',
                    max_length=20,
                )),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('error_log', models.TextField(blank=True, default='')),
                ('api_response', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='instagram_post',
                    to='products.product',
                )),
            ],
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Instagram Post',
                'verbose_name_plural': 'Instagram Posts',
            },
        ),
    ]
