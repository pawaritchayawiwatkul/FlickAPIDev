# Generated by Django 4.2.13 on 2025-01-27 10:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0046_rename_profile_image_courseregistration_payment_slip'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='code',
            field=models.CharField(default='asdf', max_length=12),
            preserve_default=False,
        ),
    ]
