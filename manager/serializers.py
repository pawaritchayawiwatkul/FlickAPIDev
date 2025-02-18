from rest_framework import serializers
from student.models import CourseRegistration
from rest_framework import serializers
from student.models import  CourseRegistration, Student, Booking
from teacher.models import Teacher, Lesson, AvailableTime
from school.models import Course, School
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
from core.models import User  # Add this import

class CourseRegistrationSerializer(serializers.ModelSerializer):
    teacher_uuid = serializers.UUIDField(write_only=True, required=True)
    course_uuid = serializers.UUIDField(write_only=True, required=True)  # Added course_uuid
    student_uuid = serializers.UUIDField(write_only=True, required=True)
    discount = serializers.FloatField()
    payment_slip = serializers.ImageField(required=False)  # Add payment_slip field
    number_of_lessons = serializers.IntegerField(required=False)  # Add number_of_lessons field

    class Meta:
        model = CourseRegistration
        fields = [
            'discount', 
            'teacher_uuid', 
            'student_uuid', 
            'course_uuid',  # Include course_uuid
            'registered_date',
            'exp_date',
            'lessons_left',
            'paid_price',
            'payment_slip',  # Include payment_slip
            'payment_status',
            'number_of_lessons'  # Include number_of_lessons
        ]

    def validate(self, data):
        # Validate teacher existence
        teacher_uuid = data.pop('teacher_uuid')
        student_uuid = data.pop('student_uuid')
        try:
            teacher = Teacher.objects.get(user__uuid=teacher_uuid)
        except Teacher.DoesNotExist:
            raise serializers.ValidationError({"teacher_uuid": "Teacher with this UUID does not exist."})
        try:
            student = Student.objects.get(user__uuid=student_uuid)
        except Student.DoesNotExist:
            return serializers.ValidationError({"student_uuid": "Student with this UUID does not exist."})

        data['teacher'] = teacher
        data['student'] = student

        # Set EXP Date
        data['registered_date'] = date.today()
        # Validate course existence
        course_uuid = data.pop('course_uuid')
        try:
            course = Course.objects.get(uuid=course_uuid)
            data['lessons_left'] = data.pop('number_of_lessons', course.number_of_lessons)
            if not course.no_exp:
                if course.exp_range is not None:
                    data['exp_date'] = data['registered_date'] + relativedelta(months=course.exp_range)

        except Course.DoesNotExist:
            raise serializers.ValidationError({"course_uuid": "Course with this UUID does not exist."})
        data['course'] = course
        if course.price != None:
            discount = data.get('discount')
            if discount > course.price:
                raise serializers.ValidationError({"discount": "Discount cannot be greater than the course price."})
            if discount == None:
                raise serializers.ValidationError({"discount": "Discount is required"})
            else:
                paid_price = data.pop('paid_price', course.price - discount)
                data['paid_price'] = paid_price
        return data

    def create(self, validated_data):
        # Pop fields not part of the CourseRegistration model
        teacher = validated_data.pop('teacher')
        student = validated_data.pop('student')

        if not teacher.student.filter(id=student.id).exists():
            teacher.student.add(student)

        # Create the CourseRegistration instance
        registration = CourseRegistration.objects.create(
            teacher=teacher,
            student=student,
            **validated_data  # Add remaining fields dynamically
        )
        return registration
    
class CourseSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=300, required=False)
    no_exp = serializers.BooleanField(default=True)
    exp_range = serializers.IntegerField(required=False)
    duration = serializers.IntegerField()
    number_of_lessons = serializers.IntegerField()
    is_group = serializers.BooleanField(default=False)
    image = serializers.FileField(required=True)
    price = serializers.FloatField(required=True)
    school_id = serializers.UUIDField(write_only=True)  # Add school field

    class Meta:
        model = Course
        fields = (
            'name', 
            'description', 
            'price',
            'no_exp', 
            'exp_range', 
            'duration', 
            'number_of_lessons', 
            'is_group',
            'image',
            'school_id',
            'uuid'
        )
        read_only_fields = ('uuid',)

    def create(self, validated_data):
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
    
class CourseDetailSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=300, required=False)
    no_exp = serializers.BooleanField(default=True)
    exp_range = serializers.IntegerField(required=False)
    duration = serializers.IntegerField()
    number_of_lessons = serializers.IntegerField()
    image = serializers.FileField(required=True)
    price = serializers.FloatField(required=True)
    created_date = serializers.DateField(read_only=True)  # Make created_date read-only

    class Meta:
        model = Course
        fields = (
            'name', 
            'description', 
            'price',
            'no_exp', 
            'exp_range', 
            'duration', 
            'created_date',
            'number_of_lessons', 
            'image',
            'uuid'
        )
        read_only_fields = ('uuid', 'created_date')  # Ensure created_date is read-only

class SchoolAnalyticsSerializer(serializers.ModelSerializer):
    earnings_amount = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = ['earnings_amount', 'staffs', 'clients', 'weekly_class', 'purchases']

    def get_earnings_amount(self, obj):
        return self.context.get('total_earnings', 0)


class PurchaseSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)
    teacher_uuid = serializers.UUIDField(source='teacher.user.uuid', read_only=True)  # Add teacher_uuid
    course_name = serializers.CharField(source='course.name')
    amount = serializers.SerializerMethodField()

    class Meta:
        model = CourseRegistration
        fields = [
            'uuid', 
            'student_name', 
            'teacher_name', 
            'teacher_uuid',  # Include teacher_uuid
            'registered_date', 
            'course_name',
            'amount', 
            'payment_slip', 
            'payment_status', 
            'lessons_left',
        ]

    def get_amount(self, obj):
        return f"฿{obj.paid_price:.2f}" if obj.paid_price else 0.0

class RegistrationDetailSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    paid_price = serializers.FloatField()
    discount = serializers.FloatField()
    lessons_left = serializers.IntegerField()
    exp_date = serializers.DateField()
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)
    teacher_uuid = serializers.UUIDField(source='teacher.user.uuid', read_only=True)
    payment_slip = serializers.ImageField()

    class Meta:
        model = CourseRegistration
        fields = [
            'uuid',
            'student_name',
            'course_name',
            'paid_price',
            'discount',
            'lessons_left',
            'exp_date',
            'teacher_name',
            'teacher_uuid',
            'payment_slip',
            'payment_status',
        ]
    
class TeacherSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()
    available_times = serializers.JSONField()  # Add available_times field

    class Meta:
        model = Teacher
        fields = ['profile_picture', 'first_name', 'last_name', 'uuid', 'phone_number', 'email', 'available_times']

    def get_profile_picture(self, obj):
        return obj.user.profile_image.url if obj.user.profile_image else ""

class StudentSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['profile_picture', 'first_name', 'last_name', 'uuid', 'phone_number']

    def get_profile_picture(self, obj):
        return obj.user.profile_image.url if obj.user.profile_image else ""

class RegistrationSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name')

    class Meta:
        model = CourseRegistration
        fields = ['registration_uuid', 'course_name', 'registration_date', 'paid_price']

class AvailableTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailableTime
        fields = ['uuid', 'day', 'start', 'stop']

class BookingSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name")

    class Meta:
        model = Booking
        fields = ["student_name", "code",  "check_in", "check_out", "status"]


class LessonSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source="course.name")
    course_uuid = serializers.UUIDField(source="course.uuid")
    teacher_name = serializers.CharField(source="teacher.user.get_full_name", allow_null=True)
    start_time = serializers.DateTimeField(source="datetime")
    end_time = serializers.SerializerMethodField()
    bookings = BookingSerializer(source="prefetched_bookings", many=True)
    
    class Meta:
        model = Lesson
        fields = [
            "code", "start_time", "end_time", "course_name", "course_uuid",
            "teacher_name", "bookings", "status"
        ]

    def get_end_time(self, obj):
        """Calculate the lesson end time based on duration."""
        return obj.datetime + timedelta(minutes=obj.course.duration)

class ProfileSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)
    
    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone_number", "email", "uuid", "profile_image")

class CreateLessonSerializer(serializers.ModelSerializer):
    datetime = serializers.DateTimeField()
    student_uuid = serializers.UUIDField(write_only=True, required=True)
    registration_uuid = serializers.UUIDField(write_only=True, required=True)
    teacher_uuid = serializers.UUIDField(write_only=True, required=True)  # Add teacher_uuid field

    class Meta:
        model = Lesson
        fields = [
            "datetime", 
            "student_uuid", 
            "registration_uuid",
            "teacher_uuid"  # Include teacher_uuid
        ]

    def create(self, validated_data):
        student_uuid = validated_data.pop('student_uuid')
        registration_uuid = validated_data.pop('registration_uuid')
        teacher_uuid = validated_data.pop('teacher_uuid')  # Retrieve teacher_uuid

        try:
            student = Student.objects.get(user__uuid=student_uuid)
        except Student.DoesNotExist:
            raise serializers.ValidationError({"student_uuid": "Student with this UUID does not exist."})

        try:
            registration = CourseRegistration.objects.get(uuid=registration_uuid)
        except CourseRegistration.DoesNotExist:
            raise serializers.ValidationError({"registration_uuid": "Registration with this UUID does not exist."})

        try:
            teacher = Teacher.objects.get(user__uuid=teacher_uuid)
        except Teacher.DoesNotExist:
            raise serializers.ValidationError({"teacher_uuid": "Teacher with this UUID does not exist."})

        try:
            lesson = Lesson.objects.create(
                status='CON', 
                course=registration.course,  # Set course to registration.course
                datetime=validated_data['datetime'],
                end_datetime=validated_data['datetime'] + timedelta(minutes=registration.course.duration),
                number_of_client=1,
                teacher=teacher  # Assign teacher to the lesson
            )
        except Exception as e:
            raise serializers.ValidationError({"lesson_creation": str(e)})
        
        Booking.objects.create(
            lesson=lesson,
            student=student,
            registration=registration,
            user_type='student',
            status='COM'
        )
        return lesson

class EditLessonSerializer(serializers.ModelSerializer):
    datetime = serializers.DateTimeField(required=False)
    student_uuid = serializers.UUIDField(write_only=True, required=False)
    registration_uuid = serializers.UUIDField(write_only=True, required=False)
    teacher_uuid = serializers.UUIDField(write_only=True, required=False)  # Add teacher_uuid field

    class Meta:
        model = Lesson
        fields = [
            "datetime", 
            "student_uuid", 
            "registration_uuid",
            "teacher_uuid"  # Include teacher_uuid
        ]

    def update(self, instance, validated_data):
        student_uuid = validated_data.pop('student_uuid', None)
        registration_uuid = validated_data.pop('registration_uuid', None)
        teacher_uuid = validated_data.pop('teacher_uuid', None)

        if student_uuid:
            try:
                student = Student.objects.get(user__uuid=student_uuid)
            except Student.DoesNotExist:
                raise serializers.ValidationError({"student_uuid": "Student with this UUID does not exist."})
            instance.student = student

        if registration_uuid:
            try:
                registration = CourseRegistration.objects.get(uuid=registration_uuid)
            except CourseRegistration.DoesNotExist:
                raise serializers.ValidationError({"registration_uuid": "Registration with this UUID does not exist."})
            instance.registration = registration

        if teacher_uuid:
            try:
                teacher = Teacher.objects.get(user__uuid=teacher_uuid)
            except Teacher.DoesNotExist:
                raise serializers.ValidationError({"teacher_uuid": "Teacher with this UUID does not exist."})
            instance.teacher = teacher

        instance.datetime = validated_data.get('datetime', instance.datetime)
        instance.save()
        return instance
