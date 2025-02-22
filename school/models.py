from django.db import models
import secrets
import uuid
import datetime
import random
# Create your models here.

class Facilities(models.Model):
    name = models.CharField(max_length=100)
    capacity = models.IntegerField()
    school = models.ForeignKey("School", on_delete=models.CASCADE, related_name="facilities")

    def __str__(self) -> str:
        return self.name
    
class SchoolSettings(models.Model):
    # Schedule
    days_ahead = models.PositiveIntegerField(default=21)
    interval = models.PositiveIntegerField(default=30)
    cancel_b4_hours = models.PositiveIntegerField(default=24)
    teacher_break = models.PositiveIntegerField(default=15)
    
    def __str__(self):
        return f"Schedule Settings for {self.school.name}"

def file_generate_upload_path(instance, filename):
	# Both filename and instance.file_name should have the same values
    return f"school_qr_code/{instance.uuid}"

class School(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=300, null=True, blank=True)
    registered_date = models.DateField(auto_now_add=True)
    payment_qr_code = models.FileField(upload_to=file_generate_upload_path, null=True, blank=True)
    start = models.TimeField(default=datetime.time(8, 0))
    stop = models.TimeField(default=datetime.time(15, 0))
    location = models.CharField(max_length=255, null=True, blank=True)
    settings = models.OneToOneField(SchoolSettings, on_delete=models.CASCADE, related_name="school", null=True, blank=True)

    def __str__(self) -> str:
        return self.name
    
    def number_of_teachers(self):
        return self.teachers.count()
    number_of_teachers.short_description = 'Number of Teachers'
    
    def save(self, *args, **kwargs):
        """Override save to ensure SchoolSettings is created when a School is created."""
        super().save(*args, **kwargs)  # Save the School first
        if self.settings is None:  # Create settings only for new schools
            settings = SchoolSettings.objects.create()
            self.settings = settings
            super().save(update_fields=["settings"])  # Update only the settings field

def file_generate_upload_path(instance, filename):
	# Both filename and instance.file_name should have the same values
    return f"course_image/{instance.uuid}"

class Course(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=300, null=True, blank=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    no_exp = models.BooleanField()
    exp_range = models.IntegerField(null=True, blank=True)
    duration = models.IntegerField(default=60)
    number_of_lessons = models.IntegerField(default=10)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="course")
    created_date = models.DateField(auto_now_add=True)
    price = models.FloatField(null=True, blank=True)

    image = models.FileField(upload_to=file_generate_upload_path, null=True, blank=True)

    is_group = models.BooleanField(default=False)
    group_size = models.IntegerField(null=True)
    
    def __str__(self) -> str:
        return self.name
