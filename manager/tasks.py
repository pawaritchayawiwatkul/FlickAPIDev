from school.models import School, SchoolSettings
from student.models import CourseRegistration
from django.utils.timezone import now
from datetime import timedelta
from utils.schedule_utils import compute_available_time
from typing import List

def generate_upcoming_private(school: School, registrations: List[CourseRegistration]) -> List[dict]:
    date_today = now().date()

    # Fetch SchoolSettings (handle if missing)
    try:
        school_settings = school.settings  # One-to-One relation
        days_ahead = school_settings.days_ahead
        interval = school_settings.interval
        gap = 15
    except SchoolSettings.DoesNotExist:
        days_ahead = 21  # Default fallback
        interval = 30  # Default fallback
        gap = 15
        
    generated_lessons = []
    for registration in registrations:
        teacher = registration.cached_teacher  # No need to filter teachers separately
        user = teacher.user
        course = registration.course
        
        # Cached values to reduce DB calls
        unavailables = teacher.cached_unavailables
        lessons = teacher.cached_lessons
        available_times = teacher.cached_available_times  
        new_lessons = []
        for available_time in available_times:
            start = available_time.start
            stop = available_time.stop
            day_of_week = int(available_time.day)


            for day_offset in range(days_ahead):
                current_date = date_today + timedelta(days=day_offset)
                if current_date.isoweekday() == day_of_week:
                    available_slots = compute_available_time(
                        unavailables, lessons, current_date, start, stop, course.duration, interval, gap
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
