from django.db import models, transaction
from core.models import User
from school.models import School, Course
import random
import string
from utils.schedule_utils import compute_available_time
import uuid
from django.core.exceptions import ValidationError
from datetime import timezone
import pytz

# Create your models here.

gmt7 = pytz.timezone("Asia/Bangkok")  # GMT+7 (Example: Thailand)

class Teacher(models.Model):
    user = models.OneToOneField(User, models.CASCADE)
    school = models.ForeignKey(School, models.CASCADE, related_name="teacher")
    # available_times = models.JSONField(default=list)  # Add available_times field
    course = models.ManyToManyField(Course, related_name="teacher")
    teacher_break = models.PositiveIntegerField(default=15)
    
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
    ]

    code = models.CharField(max_length=12, unique=True)
    datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    status = models.CharField(choices=STATUS_CHOICES, max_length=5, default="PENTE")
    course = models.ForeignKey(to=Course, on_delete=models.CASCADE, related_name="lesson")
    teacher = models.ForeignKey(to=Teacher, on_delete=models.PROTECT, related_name="lesson", null=True, blank=True)
    
    number_of_client = models.IntegerField(default=0)

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

    def check_for_conflicts(self):
        """Check for conflicting lessons when status is changed to 'PENTE'."""
        if not self.course.is_group:
            conflicting_lessons = Lesson.objects.filter(
                teacher=self.teacher,
                status__in=['CON', 'PENTE'],
                datetime__lt=self.end_datetime,  # Existing lesson starts before new lesson ends
                end_datetime__gt=self.datetime  # Existing lesson ends after new lesson starts
            )
            print(conflicting_lessons)
            for lesson in conflicting_lessons:
                print(lesson.datetime)
            if conflicting_lessons.exists():
                raise ValidationError("There is a conflicting lesson during this time.")

    def check_available_time(self):
        """Check if the lesson is within the teacher's available time."""
        # Convert lesson times to GMT
        start_gmt = self.datetime.astimezone(gmt7)
        lesson_start_gmt = start_gmt.time()
        lesson_end_gmt = self.end_datetime.astimezone(gmt7).time()
        lesson_day = str(start_gmt.weekday() + 1)

        available_times = AvailableTime.objects.filter(
            teacher=self.teacher,
            day=lesson_day,
            start__lte=lesson_start_gmt,
            stop__gte=lesson_end_gmt
        )
        if not available_times.exists():
            raise ValidationError("The lesson is not within the teacher's available time.")

    def check_unavailable_time(self):
        """Check if the lesson conflicts with the teacher's unavailable times."""
        conflicting_unavailable_times = UnavailableTimeOneTime.objects.filter(
            teacher=self.teacher,
            date=self.datetime.date(),
            start__lt=self.end_datetime.time(),
            stop__gt=self.datetime.time()
        ) 
        if conflicting_unavailable_times.exists():
            raise ValidationError("The lesson conflicts with the teacher's unavailable times.")

    def save(self, *args, **kwargs):
        with transaction.atomic():  # Ensure database consistency
            if not self.code:
                self.code = self._generate_unique_code(12)
            self.check_for_conflicts()  # Check for conflicts before saving
            super(Lesson, self).save(*args, **kwargs)
            