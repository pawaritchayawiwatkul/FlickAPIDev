# Generated by Django 4.2.13 on 2025-02-20 14:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0002_alter_booking_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='points',
            field=models.IntegerField(default=0),
        ),
    ]
