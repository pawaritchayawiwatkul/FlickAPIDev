from pathlib import Path
from datetime import timedelta
import os
from storages.backends.s3boto3 import S3Boto3Storage
from firebase_admin import initialize_app, credentials
from google.auth import load_credentials_from_file
import os
from dotenv import load_dotenv 
from django.utils.timezone import activate
from celery.schedules import crontab
import os 

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

load_dotenv() 


# DJANGO SETUP
DEBUG = True if os.getenv("DEBUGING") == "True" else False
DEVELOPING = True if os.getenv("DEVELOPING") == "True" else False

BASE_DIR = Path(__file__).resolve().parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
FERNET_KEY =  os.getenv("FERNET_SECRET_KEY")
ALLOWED_HOSTS = ["*"]
APPEND_SLASH = True 

TIME_ZONE = 'UTC'  # Set this to your desired timezone
USE_TZ = True
activate(TIME_ZONE)

CORS_ORIGIN_ALLOW_ALL = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_celery_beat',
    'rest_framework',
    'djoser',
    'fcm_django',
    'storages',

    'googlecalendar',
    'teacher',
    'student',
    'school',
    'core',
    'manager'
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBUG:
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

ROOT_URLCONF = 'internal.urls'

# Template Integration
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR.parent, 'templates'),  # Add this line to set your template root
        ],
        'APP_DIRS': True,
                'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    }
]
WSGI_APPLICATION = 'internal.wsgi.application'


# Database
if DEBUG:
    DATABASES = {
        'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': 'Pluem9988!',
        'HOST': 'localhost',
        'PORT': '5432',
        }
    }
elif DEVELOPING:
    DATABASES = {
        'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('DB_DEV_NAME'),
        'USER': os.getenv('DB_DEV_USER'),
        'PASSWORD': os.getenv('DB_DEV_PASSWORD'),
        'HOST': os.getenv('DB_DEV_HOST'),
        'PORT': os.getenv('DB_DEV_PORT'),
        }
    }    
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST': os.getenv('DB_HOST'),
            'PORT': os.getenv('DB_PORT'),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ]
}

"""
=====================================
DJOSER
=====================================
"""
DJOSER = {
    "LOGIN_FIELD": "email",
    'PASSWORD_RESET_CONFIRM_URL': 'auth/password/reset/confirm/{uid}/{token}/',   
    'SERIALIZERS' : {
        'user_create': 'core.serializers.UserCreateSerializer',
        "user": "djoser.serializers.UserSerializer",
        "current_user": 'core.serializers.UserSerializer',
        "user_delete": "djoser.serializers.UserSerializer",    
        },
    'EMAIL': {
        'password_reset': 'core.email.PasswordResetEmailTemplate'
    },
    # 'ACTIVATION_URL': 'auth/users/activate_request/{uid}/{token}',
    # 'SEND_ACTIVATION_EMAIL': True,
    # 'SEND_CONFIRMATION_EMAIL':True,
}

SEND_ACTIVATION_EMAIL = True

SIMPLE_JWT = {
    'AUTH_HEADER_TYPES': ('JWT',),
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=10),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=365*100),
}

AUTH_USER_MODEL = 'core.User'

"""
=====================================
Email Integration
=====================================
"""

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = os.getenv("EMAIL_PORT")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_USE_SSL = True

DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: True,
}



# STORAGE 
class MediaStorage(S3Boto3Storage):
    location = 'media'
    file_overwrite = True
    
if DEBUG == False:
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")

    AWS_S3_REGION_NAME = 'ap-southeast-2'  # e.g., us-east-1
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_FILE_OVERWRITE = True

    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_LOCATION = 'static'
else:
    STATIC_ROOT = os.path.join(BASE_DIR.parent, 'static')

STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/' if DEBUG == False else '/static/'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/' if DEBUG == False else '/media/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR.parent, 'staticfiles/'),
]


"""
=====================================
   Notification System ( Firebase )
=====================================
"""

# Notification System ( Firebase )
class CustomFirebaseCredentials(credentials.ApplicationDefault):
    def __init__(self, account_file_path: str):
        super().__init__()
        self._account_file_path = account_file_path

    def _load_credential(self):
        if not self._g_credential:
            self._g_credential, self._project_id = load_credentials_from_file(self._account_file_path,
                                                                              scopes=credentials._scopes)

custom_credentials = CustomFirebaseCredentials(os.getenv("FIREBASE_JSON_PATH"))
FIREBASE_MESSAGING_APP = initialize_app(custom_credentials, name='messaging')

FCM_DJANGO_SETTINGS = {
    "DEFAULT_FIREBASE_APP": FIREBASE_MESSAGING_APP,
     # default: _('FCM Django')
    "APP_VERBOSE_NAME": "Timeable",
    "ONE_DEVICE_PER_USER": False,
    "DELETE_INACTIVE_DEVICES": False,
}

# Calendar System
GOOGLE_CLIENT_SECRET_FILE = os.getenv("GOOGLE_CLIENT_KEY")
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar",     
    "https://www.googleapis.com/auth/calendar.events",
    ]


# CELERY
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_BEAT_MAX_LOOP_INTERVAL = 1800.0

from celery.schedules import schedule


CELERY_BEAT_SCHEDULE = {
    'send-lesson-notification-every-15-minutes': {
        'task': 'teacher.tasks.send_lesson_notification',
        'schedule': crontab(minute='*/15'),  # Executes every 15 minutes
        'args': (),
    },
    'send-guest-notification-every-15-minutes': {
        'task': 'teacher.tasks.send_guest_lesson_notification',
        'schedule': crontab(minute='*/15'),  # Executes every 15 minutes
        'args': (),
    },
}

DEBUG = True