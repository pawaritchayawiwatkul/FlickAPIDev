from django.db import models
from school.models import Course, School
from core.models import User
from teacher.models import Teacher, Lesson
from django.utils.timezone import make_aware, get_current_timezone
from uuid import uuid4
import random
import string

# Create your models here.

def file_generate_upload_path(instance, filename):
	# Both filename and instance.file_name should have the same values
    return f"paymentslips/{instance.uuid}"

class CourseRegistration(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('confirm', 'Confirm'),
        ('waiting', 'Waiting'),
        ('denied', 'Denied'),
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, unique=True)

    registered_date = models.DateField(auto_now_add=True)
    exp_date = models.DateField(null=True)
    finised_date = models.DateField(null=True, blank=True)

    lessons_left = models.IntegerField(default=0)

    student_favorite = models.BooleanField(default=False)
    teacher_favorite = models.BooleanField(default=False)

    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, related_name="registration", null=True, blank=True)
    course = models.ForeignKey(to=Course, on_delete=models.CASCADE, related_name="registration")
    student = models.ForeignKey(to="Student", on_delete=models.CASCADE, related_name="registration")
    
    paid_price = models.FloatField(null=True)
    discount = models.FloatField(null=True)
    payment_slip = models.FileField(
        upload_to=file_generate_upload_path,
        blank=True,
        null=True
    )    
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='waiting')

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

class Guest(models.Model):
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
    notified = models.BooleanField(default=False)
    
    def generate_unique_code(self, length=8):
        characters = string.ascii_letters + string.digits
        code = ''.join(random.choice(characters) for _ in range(length))
        return code
    
    def _generate_unique_code(self, length):
        code = self.generate_unique_code(length)
        while Guest.objects.filter(code=code).exists():
            code = self.generate_unique_code(length)
        return code
    
    def save(self, *args, **kwargs):
        if self.code is None or self.code == "":
            self.code = self._generate_unique_code(12)
        super(Guest, self).save(*args, **kwargs)

class Booking(models.Model):
    USER_TYPE_CHOICES = [
        ('student', 'Student'),
        ('guest', 'Guest'),
    ]

    STATUS_CHOICES = [
        ('COM', 'Completed'),
        ('CAN', 'Canceled'),
    ]

    code = models.CharField(max_length=12, unique=True)

    lesson = models.ForeignKey(to=Lesson, on_delete=models.CASCADE, related_name="booking")
    registration = models.ForeignKey(
        to=CourseRegistration, 
        on_delete=models.CASCADE, 
        related_name="booking", 
        null=True, 
        blank=True  # Allow null for guest bookings
    )
    student = models.ForeignKey(
        to=Student, 
        on_delete=models.CASCADE, 
        related_name="booking", 
        null=True, 
        blank=True  # Allow null for guest bookings
    )
    guest = models.ForeignKey(
        to=Guest, 
        on_delete=models.CASCADE, 
        related_name="booking", 
        null=True, 
        blank=True  # Allow null for student bookings
    )
    user_type = models.CharField(
        max_length=10, 
        choices=USER_TYPE_CHOICES, 
        default='student'
    )
    booked_datetime = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='COM'
    )  # Restricted to only completed and canceled

    def __str__(self):
        if self.user_type == 'student' and self.student:
            return f"Student Booking: {self.student} - Status: {self.status}"
        elif self.user_type == 'guest' and self.guest:
            return f"Guest Booking: {self.guest} - Status: {self.status}"
        return "Unknown Booking"

    def generate_unique_code(self, length=8):
        characters = string.ascii_letters + string.digits
        code = ''.join(random.choice(characters) for _ in range(length))
        return code
    
    def _generate_unique_code(self, length):
        code = self.generate_unique_code(length)
        while Booking.objects.filter(code=code).exists():
            code = self.generate_unique_code(length)
        return code
    
    def save(self, *args, **kwargs):
        if self.code is None or self.code == "":
            self.code = self._generate_unique_code(12)
        super(Booking, self).save(*args, **kwargs)
