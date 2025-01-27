from django.db import models
import secrets
import uuid
import datetime
import random
# Create your models here.

class School(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=300)
    registered_date = models.DateField(auto_now_add=True)
    payment_qr_code = models.FileField(upload_to="payment_qr_code/", null=True, blank=True)
    # phone_number = models.IntegerField()
    # email = models.EmailField()
    start = models.TimeField(default=datetime.time(8, 0))
    stop = models.TimeField(default=datetime.time(15, 0))
    location = models.CharField(max_length=255, null=True, blank=True)
    
    def __str__(self) -> str:
        return self.name
    
    def number_of_teachers(self):
        return self.teachers.count()
    number_of_teachers.short_description = 'Number of Teachers'

class Course(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=300, null=True, blank=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    no_exp = models.BooleanField()
    exp_range = models.IntegerField(null=True, blank=True)
    duration = models.IntegerField(default=60)
    number_of_lessons = models.IntegerField(default=10)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    created_date = models.DateField(auto_now_add=True)
    price = models.FloatField(null=True, blank=True)

    image = models.FileField(upload_to="course_images/", null=True, blank=True)

    is_group = models.BooleanField()
    group_size = models.IntegerField(null=True)
    
    def __str__(self) -> str:
        return self.name
