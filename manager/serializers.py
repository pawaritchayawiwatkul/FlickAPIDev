from rest_framework import serializers
from student.models import CourseRegistration

from rest_framework import serializers
from student.models import CourseRegistration, Student
from teacher.models import Teacher
from school.models import Course

class CourseRegistrationSerializer(serializers.ModelSerializer):
    teacher_uuid = serializers.UUIDField(write_only=True, required=True)
    course_uuid = serializers.UUIDField(write_only=True, required=True)  # Added course_uuid
    exp_date = serializers.DateField(required=True)
    used_lessons = serializers.IntegerField(required=True)
    discount = serializers.FloatField(required=False)

    class Meta:
        model = CourseRegistration
        fields = [
            'exp_date', 
            'used_lessons', 
            'discount', 
            'student',
            'teacher_uuid', 
            'course_uuid',  # Include course_uuid
        ]

    def validate(self, data):
        # Validate teacher existence
        teacher_uuid = data.pop('teacher_uuid')
        try:
            teacher = Teacher.objects.get(user__uuid=teacher_uuid)
        except Teacher.DoesNotExist:
            raise serializers.ValidationError({"teacher_uuid": "Teacher with this UUID does not exist."})
        data['teacher'] = teacher

        # Validate course existence
        course_uuid = data.pop('course_uuid')
        try:
            course = Course.objects.get(uuid=course_uuid)
        except Course.DoesNotExist:
            raise serializers.ValidationError({"course_uuid": "Course with this UUID does not exist."})
        data['course'] = course
        if course.price != None:
            discount = data.get('discount')
            if discount == None:
                raise serializers.ValidationError({"discount": "Discount is required"})
            else:
                data['paid_price'] = course.price - discount

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
    class Meta:
        model = Course
        fields = [
            'name', 
            'description', 
            'uuid', 
            'no_exp', 
            'exp_range', 
            'duration', 
            'number_of_lessons', 
            'created_date',
            'school',
            'price'
        ]
        read_only_fields = ['uuid']
        extra_kwargs = {
            'school': {'required': True, 'write_only': True},
        }

    def validate(self, data):
        # Ensure the 'exp_range' is a positive integer
        if data.get('exp_range') <= 0:
            raise serializers.ValidationError({"exp_range": "This field must be a positive integer."})
        
        # Validate 'duration' to be a positive integer
        if data.get('duration') <= 0:
            raise serializers.ValidationError({"duration": "This field must be a positive integer."})
        
        # Validate 'number_of_lessons' to be a positive integer
        if data.get('number_of_lessons') <= 0:
            raise serializers.ValidationError({"number_of_lessons": "This field must be a positive integer."})
        
        return data

    def create(self, validated_data):
        # Create the Course instance using validated data
        course = Course.objects.create(
            name=validated_data['name'],
            description=validated_data['description'],
            no_exp=validated_data['no_exp'],
            exp_range=validated_data['exp_range'],
            duration=validated_data['duration'],
            number_of_lessons=validated_data['number_of_lessons'],
            school=validated_data['school'],
            price=validated_data['price']
        )
        return course