# Generated by Django 4.2.13 on 2025-01-27 08:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0045_alter_courseregistration_teacher'),
    ]

    operations = [
        migrations.RenameField(
            model_name='courseregistration',
            old_name='profile_image',
            new_name='payment_slip',
        ),
    ]