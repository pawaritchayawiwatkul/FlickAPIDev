from rest_framework import serializers
from core.models import User

class ProfileSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)
    is_teacher = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone_number", "email", "uuid", "profile_image", "is_teacher")
    
