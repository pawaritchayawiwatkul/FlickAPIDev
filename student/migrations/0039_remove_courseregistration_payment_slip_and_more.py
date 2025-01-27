# Generated by Django 4.2.13 on 2025-01-24 10:52

from django.db import migrations, models
import student.models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0038_remove_courseregistration_status'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='courseregistration',
            name='payment_slip',
        ),
        migrations.RemoveField(
            model_name='courseregistration',
            name='payment_validated',
        ),
        migrations.AddField(
            model_name='courseregistration',
            name='payment_status',
            field=models.CharField(choices=[('confirm', 'Confirm'), ('waiting', 'Waiting'), ('denied', 'Denied')], default='waiting', max_length=10),
        ),
        migrations.AddField(
            model_name='courseregistration',
            name='profile_image',
            field=models.FileField(blank=True, null=True, upload_to=student.models.file_generate_upload_path),
        ),
    ]
