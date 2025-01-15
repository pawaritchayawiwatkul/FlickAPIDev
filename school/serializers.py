from rest_framework import serializers
from teacher.models import Teacher
from school.models import Course

class CourseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=300)
    no_exp = serializers.BooleanField(default=True)
    exp_range = serializers.IntegerField(required=False)
    duration = serializers.IntegerField()
    teacher_id = serializers.UUIDField()

    def create(self, validated_data):
        return Course.objects.create(**validated_data)

    def validate(self, attrs):
        no_exp = attrs.get('no_exp')
        exp_range = attrs.get('exp_range')
        if not no_exp and not exp_range:
            raise serializers.ValidationError({
                'exp_range': 'This field is required when no_exp is False.'
            })
        
        user_id = attrs.pop("teacher_id")
        try: 
            teacher = Teacher.objects.get(user__id=user_id)
            attrs['teacher_id'] = teacher.id
        except Teacher.DoesNotExist:
            raise serializers.ValidationError({
                'user_id': 'User not found'
            })
        return attrs
    