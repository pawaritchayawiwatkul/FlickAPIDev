# Generated by Django 4.2.13 on 2025-01-13 04:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('teacher', '0022_alter_teacher_school'),
        ('student', '0032_alter_studentteacherrelation_student_first_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='courseregistration',
            name='teacher',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='registration', to='teacher.teacher'),
        ),
    ]