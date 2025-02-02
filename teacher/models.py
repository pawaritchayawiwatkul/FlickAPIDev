from django.db import models, transaction
from core.models import User
from school.models import School, Course
import random
import string
from utils.schedule_utils import compute_available_time
import uuid
from django.core.exceptions import ValidationError
from datetime import datetime
# Create your models here.

    
class Teacher(models.Model):
    user = models.OneToOneField(User, models.CASCADE)
    school = models.ForeignKey(School, models.CASCADE, related_name="teacher")
    # available_times = models.JSONField(default=list)  # Add available_times field
    course = models.ManyToManyField(Course, related_name="teacher")

    def save(self, *args, **kwargs):
        self.clean()  # Validate before saving
        super(Teacher, self).save(*args, **kwargs)

    def __str__(self) -> str:
        return self.user.__str__()

class UnavailableTimeOneTime(models.Model):
    date = models.DateField()
    start = models.TimeField()
    stop = models.TimeField()
    teacher = models.ForeignKey(Teacher, models.CASCADE, related_name="unavailable_once")
    code = models.CharField(max_length=12, unique=True)

    def generate_unique_code(self, length=8):
        """Generate a unique random code."""
        characters = string.ascii_letters + string.digits
        code = ''.join(random.choice(characters) for _ in range(length))
        return code
    
    def _generate_unique_code(self, length):
        """Generate a unique code and ensure it's not already in the database."""
        code = self.generate_unique_code(length)
        while UnavailableTimeOneTime.objects.filter(code=code).exists() or UnavailableTimeRegular.objects.filter(code=code).exists():
            code = self.generate_unique_code(length)
        return code
    
    def save(self, *args, **kwargs):
        if self.code is None or self.code == "":
            self.code = self._generate_unique_code(12)
        super(UnavailableTimeOneTime, self).save(*args, **kwargs)
        
class UnavailableTimeRegular(models.Model):
    DAY_CHOICES = [
        ('1', 'Monday'),
        ('2', 'Tuesday'),
        ('3', 'Wednesday'),
        ('4', 'Thursday'),
        ('5', 'Friday'),
        ('6', 'Saturday'),
        ('7', 'Sunday'),
    ]
    day = models.CharField(max_length=1, choices=DAY_CHOICES)
    start = models.TimeField()
    stop = models.TimeField()
    teacher = models.ForeignKey(Teacher, models.CASCADE, related_name="unavailable_reg")
    code = models.CharField(max_length=12, unique=True)
    
    def generate_unique_code(self, length=8):
        """Generate a unique random code."""
        characters = string.ascii_letters + string.digits
        code = ''.join(random.choice(characters) for _ in range(length))
        return code
    
    def _generate_unique_code(self, length):
        """Generate a unique code and ensure it's not already in the database."""
        code = self.generate_unique_code(length)
        while UnavailableTimeOneTime.objects.filter(code=code).exists() or UnavailableTimeRegular.objects.filter(code=code).exists():
            code = self.generate_unique_code(length)
        return code
    
    def save(self, *args, **kwargs):
        if self.code is None or self.code == "":
            self.code = self._generate_unique_code(12)
        super(UnavailableTimeRegular, self).save(*args, **kwargs)


class AvailableTime(models.Model):
    DAY_CHOICES = [
        ('1', 'Monday'),
        ('2', 'Tuesday'),
        ('3', 'Wednesday'),
        ('4', 'Thursday'),
        ('5', 'Friday'),
        ('6', 'Saturday'),
        ('7', 'Sunday'),
    ]
    day = models.CharField(max_length=1, choices=DAY_CHOICES)
    start = models.TimeField()
    stop = models.TimeField()
    teacher = models.ForeignKey(Teacher, models.CASCADE, related_name="available_time")
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return f"{self.get_day_display()} {self.start} - {self.stop}"
    
class Lesson(models.Model):
    STATUS_CHOICES = [
        ('PENTE', 'PendingTeacher'),
        ('CON', 'Confirmed'),
        ('COM', 'Completed'),
        ('CAN', 'Canceled'),
        ('AVA', 'Available'),
    ]

    code = models.CharField(max_length=12, unique=True)
    datetime = models.DateTimeField()
    status = models.CharField(choices=STATUS_CHOICES, max_length=5, default="PENTE")
    course = models.ForeignKey(to=Course, on_delete=models.CASCADE, related_name="lesson")
    teacher = models.ForeignKey(to=Teacher, on_delete=models.PROTECT, related_name="lesson", null=True, blank=True)
    
    number_of_client = models.IntegerField(default=0)

    # stop_available = models.DateTimeField(null=True, blank=True)

    notified = models.BooleanField(default=False)
    student_event_id = models.CharField(null=True, blank=True)
    teacher_event_id = models.CharField(null=True, blank=True)

    def generate_unique_code(self, length=8):
        """Generate a unique random code."""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    def _generate_unique_code(self, length):
        """Generate a unique code and ensure it's not already in the database."""
        code = self.generate_unique_code(length)
        while Lesson.objects.filter(code=code).exists():
            code = self.generate_unique_code(length)
        return code

    def remove_conflicting_lessons(self):
        """Remove lessons that conflict with this lesson's time if course.is_course is False."""
        if not self.course.is_group:
            conflicting_lessons = Lesson.objects.filter(
                teacher=self.teacher,
                datetime__lt=self.datetime + self.course.duration,
                datetime__gt=self.datetime,
                status__in=['PENTE', 'AVA']  # Only remove pending and available lessons
            )
            conflicting_lessons.delete()

    def check_for_conflicts(self):
        """Check for conflicting lessons when status is changed to 'CON'."""
        if not self.course.is_group:
            conflicting_lessons = Lesson.objects.filter(
                teacher=self.teacher,
                datetime__lt=self.datetime + self.course.duration,
                datetime__gt=self.datetime,
                status='CON'
            )
            if conflicting_lessons.exists():
                raise ValidationError("There is a conflicting lesson during this time.")

    def save(self, *args, **kwargs):
        with transaction.atomic():  # Ensure database consistency
            if not self.code:
                self.code = self._generate_unique_code(12)

            # Check if the status is changing to 'CON'
            if self.pk is None:
                status_changed_to_confirm = True
            elif self.status != 'CON':
                status_changed_to_confirm = False
            else:
                previous_status = Lesson.objects.get(pk=self.pk).status
                status_changed_to_confirm = self.status == 'CON' and previous_status != 'CON'

            if status_changed_to_confirm:
                self.check_for_conflicts()  # Check for conflicts before saving

            super(Lesson, self).save(*args, **kwargs)

            # Check if the lesson's course requires rescheduling and status changed to 'CON'
            if not self.course.is_group and status_changed_to_confirm:
                self.remove_conflicting_lessons()  # Step 1: Remove conflicts
                # self.regenerate_available_lessons()  # Step 2: Regenerate available slots
                