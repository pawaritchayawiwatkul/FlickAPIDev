from school.models import School, SchoolSettings
from student.models import CourseRegistration
from django.utils.timezone import now
from datetime import timedelta
from utils.schedule_utils import compute_available_time
from typing import List