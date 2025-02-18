from celery import shared_task
from django.core.mail import send_mail
from django.db.models import Prefetch
from student.models import Lesson, Booking
from datetime import timedelta
from django.utils import timezone
from pytz import timezone as ptimezone
from utils.notification_utils import send_notification
from celery_singleton import Singleton
import pytz

gmt7 = pytz.timezone('Asia/Bangkok')

# Send Notifications
@shared_task(base=Singleton)
def send_lesson_notification():
    now = timezone.now()
    end_time = now + timedelta(minutes=60)
    upcoming_lessons = list(Lesson.objects.select_related("teacher__user").prefetch_related(
       Prefetch("booking", queryset=Booking.objects.select_related("student__user").filter(status='COM'), to_attr="cached_booking")
    ).filter(
        # datetime__gte=now,
        datetime__lte=end_time,
        status='CON',
        notified=False
    ))
    if upcoming_lessons:
        for lesson in upcoming_lessons:
            gmt_time = lesson.datetime.astimezone(gmt7)
            if lesson.teacher:
                if not lesson.course.is_group:
                    send_notification(
                        lesson.teacher.user_id, 
                        "Lesson Notification",  
                        f'You have a lesson with {lesson.cached_booking[0].student.user.first_name} on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.')
                else:
                    send_notification(
                        lesson.teacher.user_id, 
                        "Lesson Notification",  
                        f'You have a lesson on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.'
                    )
                for booking in lesson.cached_booking:
                    send_notification(
                        booking.student.user_id,
                        "Lesson Notification", 
                        f'You have a lesson with {lesson.teacher.user.first_name} on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.',
                    )
            else:
                for booking in lesson.cached_booking:
                    send_notification(
                        booking.student.user_id,
                        "Lesson Notification", 
                        f'You have a lesson on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.',
                    )
            lesson.notified = True
            
        Lesson.objects.bulk_update(upcoming_lessons, fields=["notified"])
    return len(upcoming_lessons)
