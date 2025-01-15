from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from pytz import timezone as ptimezone

utc_timezone = ptimezone('UTC')

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'internal.settings')

app = Celery('internal')

# Using a string here means the worker doesn't have to serialize
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodiscover tasks in installed apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
