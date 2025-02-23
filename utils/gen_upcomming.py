from school.models import School, SchoolSettings
from teacher.models import Lesson
from student.models import CourseRegistration
from django.utils.timezone import now
from utils.schedule_utils import compute_available_time
from typing import List
from datetime import timedelta
from collections import defaultdict
import bisect


def generate_upcoming_private(school: School, registrations: List[CourseRegistration]) -> List[dict]:
    date_today = now().date()

    # Fetch SchoolSettings (handle if missing)
    try:
        school_settings = school.settings  # One-to-One relation
        days_ahead = school_settings.days_ahead
        interval = school_settings.interval
        max_capacity = school.facilities.first().capacity  # Default fallback
    except SchoolSettings.DoesNotExist and AttributeError:
        days_ahead = 21  # Default fallback
        interval = 30  # Default fallback
        max_capacity = 21

    # Fetch all existing lessons in the school
    school_lessons = Lesson.objects.filter(course__school=school, datetime__gte=date_today)
    
    # Track ongoing lessons per time slot and day
    ongoing_lessons_per_day = defaultdict(list)
    for lesson in school_lessons:
        bisect.insort(ongoing_lessons_per_day[lesson.datetime.date()], (lesson.datetime, lesson.end_datetime))
    
    generated_lessons = []
    for registration in registrations:
        teacher = registration.cached_teacher  # No need to filter teachers separately
        user = teacher.user
        course = registration.course
        
        # Cached values to reduce DB calls
        unavailables = teacher.cached_unavailables
        lessons = teacher.cached_lessons
        available_times = teacher.cached_available_times  
        break_time = teacher.teacher_break
        new_lessons = []
        for available_time in available_times:
            start = available_time.start
            stop = available_time.stop
            day_of_week = int(available_time.day)


            for day_offset in range(days_ahead):
                current_date = date_today + timedelta(days=day_offset)
                if current_date.isoweekday() == day_of_week:
                    available_slots = compute_available_time(
                        unavailables, lessons, current_date, start, stop, course.duration, interval, break_time
                    )
                    
                    existing_lessons = ongoing_lessons_per_day[current_date]
                    for slot in available_slots:
                        lesson_start = slot['start']
                        lesson_end = lesson_start + timedelta(minutes=course.duration)
                        
                        # Skip if the facility has reached its max capacity for overlapping slots
                        overlapping_count = sum(
                            1 for l_start, l_end in existing_lessons if not (lesson_end <= l_start or lesson_start >= l_end)
                        )
                        
                        if overlapping_count < max_capacity:
                            new_lessons.append({'datetime': lesson_start})
                                    
        generated_lessons.append({
            "course_name": course.name,
            "course_description": course.description,
            "registration_uuid": registration.uuid,
            'instructor_picture': user.profile_image.url if user.profile_image else "",
            "instructor_name": user.get_full_name(),
            "instructor_phone_number": user.phone_number,
            "instructor_email": user.email,
            "lesson_duration": course.duration,
            "location": school.location,
            "lessons": new_lessons
        })

    return generated_lessons
