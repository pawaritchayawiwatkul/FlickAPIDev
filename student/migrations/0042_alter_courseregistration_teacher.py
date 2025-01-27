# Generated by Django 4.2.13 on 2025-01-27 05:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('teacher', '0026_alter_lesson_teacher'),
        ('student', '0041_remove_booking_lesson_booking_lesson'),
    ]

    operations = [
        migrations.AlterField(
            model_name='courseregistration',
            name='teacher',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='registration', to='teacher.teacher'),
        ),
    ]
