# Generated by Django 4.2.13 on 2024-11-19 10:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_alter_user_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='google_credentials',
            field=models.JSONField(blank=True, null=True),
        ),
    ]