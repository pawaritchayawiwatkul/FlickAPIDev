# Generated by Django 4.2.13 on 2025-01-27 08:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0042_alter_courseregistration_teacher'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='booked_datetime',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
