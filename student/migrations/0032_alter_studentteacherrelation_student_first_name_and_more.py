# Generated by Django 4.2.13 on 2025-01-13 04:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0031_guestlesson_notified'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentteacherrelation',
            name='student_first_name',
            field=models.CharField(default='unknown'),
        ),
        migrations.AlterField(
            model_name='studentteacherrelation',
            name='student_last_name',
            field=models.CharField(default='unknown'),
        ),
    ]