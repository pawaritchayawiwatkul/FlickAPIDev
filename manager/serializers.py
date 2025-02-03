from rest_framework import serializers
from student.models import CourseRegistration
from rest_framework import serializers
from student.models import  CourseRegistration, Student
from teacher.models import Teacher, Lesson, AvailableTime
from school.models import Course, School
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta

class CourseRegistrationSerializer(serializers.ModelSerializer):
    teacher_uuid = serializers.UUIDField(write_only=True, required=True)
    course_uuid = serializers.UUIDField(write_only=True, required=True)  # Added course_uuid
    discount = serializers.FloatField()
    payment_slip = serializers.ImageField(required=False)  # Add payment_slip field
    number_of_lessons = serializers.IntegerField(required=False)  # Add number_of_lessons field

    class Meta:
        model = CourseRegistration
        fields = [
            'discount', 
            'student',
            'teacher_uuid', 
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
        try:
            teacher = Teacher.objects.get(user__uuid=teacher_uuid)
        except Teacher.DoesNotExist:
            raise serializers.ValidationError({"teacher_uuid": "Teacher with this UUID does not exist."})
        data['teacher'] = teacher

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
        course = validated_data.pop('course')

        # Create the CourseRegistration instance
        registration = CourseRegistration.objects.create(
            teacher=teacher,
            course=course,
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
    
    class Meta:
        model = Course
        fields = (
            'name', 
            'description', 
            'no_exp', 
            'exp_range', 
            'duration', 
            'number_of_lessons', 
            'is_group',
            'image',
            'school'
        )

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
    
# class CourseSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Course
#         fields = [
#             'name', 
#             'description', 
#             'uuid', 
#             'no_exp', 
#             'exp_range', 
#             'duration', 
#             'number_of_lessons', 
#             'created_date',
#             'school',
#             'price',
#             'is_group',
#             'group_size'
#         ]
#         read_only_fields = ['uuid']
#         extra_kwargs = {
#             'school': {'required': True, 'write_only': True},
#         }

#     def validate(self, data):
#         # Ensure the 'exp_range' is a positive integer
#         if data.get('exp_range') <= 0:
#             raise serializers.ValidationError({"exp_range": "This field must be a positive integer."})
        
#         # Validate 'duration' to be a positive integer
#         if data.get('duration') <= 0:
#             raise serializers.ValidationError({"duration": "This field must be a positive integer."})
        
#         # Validate 'number_of_lessons' to be a positive integer
#         if data.get('number_of_lessons') <= 0:
#             raise serializers.ValidationError({"number_of_lessons": "This field must be a positive integer."})
        
#         return data

#     def create(self, validated_data):
#         # Create the Course instance using validated data
#         course = Course.objects.create(
#             name=validated_data['name'],
#             description=validated_data['description'],
#             no_exp=validated_data['no_exp'],
#             exp_range=validated_data['exp_range'],
#             duration=validated_data['duration'],
#             number_of_lessons=validated_data['number_of_lessons'],
#             school=validated_data['school'],
#             price=validated_data['price'],
#             is_group=validated_data.get('is_group', False),
#             group_size=validated_data.get('group_size', None) if validated_data.get('is_group', False) else None
#         )
#         return course

class SchoolAnalyticsSerializer(serializers.ModelSerializer):
    earnings_amount = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = ['earnings_amount', 'staffs', 'clients', 'weekly_class', 'purchases']

    def get_earnings_amount(self, obj):
        return self.context.get('total_earnings', 0)

class LessonSerializer(serializers.ModelSerializer):
    start_time = serializers.DateTimeField(source='booked_datetime')
    end_time = serializers.SerializerMethodField()
    course_name = serializers.CharField(source='registration.course.name')
    course_uuid = serializers.UUIDField(source='registration.course.uuid')
    student_first_name = serializers.CharField(source='registration.student.user.first_name')
    student_last_name = serializers.CharField(source='registration.student.user.last_name')
    student_uuid = serializers.UUIDField(source='registration.student.user.uuid')
    teacher_first_name = serializers.CharField(source='registration.teacher.user.first_name')
    teacher_last_name = serializers.CharField(source='registration.teacher.user.last_name')
    teacher_uuid = serializers.UUIDField(source='registration.teacher.user.uuid')

    class Meta:
        model = Lesson
        fields = ['code', 'start_time', 'end_time', 'course_name', 'course_uuid', 'student_first_name', 'student_last_name', 'student_uuid', 'teacher_first_name', 'teacher_last_name', 'teacher_uuid']

    def get_end_time(self, obj):
        return obj.booked_datetime + timedelta(minutes=obj.registration.course.duration)


class PurchaseSerializer(serializers.ModelSerializer):
    student_first_name = serializers.CharField(source='student.user.first_name')
    student_last_name = serializers.CharField(source='student.user.last_name')
    student_uuid = serializers.UUIDField(source='student.user.uuid')
    course_name = serializers.CharField(source='course.name')
    course_uuid = serializers.UUIDField(source='course.uuid')
    amount = serializers.SerializerMethodField()

    class Meta:
        model = CourseRegistration
        fields = ['uuid', 'student_first_name', 'student_last_name', 'student_uuid', 'registered_date', 'course_name', 'course_uuid', 'amount', 'payment_slip', 'payment_status', 'lessons_left']

    def get_amount(self, obj):
        return f"${obj.paid_price:.2f}" if obj.paid_price else 0.0


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