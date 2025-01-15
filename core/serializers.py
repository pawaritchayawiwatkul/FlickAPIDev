from student.models import Student
from teacher.models import Teacher
from school.models import School
from django.db import IntegrityError
from djoser.serializers import UserSerializer as BaseUserSerializer, UserCreateSerializer as BaseUserCreateSerializer
from rest_framework.serializers import ModelSerializer, CharField
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions as django_exceptions
from rest_framework import serializers
from rest_framework.settings import api_settings
from djoser.conf import settings
from django.db import transaction
from rest_framework.utils import html, model_meta, representation
import copy
from rest_framework.fields import SkipField
from rest_framework.relations import Hyperlink, PKOnlyObject  # NOQA # isort:skip

User = get_user_model()
    
ALL_FIELDS = '__all__'

class CreateUserSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    phone_number = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'profile_image']

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'profile_image']  # Fields to be updated

    # Optionally, we can add additional validation or logic if needed
    def validate_phone_number(self, value):
        if len(value) != 10:
            raise serializers.ValidationError("Phone number must be 10 digits.")
        return value
    
class UserCreateSerializer(BaseUserCreateSerializer):
    school_name = serializers.CharField(required=False)
    school_description = serializers.CharField(required=False)
    school_start = serializers.TimeField(required=False)
    school_stop = serializers.TimeField(required=False)
    uuid = serializers.CharField(required=False)
    
    class Meta(BaseUserCreateSerializer.Meta):
        fields = ['password', 'email', 'first_name', 'last_name', 'is_teacher', 'phone_number', "school_name", "uuid", "school_description", "profile_image", "school_start", "school_stop"]
        non_native_fields = ["school_name", "school_description", "school_start", "school_stop"]

    def to_native(self, obj):
        """
        Serialize objects -> primitives.
        """
        ret = self._dict_class()
        ret.fields = {}

        for field_name, field in self.fields.items():
            # --- BEGIN EDIT --- #
            if field_name in self.Meta.non_native_fields:
                continue
            # --- END --- #
            field.initialize(parent=self, field_name=field_name)
            key = self.get_field_key(field_name)
            value = field.field_to_native(obj, field_name)
            ret[key] = value
            ret.fields[key] = field
        return ret

    def create(self, validated_data):
        validated_data.pop("uuid", None)
        school_name = validated_data.pop("school_name", None)
        school_desc = validated_data.pop("school_description", None)
        school_start = validated_data.pop("school_start", None)
        school_stop = validated_data.pop("school_stop", None)
        try:
            user = self.perform_create(validated_data)
        except IntegrityError:
            self.fail("cannot_create_user")
        if user.is_teacher:
            if not school_name or not school_desc:
                user.delete()
                raise serializers.ValidationError(
                    {"school_info": "please provide name and description"}
                )
                # self.fail("please_provide_school_info") 
            if not school_start or not school_stop:
                user.delete()
                raise serializers.ValidationError(
                    {"operating_info": "please provide start and stop"}
                )
                # self.fail("please_provide_schoo            
            school = School.objects.create(
                name=school_name,
                description=school_desc,
                start=school_start,
                stop=school_stop
            )
            Teacher.objects.create(
                user_id=user.id,
                school_id=school.id
            )
        else:
            Student.objects.create(
                user_id=user.id 
            )
        return user

    def validate(self, attrs):
        password = attrs.get("password")
        try:
            validate_password(password)
        except django_exceptions.ValidationError as e:
            serializer_error = serializers.as_serializer_error(e)
            raise serializers.ValidationError(
                {"password": serializer_error[api_settings.NON_FIELD_ERRORS_KEY]}
            )
        return attrs

    def to_representation(self, instance):
        """
        Object instance -> Dict of primitive datatypes.
        """
        ret = {}
        fields = self._readable_fields
        for field in fields:
            if field.field_name in self.Meta.non_native_fields:
                continue
            try:
                attribute = field.get_attribute(instance)
            except SkipField:
                continue
            check_for_none = attribute.pk if isinstance(attribute, PKOnlyObject) else attribute
            if check_for_none is None:
                ret[field.field_name] = None
            else:
                ret[field.field_name] = field.to_representation(attribute)

        return ret

class UserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        fields = ['email', 'full_name', 'uuid']
