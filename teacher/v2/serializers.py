from rest_framework import serializers
from teacher.models import Course, Teacher, UnavailableTimeOneTime, UnavailableTimeRegular
from student.models import StudentTeacherRelation, CourseRegistration, Lesson, Student, Booking
from core.models import User
import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from utils.notification_utils import send_notification
\
class ListCourseSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='name')
    course_price = serializers.FloatField(source='price')
    course_image_url = serializers.FileField(source='image')

    class Meta:
        model = Course
        fields = (
            "uuid", 
            "course_name", 
            "course_price", 
            "course_image_url"
        )

class CourseDetailSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='name', required=False)
    course_description = serializers.CharField(source='description', required=False)
    course_price = serializers.FloatField(source='price', required=False)
    exp_range = serializers.IntegerField(required=False)
    lesson_duration = serializers.IntegerField(source='duration', required=False)
    number_of_lessons = serializers.IntegerField(required=False)
    location = serializers.CharField(source="school.location", read_only=True)

    class Meta:
        model = Course
        fields = (
            "uuid", 
            "course_name", 
            "course_description", 
            "course_price", 
            "image",
            "exp_range", 
            "lesson_duration", 
            "number_of_lessons",
            "location"
        )
    
    def validate_course_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Course price must be a positive number.")
        return value

    def validate_exp_range(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Experience range must be a positive integer.")
        return value

    def update(self, instance, validated_data):
        if 'name' in validated_data:
            instance.name = validated_data['name']
        if 'description' in validated_data:
            instance.description = validated_data['description']
        if 'price' in validated_data:
            instance.price = validated_data['price']
        if 'duration' in validated_data:
            instance.duration = validated_data['duration']
        if 'image' in validated_data:
            instance.image = validated_data['image']

        instance.exp_range = validated_data.get('exp_range', instance.exp_range)
        instance.number_of_lessons = validated_data.get('number_of_lessons', instance.number_of_lessons)

        instance.save()
        return instance
    
class CreateCourseSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=300, required=False)
    no_exp = serializers.BooleanField(default=True)
    exp_range = serializers.IntegerField(required=False)
    duration = serializers.IntegerField()
    number_of_lessons = serializers.IntegerField()
    user_id = serializers.IntegerField(write_only=True)
    is_group = serializers.BooleanField(default=False)
    image = serializers.FileField(required=True)
    price = serializers.FloatField(required=True)

    class Meta:
        model = Course
        fields = (
            'name', 
            'description', 
            'no_exp', 
            'exp_range', 
            'duration', 
            'number_of_lessons', 
            'user_id', 
            'is_group',
            'image',
            'price'
        )

    def create(self, validated_data):
        user_id = validated_data.pop('user_id')
        try:
            teacher = Teacher.objects.select_related("school").get(user__id=user_id)
            validated_data['school_id'] = teacher.school.id
        except Teacher.DoesNotExist:
            raise serializers.ValidationError({
                'user_id': 'User not found'
            })
        course = Course.objects.create(**validated_data)
        return course

    def validate(self, attrs):
        no_exp = attrs.get('no_exp')
        exp_range = attrs.get('exp_range')
        if not no_exp and not exp_range:
            raise serializers.ValidationError({
                'exp_range': 'This field is required when no_exp is False.'
            })
        return attrs

class ListStudentSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="student.user.get_full_name")
    phone_number = serializers.CharField(source="student.user.phone_number")
    email = serializers.CharField(source="student.user.email")
    uuid = serializers.CharField(source="student.user.uuid")
    profile_image = serializers.FileField(source="student.user.profile_image")

    class Meta:
        model = StudentTeacherRelation
        fields = ("name", "phone_number", "email", "uuid", "profile_image")
        
class ProfileSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)
    is_teacher = serializers.BooleanField(read_only=True)
    is_manager = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = ("country_code", "first_name", "last_name", "phone_number", "email", "uuid", "profile_image", "is_teacher", "is_manager")

class ListCourseRegistrationSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source="course.name")
    number_of_lessons = serializers.IntegerField(source="course.number_of_lessons")
    course_image_url = serializers.FileField(source="course.image")
    instructor_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)
    instructor_uuid = serializers.UUIDField(source="teacher.user.uuid", read_only=True)

    class Meta:
        model = CourseRegistration
        fields = ("uuid", "course_name", "lessons_left", "number_of_lessons", "exp_date", "course_image_url", "instructor_name", "instructor_uuid")
        
class SimpleListCourseRegistrationSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source="course.name")
    course_image_url = serializers.FileField(source="course.image")
    duration = serializers.IntegerField(source="course.duration")
    description = serializers.CharField(source="course.description")

    class Meta:
        model = CourseRegistration
        fields = ("uuid", "course_name", "course_image_url", "duration", "description")
        

class CourseRegistrationDetailSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source="course.name")
    course_price = serializers.FloatField(source="course.price")
    course_description = serializers.CharField(source="course.description")
    number_of_lessons = serializers.IntegerField(source="course.number_of_lessons")
    instructor_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)
    lesson_duration = serializers.IntegerField(source="course.duration")
    course_image_url = serializers.FileField(source="course.image")
    location = serializers.CharField(source="course.school.location", read_only=True)

    class Meta:
        model = CourseRegistration
        fields = ( "course_name", "course_description", "course_price", "course_image_url", "number_of_lessons", "lesson_duration", "instructor_name", "lessons_left", "uuid", "exp_date", "location")

class CreateCourseRegistrationSerializer(serializers.Serializer):
    course_id = serializers.CharField()
    teacher_id = serializers.IntegerField()
    student_id = serializers.CharField()
    number_of_lessons = serializers.IntegerField(required=False)

    def create(self, validated_data):
        regis = CourseRegistration.objects.create(payment_status="confirm", **validated_data)
        return regis
    
    def validate(self, attrs):
        student_id = attrs.pop("student_id")
        teacher_id = attrs.pop("teacher_id")
        course_id = attrs.pop("course_id")
        try: 
            student = Student.objects.get(user__uuid=student_id)
            teacher = Teacher.objects.get(user__id=teacher_id)
            course = Course.objects.get(uuid=course_id)
            attrs['student'] = student
            attrs['teacher'] = teacher
            attrs['course'] = course
            attrs['lessons_left'] = attrs.pop('number_of_lessons', course.number_of_lessons)
        except Student.DoesNotExist:
            raise serializers.ValidationError({
                'student_id': 'Student not found'
            })
        except Teacher.DoesNotExist:
            raise serializers.ValidationError({
                'teacher_id': 'User not found'
            })
        except Course.DoesNotExist:
            raise serializers.ValidationError({
                'course_code': 'Course not found'
            })
        attrs['registered_date'] = datetime.date.today()
        if not course.no_exp:
            attrs['exp_date'] = attrs['registered_date'] + relativedelta(months=course.exp_range)
        return attrs

class ListLessonSerializer(serializers.ModelSerializer):
    duration = serializers.IntegerField(source="course.duration")
    course_name = serializers.CharField(source="course.name")
    course_description = serializers.CharField(source="course.description")
    is_group = serializers.BooleanField(source="course.is_group")
    student_name = serializers.SerializerMethodField()
    student_phone_number = serializers.SerializerMethodField()
    student_email = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ("datetime", "duration", "student_name", "student_email", "student_phone_number", "course_name", "course_description", "code", "status", "is_group", "profile_image")

    def get_student_name(self, obj):
        # Assuming `students` is a related_name for the reverse relationship
        first_booking = obj.bookings[:1]
        if first_booking:
            if first_booking[0].student.user:
                return first_booking[0].student.user.first_name
        return None
    
    def get_student_email(self, obj):
        # Assuming `students` is a related_name for the reverse relationship
        first_booking = obj.bookings[:1]
        if first_booking:
            if first_booking[0].student.user:
                return first_booking[0].student.user.email
        return None
    
    def get_profile_image(self, obj):
        # Assuming `students` is a related_name for the reverse relationship
        first_booking = obj.bookings[:1]
        if first_booking:
            if first_booking[0].student.user.profile_image:
                return first_booking[0].student.user.profile_image.url
        return None

    def get_student_phone_number(self, obj):
        # Assuming `students` is a related_name for the reverse relationship
        first_booking = obj.bookings[:1]
        if first_booking:
            if first_booking[0].student.user:
                return first_booking[0].student.user.phone_number
        return None
    
class LessonDetailSerializer(serializers.ModelSerializer):
    duration = serializers.IntegerField(source="course.duration")
    description = serializers.CharField(source="course.description")
    location = serializers.CharField(source="course.school.location")
    course_name = serializers.CharField(source="course.name")
    is_group = serializers.CharField(source="course.is_group")
    students = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ("datetime", "duration", "students", "course_name", "code", "status", "description", "location", "is_group")

    def get_students(self, obj):
        # Assuming `bookings` is a related_name for the reverse relationship
        return [
            {
                "name": booking.student.user.first_name,
                "uuid": booking.student.user.uuid
            }
            for booking in obj.bookings
            if booking.student and booking.student.user
        ]

class CreateLessonSerializer(serializers.ModelSerializer):
    datetime = serializers.DateTimeField()
    student_uuid = serializers.UUIDField(write_only=True, required=True)
    registration_uuid = serializers.UUIDField(write_only=True, required=True)
    teacher_uuid = serializers.UUIDField(write_only=True, required=True)

    class Meta:
        model = Lesson
        fields = [
            "datetime",
            "student_uuid",
            "registration_uuid",
            "teacher_uuid"
        ]

    def validate(self, data):
        student_uuid = data.get("student_uuid")
        registration_uuid = data.get("registration_uuid")
        teacher_uuid = data.get("teacher_uuid")

        errors = {}

        # Validate Student
        try:
            student = Student.objects.get(user__uuid=student_uuid)
        except Student.DoesNotExist:
            errors["student_uuid"] = "Student with this UUID does not exist."

        # Validate Registration
        try:
            registration = CourseRegistration.objects.get(uuid=registration_uuid)
        except CourseRegistration.DoesNotExist:
            errors["registration_uuid"] = "Registration with this UUID does not exist."

        # Validate Teacher
        try:
            teacher = Teacher.objects.get(user__uuid=teacher_uuid)
        except Teacher.DoesNotExist:
            errors["teacher_uuid"] = "Teacher with this UUID does not exist."

        # Raise validation errors if any
        if errors:
            raise serializers.ValidationError(errors)

        # Add validated objects to `data`
        data["student"] = student
        data["registration"] = registration
        data["teacher"] = teacher

        return data

    def create(self, validated_data):
        # Extract validated objects
        student = validated_data.pop("student")
        registration = validated_data.pop("registration")
        teacher = validated_data.pop("teacher")

        try:
            lesson = Lesson.objects.create(
                status="CON",
                course=registration.course,  
                datetime=validated_data["datetime"],
                end_datetime=validated_data["datetime"] + timedelta(minutes=registration.course.duration),
                number_of_client=1,
                teacher=teacher  
            )
        except Exception as e:
            raise serializers.ValidationError({"lesson_creation": str(e)})

        Booking.objects.create(
            lesson=lesson,
            student=student,
            registration=registration,
            user_type="student",
            status="COM"
        )

        send_notification(student.user, "New Booking Alert",
                          f"{teacher.user.first_name} has booked a class with you. Check your schedule for details.")

        return lesson

class ListBookingSerializer(serializers.ModelSerializer):
    duration = serializers.IntegerField(source="lesson.course.duration")
    course_name = serializers.CharField(source="lesson.course.name")
    is_group = serializers.CharField(source="lesson.course.is_group")
    instructor_name = serializers.CharField(source='lesson.teacher.user.get_full_name', read_only=True)
    datetime = serializers.DateTimeField(source="lesson.datetime")

    class Meta:
        model = Booking
        fields = ("datetime", "duration", "course_name", "instructor_name", "code", "status",  "is_group")

class CreateUnavailableTimeOneTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnavailableTimeOneTime
        fields = ['date', 'start', 'stop', 'teacher', 'code']
        read_only_fields = ['code']

class CreateUnavailableTimeRegularSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnavailableTimeRegular
        fields = ['day', 'start', 'stop', 'teacher', 'code']
        read_only_fields = ['code']

class ListUnavailableTimeOneTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnavailableTimeOneTime
        fields = ['date', 'start', 'stop', 'code']

class ListUnavailableTimeRegularSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnavailableTimeRegular
        fields = ['day', 'start', 'stop', 'code']
