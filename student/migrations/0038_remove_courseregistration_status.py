# Generated by Django 4.2.13 on 2025-01-23 12:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0037_courseregistration_payment_slip_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='courseregistration',
            name='status',
        ),
    ]