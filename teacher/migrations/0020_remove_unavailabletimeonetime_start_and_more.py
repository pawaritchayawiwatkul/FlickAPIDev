# Generated by Django 4.2.13 on 2024-11-29 11:03

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('teacher', '0019_alter_unavailabletimeonetime_start_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='unavailabletimeonetime',
            name='start',
        ),
        migrations.RemoveField(
            model_name='unavailabletimeonetime',
            name='stop',
        ),
        migrations.AddField(
            model_name='unavailabletimeonetime',
            name='date',
            field=models.DateField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]