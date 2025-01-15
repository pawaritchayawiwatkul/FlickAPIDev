from django.db.models import EmailField, CharField, UUIDField, BooleanField, Model
from django.contrib.auth.models import PermissionsMixin, UserManager, BaseUserManager
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db.models.fields import BooleanField
from django.forms import IntegerField
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            return ValueError(_("Email field is required"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_admin', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_("Superuser must have is_staff=True. "))
        elif extra_fields.get('is_superuser') is not True:
            raise ValueError(_("Superuser must have is_superuser=True. "))
        elif extra_fields.get('is_admin') is not True:
            raise ValueError(_("Superuser must have is_admin=True. "))
        
        return self.create_user(email, password, **extra_fields)
    
def file_generate_upload_path(instance, filename):
	# Both filename and instance.file_name should have the same values
    return f"profile_image/{instance.uuid}"

class User(AbstractBaseUser, PermissionsMixin):
    email = EmailField(unique=True, blank=True)
    first_name = CharField(max_length=255, blank=True)
    last_name = CharField(max_length=255, blank=True)
    phone_number = CharField(max_length=10, blank=True, unique=True)
    password = CharField(max_length=255, blank=True)
    profile_image = models.FileField(
        upload_to=file_generate_upload_path,
        blank=True,
        null=True
    )
    uuid = UUIDField(default=uuid.uuid4, editable=False, unique=True)

    is_teacher = BooleanField(default=True)
    is_admin = BooleanField(default=False)
    is_staff = BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    
    is_active = BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    objects = CustomUserManager()
    google_credentials = models.JSONField(null=True, blank=True)
    google_calendar_id = models.CharField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "phone_number", "profile_image"]

    def get_full_name(self):
        return f"{self.first_name} - {self.last_name}"

    def get_short_name(self):
        return self.first_name
    
    def has_perm(self, perm: str, obj=True) -> bool:
        return self.is_admin
    
    def has_module_perms(self, app_label: str) -> bool:
        return True

    def __str__(self):
        return self.first_name
