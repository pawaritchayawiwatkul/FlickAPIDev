from django.apps import AppConfig
from django.db import models


class AdminManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'manager'