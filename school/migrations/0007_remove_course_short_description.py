# Generated by Django 4.2.13 on 2024-07-30 09:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('school', '0006_alter_course_short_description'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='course',
            name='short_description',
        ),
    ]