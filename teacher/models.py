from django.db import models
from core.models import User
from school.models import School, Course
import random
import string

# Create your models here.

class TeacherCourses(models.Model):
    teacher = models.ForeignKey("Teacher", on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    favorite = models.BooleanField(default=False)
    
class Teacher(models.Model):
    user = models.OneToOneField(User, models.CASCADE)
    course = models.ManyToManyField(Course, through=TeacherCourses, related_name="teachers")
    school = models.ForeignKey(School, models.CASCADE, related_name="teacher")

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