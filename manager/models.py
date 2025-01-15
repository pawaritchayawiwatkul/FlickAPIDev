from django.db import models
from core.models import User
from school.models import School
# Create your models here.

class Admin(models.Model):
    user = models.OneToOneField(User, models.CASCADE)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="admins")
    