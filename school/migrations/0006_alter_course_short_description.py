# Generated by Django 4.2.13 on 2024-07-25 15:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('school', '0005_course_short_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='short_description',
            field=models.CharField(max_length=100),
        ),
    ]