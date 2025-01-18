from django.db import models
from school.models import Course, School
from core.models import User
from teacher.models import Teacher
from django.utils.timezone import make_aware, get_current_timezone
from uuid import uuid4
import random
import string

# Create your models here.
_timezone = get_current_timezone()

class CourseRegistration(models.Model):
    STATUS_CHOICES = [
        ('PEN', 'Pending'),
        ('COM', 'Completed'),
        ('EXP', 'Expired'),
    ]
    uuid = models.UUIDField(default=uuid4, editable=False, unique=True)

    registered_date = models.DateField(auto_now_add=True)
    exp_date = models.DateField(null=True)
    finised_date = models.DateField(null=True, blank=True)

    status = models.CharField(choices=STATUS_CHOICES, max_length=3, default="PEN")
    used_lessons = models.IntegerField(default=0)

    student_favorite = models.BooleanField(default=False)
    teacher_favorite = models.BooleanField(default=False)

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="registration")
    course = models.ForeignKey(to=Course, on_delete=models.CASCADE, related_name="registration")
    student = models.ForeignKey(to="Student", on_delete=models.CASCADE, related_name="registration")
    
    paid_price = models.FloatField(null=True)
    discount = models.FloatField(null=True)

    def __str__(self) -> str:
        return f"{self.student.__str__()} {self.course.__str__()} {self.teacher.__str__()}"

class StudentTeacherRelation(models.Model):
    student = models.ForeignKey("Student", on_delete=models.CASCADE, related_name="teacher_relation")
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="student_relation")
    favorite_teacher = models.BooleanField(default=False)
    favorite_student = models.BooleanField(default=False)
    student_first_name = models.CharField(default="unknown")
    student_last_name = models.CharField(default="unknown")
    student_color = models.CharField(default="C5E5DB", max_length=6)

    def save(self, *args, **kwargs):
        # Automatically set student names if they are still the default value
        if self.student_first_name == "unknown":
            self.student_first_name = self.student.user.first_name
        if self.student_last_name == "unknown":
            self.student_last_name = self.student.user.last_name
        super().save(*args, **kwargs)

class Student(models.Model):
    course = models.ManyToManyField(to=Course, through=CourseRegistration, related_name="student")
    school = models.ManyToManyField(to=School, related_name="student")
    teacher = models.ManyToManyField(to=Teacher, through=StudentTeacherRelation, related_name="student")
    user = models.OneToOneField(User, models.CASCADE)

    def __str__(self) -> str:
        return self.user.__str__()

class Lesson(models.Model):
    STATUS_CHOICES = [
        ('PENTE', 'PendingTeacher'),
        ('PENST', 'PendingStudent'),
        ('CON', 'Confirmed'),
        ('COM', 'Completed'),
        ('CAN', 'Canceled'),
        ('MIS', 'Missed'),
    ]

    notes = models.CharField(max_length=300, blank=True)
    booked_datetime = models.DateTimeField()
    registration = models.ForeignKey(to=CourseRegistration, on_delete=models.CASCADE, related_name="lesson")
    code = models.CharField(max_length=12, unique=True)
    status = models.CharField(choices=STATUS_CHOICES, max_length=5, default="PENTE")
    online = models.BooleanField(default=False)
    notified = models.BooleanField(default=False)
    student_event_id = models.CharField(null=True, blank=True)
    teacher_event_id = models.CharField(null=True, blank=True)
    
    def generate_unique_code(self, length=8):
        """Generate a unique random code."""
        characters = string.ascii_letters + string.digits
        code = ''.join(random.choice(characters) for _ in range(length))
        return code
    
    def _generate_unique_code(self, length):
        """Generate a unique code and ensure it's not already in the database."""
        code = self.generate_unique_code(length)
        while Lesson.objects.filter(code=code).exists():
            code = self.generate_unique_code(length)
        return code
    
    def save(self, *args, **kwargs):
        if self.code is None or self.code == "":
            self.code = self._generate_unique_code(12)
        super(Lesson, self).save(*args, **kwargs)

    def generate_title(self, is_teacher):
        duration = self.registration.course.duration
        subject_user = self.registration.student.user if is_teacher else self.registration.teacher.user
        if self.online:
            title = f"{subject_user.first_name} {subject_user.last_name} - {duration} min (Online)"
        else:
            title = f"{subject_user.first_name} {subject_user.last_name} - {duration} min"
        return title

    def generate_description(self, is_teacher):
        """
        Generates a detailed description string for the lesson.

        Args:
            is_teacher (bool): Determines the perspective of the description.
                                True for teacher, False for student.

        Returns:
            str: A formatted description string.
        """
        # Determine the mode of the lesson
        mode = "Online" if self.online else "In-Person"

        # Format the booked datetime
        datetime_formatted = self.booked_datetime.strftime("%Y-%m-%d %H:%M %Z")

        # Handle optional fields gracefully
        notes_display = self.notes if self.notes else "N/A"

        # Determine the subject user based on the perspective
        if is_teacher:
            subject_user = self.registration.student.user
        else:
            subject_user = self.registration.teacher.user

        # Retrieve the full name and email of the subject user
        full_name = f"{subject_user.first_name} {subject_user.last_name}"
        email_display = subject_user.email if subject_user.email else "N/A"

        # Retrieve course information
        course = self.registration.course
        course_name = course.name if course else "N/A"
        course_description = course.description if course else "N/A"

        # Construct the description string
        description = (
            f"Lesson Details:\n\n"
            f"Name: {full_name}\n"
            f"Email: {email_display}\n"
            f"Course: {course_name}\n"
            f"Course Description: {course_description}\n"
            f"Date & Time: {datetime_formatted}\n"
            f"Duration: {self.registration.course.duration} minutes\n"
            f"Mode: {mode}\n"
            f"Notes: {notes_display}\n"
        )

        return description
    
class GuestLesson(models.Model):
    STATUS_CHOICES = [
        ('PEN', 'Pending'),
        ('CON', 'Confirmed'),
        ('COM', 'Completed'),
        ('CAN', 'Canceled'),
        ('MIS', 'Missed'),
    ]

    notes = models.CharField(max_length=300, blank=True)
    name = models.CharField(max_length=300)
    email = models.CharField(max_length=300, blank=True)
    datetime = models.DateTimeField()
    duration = models.IntegerField()
    code = models.CharField(max_length=12, unique=True)
    status = models.CharField(choices=STATUS_CHOICES, max_length=3, default="PEN")
    online = models.BooleanField(default=False)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="guestlesson")
    teacher_event_id = models.CharField(null=True, blank=True)
    notified = models.BooleanField(default=False)
    
    def generate_unique_code(self, length=8):
        characters = string.ascii_letters + string.digits
        code = ''.join(random.choice(characters) for _ in range(length))
        return code
    
    def _generate_unique_code(self, length):
        code = self.generate_unique_code(length)
        while GuestLesson.objects.filter(code=code).exists():
            code = self.generate_unique_code(length)
        return code
    
    def save(self, *args, **kwargs):
        if self.code is None or self.code == "":
            self.code = self._generate_unique_code(12)
        super(GuestLesson, self).save(*args, **kwargs)

    def generate_description(self):
        """
        Generates a detailed description string for the lesson.
        """
        mode = "Online" if self.online else "In-Person"
        datetime_formatted = self.datetime.strftime("%Y-%m-%d %H:%M %Z")

        # Handle optional fields gracefully
        email_display = self.email if self.email else "N/A"
        notes_display = self.notes if self.notes else "N/A"

        description = (
            f"Lesson Details:\n\n"
            f"Name: {self.name}\n"
            f"Email: {email_display}\n"
            f"Date & Time: {datetime_formatted}\n"
            f"Duration: {self.duration} minutes\n"
            f"Mode: {mode}\n"
            f"Notes: {notes_display}\n"
        )

        return description
