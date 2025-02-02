from celery import shared_task
from celery_singleton import Singleton
from django.db.models import Prefetch
from school.models import School, Course, SchoolSettings
from teacher.models import Lesson, Teacher
from django.utils.timezone import now
from datetime import timedelta, datetime
from utils.schedule_utils import compute_available_time, generate_unique_code

def generate_upcoming_private(schools):
    new_lessons = []
    date_today = now().date()
    existing_codes = set(Lesson.objects.values_list('code', flat=True))
    for school in schools:
        # Fetch SchoolSettings (handle if missing)
        try:
            school_settings = school.settings  # One-to-One relation
            days_ahead = school_settings.days_ahead
            gap = school_settings.interval
        except SchoolSettings.DoesNotExist:
            days_ahead = 21  # Default fallback
            gap = 30  # Default fallback

        teachers = school.cached_teachers  # Prefetched teachers

        for teacher in teachers:
            unavailables = teacher.cached_unavailables
            lessons = teacher.cached_lessons
            available_times = teacher.cached_available_times  # Use cached available times
            courses = teacher.cached_courses  # Prefetched courses
            for available_time in available_times:
                start = available_time.start
                stop = available_time.stop
                day_of_week = int(available_time.day)          
                for course in courses:
                    for day_offset in range(days_ahead):
                        date_time = date_today + timedelta(days=day_offset)
                        if date_time.isoweekday() == day_of_week:
                            interval = course.duration + gap
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
    return new_lessons

@shared_task(base=Singleton)
def generate_upcoming_lessons():
    # Prefetch schools along with teachers, courses, and all necessary related data
    schools = School.objects.prefetch_related(
        Prefetch('teacher', 
                queryset=Teacher.objects.prefetch_related(
                Prefetch('unavailable_once', to_attr='cached_unavailables'),
                Prefetch('lesson', to_attr='cached_lessons'),
                Prefetch('course',
                    queryset=Course.objects.filter(is_group=False), to_attr='cached_courses'),
                Prefetch('available_time', to_attr='cached_available_times'),  # Prefetch available times
            ), to_attr='cached_teachers'),
        ).select_related("settings").all()

    new_lessons = generate_upcoming_private(schools)

    if new_lessons:
        Lesson.objects.bulk_create(new_lessons, batch_size=100)