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
    available_times = models.JSONField(default=list)  # Add available_times field

    def clean(self):
        """Validate available_times field."""
        allowed_keys = {'date', 'start', 'stop'}
        for time_slot in self.available_times:
            if not allowed_keys.issuperset(time_slot.keys()):
                raise ValidationError(f"Only 'date', 'start', and 'stop' fields are allowed in each time slot.")
            if not all(key in time_slot for key in allowed_keys):
                raise ValidationError("Each time slot must contain 'date', 'start', and 'stop' fields.")
            if not (1 <= int(time_slot['date']) <= 7):
                raise ValidationError("The 'date' field must be between 1 and 7.")
            try:
                start_time = datetime.strptime(time_slot['start'], '%H:%M').time()
                stop_time = datetime.strptime(time_slot['stop'], '%H:%M').time()
            except ValueError:
                raise ValidationError("Time fields must be in HH:MM format.")
            if start_time >= stop_time:
                raise ValidationError("'start' time must be before 'stop' time.")

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
    available_time = models.ForeignKey(to=Teacher, on_delete=models.deletion.CASCADE, blank=True, null=True, related_name='lesson'),

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
                datetime__gte=self.available_time.start,
                datetime__lt=self.available_time.stop,
                status__in=['PENTE', 'AVA']  # Only remove pending and available lessons
            )
            conflicting_lessons.delete()

    def regenerate_available_lessons(self):
        """Recompute available lesson slots after removing conflicts."""
        if not self.course.is_group:
            # Get school settings
            school_settings = self.teacher.school.settings
            interval = school_settings.interval

            # Compute available slots for the given teacher
            unavailables = list(self.teacher.unavailable_once.all())
            lessons = list(self.teacher.lesson.exclude(status__in=['CON', 'CAN']))
            
            available_slots = compute_available_time(
                unavailables=unavailables,
                lessons=lessons,
                date_time=self.datetime.date(),
                start=self.available_time.start,
                stop=self.available_time.stop,
                duration=self.course.duration,
                interval=interval
            )

            # Track already generated codes in memory
            generated_codes = set(Lesson.objects.values_list('code', flat=True))

            new_lessons = []
            for slot in available_slots:
                while True:
                    lesson_code = self._generate_unique_code(12)
                    if lesson_code not in generated_codes:
                        generated_codes.add(lesson_code)  # Add to the tracking set
                        break  # Unique code found, exit loop

                new_lessons.append(
                    Lesson(
                        code=lesson_code,
                        datetime=slot['start'],
                        status='AVA',
                        course=self.course,
                        teacher=self.teacher,
                        available_time=self.available_time
                    )
                )

            # Bulk insert new available lessons
            if new_lessons:
                Lesson.objects.bulk_create(new_lessons, batch_size=100)

    def save(self, *args, **kwargs):
        with transaction.atomic():  # Ensure database consistency
            if not self.code:
                self.code = self._generate_unique_code(12)

            super(Lesson, self).save(*args, **kwargs)

            # Check if the lesson's course requires rescheduling
            if not self.course.is_group:
                self.remove_conflicting_lessons()  # Step 1: Remove conflicts
                self.regenerate_available_lessons()  # Step 2: Regenerate available slots