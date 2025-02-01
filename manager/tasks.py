from celery import shared_task
from celery_singleton import Singleton
from django.utils.timezone import now
from django.db.models import Prefetch
from datetime import timedelta
from school.models import School, SchoolSettings, Course
from teacher.models import Lesson, Teacher
from utils.schedule_utils import compute_available_time
import string
import random

def generate_unique_code(existing_codes, length=8):
    """Generate a unique random code ensuring no duplicates."""
    characters = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choices(characters, k=length))
        if code not in existing_codes:
            existing_codes.add(code)  # Append new code to prevent duplicates
            return code


@shared_task(base=Singleton)
def generate_upcoming_lessons():
    # Prefetch schools along with teachers and all necessary related data
    schools = School.objects.prefetch_related(
        Prefetch('teacher', queryset=Teacher.objects.prefetch_related(
            Prefetch('unavailable_once', to_attr='cached_unavailables'),
            Prefetch('lesson', to_attr='cached_lessons'),
            Prefetch('available_times', to_attr='cached_available_times')
        ), to_attr='cached_teachers')
    ).select_related("settings").all()

    date_today = now().date()
    existing_codes = set(Lesson.objects.values_list('code', flat=True))

    for school in schools:
        # Fetch SchoolSettings (handle if missing)
        try:
            school_settings = school.settings  # One-to-One relation
            days_ahead = school_settings.days_ahead
            interval = school_settings.interval
        except SchoolSettings.DoesNotExist:
            print(f"⚠ Warning: SchoolSettings missing for {school.name}, using defaults.")
            days_ahead = 21  # Default fallback
            interval = 30  # Default fallback

        teachers = school.cached_teachers  # Prefetched teachers

        for teacher in teachers:
            unavailables = teacher.cached_unavailables
            lessons = teacher.cached_lessons
            available_times = teacher.cached_available_times

            for available_time in available_times:
                start = available_time.start
                stop = available_time.stop
                courses = Course.objects.filter(school=school)

                for course in courses:
                    new_lessons = []

                    for day_offset in range(days_ahead):
                        date_time = date_today + timedelta(days=day_offset)

                        available_slots = compute_available_time(
                            unavailables, lessons, date_time, start, stop, course.duration, interval
                        )

                        for slot in available_slots:
                            lesson_code = generate_unique_code(existing_codes, 12)
                            new_lessons.append(
                                Lesson(
                                    code=lesson_code,
                                    datetime=slot['start'],
                                    status='AVA',
                                    course=course,
                                    teacher=teacher
                                )
                            )

                    if new_lessons:
                        Lesson.objects.bulk_create(new_lessons, batch_size=100)