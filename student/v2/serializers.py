from rest_framework import serializers
from student.models import CourseRegistration, Student, StudentTeacherRelation, Booking
from teacher.models import Teacher, Lesson
from school.models import Course
from core.models import User
from datetime import timedelta
from django.utils.timezone import now
    
class ListTeacherSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="teacher.user.first_name")
    last_name = serializers.CharField(source="teacher.user.last_name")
    uuid = serializers.CharField(source="teacher.user.uuid")
    email = serializers.CharField(source="teacher.user.email")
    phone_number = serializers.CharField(source="teacher.user.phone_number")
    profile_image = serializers.FileField(source="teacher.user.profile_image")

    class Meta:
        model = StudentTeacherRelation
        fields = ("first_name", "last_name",  "email", "phone_number", "uuid", "profile_image")

class ListCourseRegistrationSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source="course.name")
    number_of_lessons = serializers.IntegerField(source="course.number_of_lessons")
    course_image_url = serializers.FileField(source="course.image")
    instructor_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)

    class Meta:
        model = CourseRegistration
        fields = ("uuid", "course_name", "lessons_left", "number_of_lessons", "exp_date", "course_image_url", "instructor_name")

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
        fields = ("lessons_left", "uuid", "exp_date", "course_name", "course_description", "course_price", "course_image_url", "number_of_lessons", "lesson_duration", "instructor_name", "location")

class ListLessonDateTimeSerializer(serializers.ModelSerializer):
    duration = serializers.IntegerField(source="registration.course.duration")
    
    class Meta:
        model = Lesson
        fields = ("booked_datetime", "duration", "status", "code", "online")

class ListLessonSerializer(serializers.ModelSerializer):
    duration = serializers.IntegerField(source="registration.course.duration")
    teacher_name = serializers.CharField(source="registration.teacher.user.first_name")
    course_name = serializers.CharField(source="registration.course.name")
    
    class Meta:
        model = Lesson
        fields = ("booked_datetime", "duration", "teacher_name", "course_name", "status", "code", "online")

class CourseRegistrationSerializer(serializers.Serializer):
    course_uuid = serializers.CharField()
    student_id = serializers.IntegerField()
    payment_slip = serializers.FileField()
    
    def create(self, validated_data):
        course = validated_data.get('course')
        if not course.no_exp:
            exp_range = course.exp_range
            validated_data['exp_date'] = now().date() + timedelta(days=exp_range * 30)
        regis = CourseRegistration.objects.create(**validated_data)
        return regis
    
    def validate(self, attrs):
        course_id = attrs.pop("course_uuid")
        try: 
            course = Course.objects.get(uuid=course_id)
            attrs['course_id'] = course.id
            attrs['lessons_left'] = course.number_of_lessons
            attrs['course'] = course  # Add course to attrs for use in create method
        except Student.DoesNotExist:
            raise serializers.ValidationError({
                'user_id': 'User not found'
            })
        except Teacher.DoesNotExist:
            raise serializers.ValidationError({
                'teacher_code': 'Teacher not found'
            })
        except Course.DoesNotExist:
            raise serializers.ValidationError({
                'course_code': 'Course not found'
            })
        
        payment_slip = attrs.get('payment_slip')
        if payment_slip:
            if not payment_slip.name.endswith(('.png', '.jpeg', '.jpg')):
                raise serializers.ValidationError("Only PNG and JPEG files are allowed for the payment slip.")
        
        return attrs

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
            "course_image_url", 
        )

class CourseDetailSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='name')
    course_description = serializers.CharField(source='description')
    course_price = serializers.FloatField(source='price')
    exp_range = serializers.IntegerField()
    lesson_duration = serializers.IntegerField(source='duration')
    number_of_lessons = serializers.IntegerField()
    course_image_url = serializers.FileField(source='image')
    location = serializers.CharField(source="school.location", read_only=True)

    class Meta:
        model = Course
        fields = (
            "uuid", 
            "course_name", 
            "course_description", 
            "course_price", 
            "course_image_url",
            "exp_range", 
            "lesson_duration", 
            "number_of_lessons",
            "location"
        )

class ListLessonCourseSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_description = serializers.CharField(source='course.description', read_only=True)
    course_uuid = serializers.UUIDField(source='course.uuid', read_only=True)
    instructor_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)
    instructor_phone_number = serializers.CharField(source='teacher.user.phone_number', read_only=True)
    instructor_email = serializers.CharField(source='teacher.user.email', read_only=True)
    instructor_uuid = serializers.UUIDField(source='teacher.user.uuid', read_only=True)
    lesson_duration = serializers.IntegerField(source='course.duration', read_only=True)
    location = serializers.CharField(source="course.school.location", read_only=True)
    spots_left = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            'code',
            'course_name',
            'course_description',
            'course_uuid',
            'number_of_client',
            'instructor_name',
            'instructor_phone_number',
            'instructor_email',
            'instructor_uuid',
            'lesson_duration',
            'datetime',
            'location',
            'spots_left'
        ]

    def get_spots_left(self, obj:Lesson):
        """Calculate remaining spots for group courses."""
        if obj.course.is_group:
            return max(obj.course.group_size - obj.number_of_client, 0)
        return None

    def to_representation(self, instance):
        """Customize representation to handle null teacher."""
        representation = super().to_representation(instance)

        # If no teacher is assigned, set instructor fields to null
        if instance.teacher is None:
            representation['instructor_name'] = None
            representation['instructor_phone_number'] = None
            representation['instructor_email'] = None

        return representation
    
class ListLessonPrivateSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_description = serializers.CharField(source='course.description', read_only=True)
    course_uuid = serializers.UUIDField(source='course.uuid', read_only=True)
    instructor_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)
    instructor_phone_number = serializers.CharField(source='teacher.user.phone_number', read_only=True)
    instructor_email = serializers.CharField(source='teacher.user.email', read_only=True)
    instructor_uuid = serializers.UUIDField(source='teacher.user.uuid', read_only=True)
    lesson_duration = serializers.IntegerField(source='course.duration', read_only=True)
    location = serializers.CharField(source="course.school.location", read_only=True)

    class Meta:
        model = Lesson
        fields = [
            'code',
            'course_name',
            'course_description',
            'course_uuid',
            'instructor_name',
            'instructor_phone_number',
            'instructor_email',
            'instructor_uuid',
            'lesson_duration',
            'datetime',
            'location',
        ]

    def to_representation(self, instance):
        """Customize representation to handle null teacher."""
        representation = super().to_representation(instance)

        # If no teacher is assigned, set instructor fields to null
        if instance.teacher is None:
            representation['instructor_name'] = None
            representation['instructor_phone_number'] = None
            representation['instructor_email'] = None

        return representation
    
class ListBookingSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='lesson.course.name', read_only=True)
    instructor_name = serializers.CharField(source='lesson.teacher.user.get_full_name', read_only=True)
    lesson_datetime = serializers.DateTimeField(source='lesson.datetime', read_only=True)
    lesson_duration = serializers.IntegerField(source='lesson.course.duration', read_only=True)
    lesson_status = serializers.CharField(source='lesson.status', read_only=True)
    is_group = serializers.BooleanField(source='lesson.course.is_group', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'code',
            'course_name',
            'instructor_name',
            'lesson_datetime',
            'lesson_duration',
            'lesson_status',
            'is_group'
        ]

class BookingDetailSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='lesson.course.name', read_only=True)
    course_description = serializers.CharField(source='lesson.course.description', read_only=True)
    instructor_image_url = serializers.FileField(source="lesson.teacher.user.profile_image")
    instructor_name = serializers.CharField(source='lesson.teacher.user.get_full_name', read_only=True)
    instructor_phone_number = serializers.CharField(source='lesson.teacher.user.phone_number', read_only=True)
    instructor_email = serializers.CharField(source='lesson.teacher.user.email', read_only=True)
    lesson_datetime = serializers.DateTimeField(source='lesson.datetime', read_only=True)
    lesson_duration = serializers.IntegerField(source='lesson.course.duration', read_only=True)
    lesson_status = serializers.CharField(source='lesson.status', read_only=True)
    location = serializers.CharField(source="lesson.course.school.location", read_only=True)
    is_group = serializers.BooleanField(source='lesson.course.is_group', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'code',
            'course_name',
            'course_description',
            'instructor_image_url',
            'instructor_name',
            'instructor_phone_number',
            'instructor_email',
            'lesson_datetime',
            'lesson_duration',
            'lesson_status',
            'location',
            'is_group'
        ]

class CreateBookingSerializer(serializers.ModelSerializer):
    lesson_id = serializers.IntegerField(write_only=True)
    registration_id = serializers.IntegerField(write_only=True)
    student_id = serializers.IntegerField(write_only=True, required=False)
    guest_id = serializers.IntegerField(write_only=True, required=False)
    user_type = serializers.ChoiceField(choices=[('student', 'Student'), ('guest', 'Guest')], required=True)

    class Meta:
        model = Booking
        fields = [
            'lesson_id',
            'student_id',
            'guest_id',
            'registration_id',
            'user_type',
        ]

    def validate(self, attrs):
        """
        Validate that either student_id or guest_id is provided based on user_type.
        """
        user_type = attrs.get('user_type')
        student = attrs.get('student_id')
        guest = attrs.get('guest')

        if user_type == 'student' and not student:
            raise serializers.ValidationError("A student must be provided for a student booking.")
        if user_type == 'guest' and not guest:
            raise serializers.ValidationError("A guest must be provided for a guest booking.")
        return attrs

    def create(self, validated_data):
        """
        Create a new Booking instance with the provided data.
        """
        lesson = validated_data.get('lesson')
        student = validated_data.get('student_id', None)
        registration = validated_data.get('registration_id', None)
        guest = validated_data.get('guest', None)
        user_type = validated_data.get('user_type')

        # Create and return the Booking instance
        return Booking.objects.create(
            lesson=lesson,
            student_id=student,
            guest=guest,
            registration_id=registration,
            user_type=user_type,
        )