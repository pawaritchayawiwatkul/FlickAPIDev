# Generated by Django 4.2.13 on 2024-11-11 04:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0025_studentteacherrelation_student_color_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='guestlesson',
            name='email',
            field=models.CharField(blank=True, max_length=300),
        ),
        migrations.AlterField(
            model_name='guestlesson',
            name='name',
            field=models.CharField(max_length=300),
        ),
        migrations.AlterField(
            model_name='studentteacherrelation',
            name='student_first_name',
            field=models.CharField(default='unknown124'),
        ),
        migrations.AlterField(
            model_name='studentteacherrelation',
            name='student_last_name',
            field=models.CharField(default='unknown124'),
        ),
    ]