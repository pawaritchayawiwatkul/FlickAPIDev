# Generated by Django 4.2.13 on 2024-11-06 03:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('teacher', '0011_delete_makeuplesson'),
        ('student', '0021_lesson_online'),
    ]

    operations = [
        migrations.CreateModel(
            name='MakeUpLesson',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notes', models.CharField(blank=True, max_length=300)),
                ('name', models.CharField(blank=True, max_length=300)),
                ('booked_datetime', models.DateTimeField()),
                ('duration', models.IntegerField()),
                ('code', models.CharField(max_length=12, unique=True)),
                ('status', models.CharField(choices=[('PEN', 'Pending'), ('CON', 'Confirmed'), ('COM', 'Completed'), ('CAN', 'Canceled'), ('MIS', 'Missed')], default='PEN', max_length=3)),
                ('online', models.BooleanField(default=False)),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='teacher.teacher')),
            ],
        ),
    ]