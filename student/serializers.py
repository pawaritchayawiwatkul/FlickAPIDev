from rest_framework import serializers
from student.models import Lesson, GuestLesson, CourseRegistration, Student, StudentTeacherRelation
from teacher.models import Teacher
from school.models import Course
from core.models import User

class GuestLessonSerializer(serializers.ModelSerializer):
    notes = serializers.CharField(max_length=300)
    online = serializers.BooleanField(required=True)

    class Meta:
        model = GuestLesson
        fields = ("notes", "name", "datetime", "duration", "online", "email")

    def validate(self, attrs):
        attrs['status'] = "PEN"
        return attrs
    
class ListTeacherSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="teacher.user.first_name")
    uuid = serializers.CharField(source="teacher.user.uuid")
    email = serializers.CharField(source="teacher.user.email")
    phone_number = serializers.CharField(source="teacher.user.phone_number")
    school_name = serializers.CharField(source="teacher.school.name")
    profile_image = serializers.FileField(source="teacher.user.profile_image")

    class Meta:
        model = StudentTeacherRelation
        fields = ("name", "school_name", "email", "phone_number", "uuid", "favorite_teacher", "profile_image")

class ListCourseRegistrationSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="course.name")
    description = serializers.CharField(source="course.description")
    number_of_lessons = serializers.IntegerField(source="course.number_of_lessons")
    class Meta:
        model = CourseRegistration
        fields = ("name", "description", "used_lessons", "number_of_lessons", "student_favorite", "uuid", "exp_date")

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
    course_id = serializers.CharField()
    teacher_id = serializers.CharField()
    student_id = serializers.IntegerField()

    def create(self, validated_data):
        regis = CourseRegistration.objects.create(**validated_data)
        student = validated_data['student']
        teacher = validated_data['teacher']
        if not student.teacher.filter(id=teacher.id).exists():
            student.teacher.add(teacher)
            student.school.add(teacher.school_id)
        return regis
    
    def validate(self, attrs):
        user_id = attrs.pop("student_id")
        teacher_id = attrs.pop("teacher_id")
        course_id = attrs.pop("course_id")
        try: 
            student = Student.objects.get(user__id=user_id)
            teacher = Teacher.objects.get(user__uuid=teacher_id)
            course = Course.objects.get(uuid=course_id)
            attrs['student'] = student
            attrs['teacher'] = teacher
            attrs['course_id'] = course.id
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
        return attrs

class LessonSerializer(serializers.ModelSerializer):
    notes = serializers.CharField(max_length=300)
    online = serializers.BooleanField(required=True)

    class Meta:
        model = Lesson
        fields = ("booked_datetime", "registration", "notes", "online")

    def create(self, validated_data):
        return Lesson.objects.create(**validated_data)

    def validate(self, attrs):
        attrs['status'] = "PENTE"
        return attrs

class ProfileSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)
    is_teacher = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone_number", "email", "uuid", "profile_image", "is_teacher")
    
class UnavailableTimeSerializer(serializers.Serializer):
    start = serializers.TimeField()
    stop = serializers.TimeField()

    class Meta:
        fields = ("start", "stop")
