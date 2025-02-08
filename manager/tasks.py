from celery import shared_task
from celery_singleton import Singleton
from django.db.models import Prefetch
from school.models import School, Course, SchoolSettings
from teacher.models import Lesson, Teacher
from student.models import CourseRegistration
from django.utils.timezone import now
from datetime import timedelta, datetime
from utils.schedule_utils import compute_available_time, generate_unique_code
from typing import List

def generate_upcoming_private(school: School, registrations: List[CourseRegistration]) -> List[dict]:
    date_today = now().date()

    # Fetch SchoolSettings (handle if missing)
    try:
        school_settings = school.settings  # One-to-One relation
        days_ahead = school_settings.days_ahead
        interval = school_settings.interval
    except SchoolSettings.DoesNotExist:
        days_ahead = 21  # Default fallback
        interval = 30  # Default fallback

    generated_lessons = []
    for registration in registrations:
        teacher = registration.cached_teacher  # No need to filter teachers separately
        user = teacher.user
        course = registration.course
        
        # Cached values to reduce DB calls
        unavailables = teacher.cached_unavailables
        lessons = teacher.cached_lessons
        available_times = teacher.cached_available_times  
        for lesson in lessons:
            print(lesson.datetime.tzinfo)
        new_lessons = []
        for available_time in available_times:
            start = available_time.start
            stop = available_time.stop
            day_of_week = int(available_time.day)

            for day_offset in range(days_ahead):
                date_time = date_today + timedelta(days=day_offset)
                if date_time.isoweekday() == day_of_week:
                    interval = course.duration + interval
                    available_slots = compute_available_time(
                        unavailables, lessons, date_time, start, stop, course.duration, interval
                    )
                    for slot in available_slots:
                        new_lessons.append({
                            'datetime': slot['start'],
                        })

        generated_lessons.append({
            "course_name": course.name,
            "course_description": course.description,
            "registration_uuid": registration.uuid,
            'instructor_picture': user.profile_image.url,
            "instructor_name": user.get_full_name(),
            "instructor_phone_number": user.phone_number,
            "instructor_email": user.email,
            "lesson_duration": course.duration,
            "location": school.location,
            "lessons": new_lessons
        })

    return generated_lessons
