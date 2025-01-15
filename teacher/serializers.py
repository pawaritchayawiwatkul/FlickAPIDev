from rest_framework import serializers
from teacher.models import Course, Teacher, TeacherCourses, UnavailableTimeOneTime, UnavailableTimeRegular
from student.models import GuestLesson, StudentTeacherRelation, CourseRegistration, Lesson, Student
from school.models import School
from core.models import User
import datetime
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification
from dateutil.relativedelta import relativedelta

class SchoolSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="course.name", required=False)
    description = serializers.CharField(source="course.description", required=False)
    start = serializers.TimeField(required=False)
    stop = serializers.TimeField(required=False)

    class Meta:
        model = School
        fields = ("name", "description", "start", "stop")

class RegularUnavailableSerializer(serializers.ModelSerializer):
    day = serializers.ChoiceField(choices=UnavailableTimeRegular.DAY_CHOICES)
    start = serializers.TimeField()
    stop = serializers.TimeField()
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = UnavailableTimeRegular
        fields = ("day", "start", "stop", "user_id")

    def create(self, validated_data):
        return UnavailableTimeRegular.objects.get_or_create(**validated_data)
    
    def validate(self, attrs):
        user_id = attrs.pop('user_id')
        try:
            teacher = Teacher.objects.get(user_id=user_id)
            attrs['teacher_id'] = teacher.id
        except Teacher.DoesNotExist:
            raise serializers.ValidationError({
                'user_id': 'Teacher not found'
            })
        if attrs['stop'] < attrs['start']:
            raise serializers.ValidationError({
                'start_n_stop': 'start must be before stop'
            })
        return attrs

class OnetimeUnavailableSerializer(serializers.ModelSerializer):
    date = serializers.DateField()
    start = serializers.TimeField()
    stop = serializers.TimeField()
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = UnavailableTimeOneTime
        fields = ("date", "start", "stop", "user_id")
                  
    def create(self, validated_data):
        return UnavailableTimeOneTime.objects.get_or_create(**validated_data)
    
    def validate(self, attrs):
        user_id = attrs.pop('user_id')
        try:
            teacher = Teacher.objects.get(user_id=user_id)
            attrs['teacher_id'] = teacher.id
        except Teacher.DoesNotExist:
            raise serializers.ValidationError({
                'user_id': 'Teacher not found'
            })
        if attrs['stop'] < attrs['start']:
            raise serializers.ValidationError({
                'start_n_stop': 'start must be before stop'
            })
        return attrs

class TeacherCourseListSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="course.name")
    description = serializers.CharField(source="course.description")
    uuid = serializers.CharField(source="course.uuid")


    class Meta:
        model = TeacherCourses
        fields = ("name", "description", "favorite", "uuid")

class TeacherCourseDetailwithStudentSerializer(serializers.ModelSerializer):
    no_exp = serializers.BooleanField(source="course.no_exp")
    exp_range = serializers.IntegerField(source="course.exp_range")
    duration = serializers.IntegerField(source="course.duration")
    description = serializers.CharField(source="course.description")
    number_of_lessons = serializers.IntegerField(source="course.number_of_lessons")
    students = serializers.SerializerMethodField()

    def get_students(self, obj):
        students = obj.course._prefetched_objects_cache['registration'].values_list('student').distinct()
        return ListStudentSerializer(StudentTeacherRelation.objects.select_related("student__user").filter(student_id__in=students, teacher_id=obj.teacher_id), many=True).data
    
    class Meta:
        model = TeacherCourses
        fields = ("favorite", "no_exp", "exp_range", "duration", "number_of_lessons", "description", "students")

class TeacherCourseDetailSerializer(serializers.ModelSerializer):
    no_exp = serializers.BooleanField(source="course.no_exp")
    exp_range = serializers.IntegerField(source="course.exp_range")
    duration = serializers.IntegerField(source="course.duration")
    description = serializers.CharField(source="course.description")
    number_of_lessons = serializers.IntegerField(source="course.number_of_lessons")

    class Meta:
        model = TeacherCourses
        fields = ("favorite", "no_exp", "exp_range", "duration", "number_of_lessons", "description")


class UnavailableTimeSerializer(serializers.Serializer):
    start = serializers.TimeField()
    stop = serializers.TimeField()
    code = serializers.CharField()

    class Meta:
        fields = ("start", "stop", "code")

class CourseSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=300)
    no_exp = serializers.BooleanField(default=True)
    exp_range = serializers.IntegerField(required=False)
    duration = serializers.IntegerField()
    number_of_lessons = serializers.IntegerField()
    user_id = serializers.IntegerField(write_only=True)

    def create(self, validated_data):
        teacher = validated_data.pop("teacher")
        course = Course.objects.create(**validated_data)
        teacher.course.add(course)
        return course

    def validate(self, attrs):
        no_exp = attrs.get('no_exp')
        exp_range = attrs.get('exp_range')
        if not no_exp and not exp_range:
            raise serializers.ValidationError({
                'exp_range': 'This field is required when no_exp is False.'
            })
        
        user_id = attrs.pop("user_id")
        try: 
            teacher = Teacher.objects.select_related("school").get(user__id=user_id)
            attrs['teacher'] = teacher
            attrs['school_id'] = teacher.school.id
        except Teacher.DoesNotExist:
            raise serializers.ValidationError({
                'user_id': 'User not found'
            })
        return attrs
    
class TeacherStudentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentTeacherRelation
        fields = ("student_color", "student_first_name", "student_last_name")

class StudentSearchSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.first_name")
    uuid = serializers.CharField(source="user.uuid")
    profile_image = serializers.FileField(source="user.profile_image")

    class Meta:
        model = Student
        fields = ("name", "uuid", "profile_image")

class ListStudentSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    phone_number = serializers.CharField(source="student.user.phone_number")
    email = serializers.CharField(source="student.user.email")
    uuid = serializers.CharField(source="student.user.uuid")
    profile_image = serializers.FileField(source="student.user.profile_image")
    color = serializers.CharField(source="student_color")

    class Meta:
        model = StudentTeacherRelation
        fields = ("name", "phone_number", "email", "uuid", "favorite_student", "profile_image", "color")

    def get_name(self, obj:StudentTeacherRelation):
        return f"{obj.student_first_name} {obj.student_last_name}"
    
class ListCourseRegistrationSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="course.name")
    description = serializers.CharField(source="course.description")
    number_of_lessons = serializers.IntegerField(source="course.number_of_lessons")
    class Meta:
        model = CourseRegistration
        fields = ("name", "description", "used_lessons", "number_of_lessons", "teacher_favorite", "uuid", "exp_date")

class ProfileSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)
    is_teacher = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone_number", "email", "uuid", "profile_image", "is_teacher")
    
class SchoolSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    registered_date = serializers.DateField(read_only=True)
    start = serializers.TimeField(required=False)
    stop = serializers.TimeField(required=False)
    # is_teacher = serializers.CharField(source="user.is_teacher", read_only=False)

    class Meta:
        model = Teacher
        fields = ("name", "description", "registered_date", "start", "stop")

class ListLessonDateTimeSerializer(serializers.ModelSerializer):
    duration = serializers.IntegerField(source="registration.course.duration")
    
    class Meta:
        model = Lesson
        fields = ("booked_datetime", "duration", "status", "code", "online")

class LessonSerializer(serializers.ModelSerializer):
    notes = serializers.CharField(max_length=300)
    online = serializers.BooleanField(required=True)
    # booked_datetime = serializers.DateTimeField() # YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].

    class Meta:
        model = Lesson
        fields = ("booked_datetime", "registration", "notes", "online")

    def create(self, validated_data):
        return Lesson.objects.create(**validated_data)

    def validate(self, attrs):
        attrs['status'] = "PENST"
        return attrs

class CourseRegistrationSerializer(serializers.Serializer):
    course_id = serializers.CharField()
    teacher_id = serializers.IntegerField()
    student_id = serializers.CharField()

    def create(self, validated_data):
        regis = CourseRegistration.objects.create(**validated_data)
        student = validated_data['student']
        teacher = validated_data['teacher']
        course = validated_data['course']
        if not student.teacher.filter(id=teacher.id).exists():
            student.teacher.add(teacher)
            student.school.add(teacher.school_id)

        exp_date = ""
        devices = FCMDevice.objects.filter(user=student.user_id)
        devices.send_message(
                message = Message(
                    notification=Notification(
                        title=f"Registration Successful",
                        body=f"The course {course.name} is registered"
                    ),
                ),
            )
        return regis
    
    def validate(self, attrs):
        student_id = attrs.pop("student_id")
        user_id = attrs.pop("teacher_id")
        course_id = attrs.pop("course_id")
        try: 
            student = Student.objects.get(user__uuid=student_id)
            teacher = Teacher.objects.get(user__id=user_id)
            course = Course.objects.get(uuid=course_id)
            attrs['student'] = student
            attrs['teacher'] = teacher
            attrs['course'] = course
        except Student.DoesNotExist:
            raise serializers.ValidationError({
                'student_id': 'Student not found'
            })
        except Teacher.DoesNotExist:
            raise serializers.ValidationError({
                'user_id': 'User not found'
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
    duration = serializers.IntegerField(source="registration.course.duration")
    student_name = serializers.CharField(source="registration.student.user.first_name")
    course_name = serializers.CharField(source="registration.course.name")
    
    class Meta:
        model = Lesson
        fields = ("booked_datetime", "duration", "student_name", "course_name", "code", "status", "online")

class ListGuestLessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestLesson
        fields = ("name", "datetime", "duration", "code", "status", "online", "notes")
