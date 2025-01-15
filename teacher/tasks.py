from celery import shared_task
from django.core.mail import send_mail
from student.models import Lesson, GuestLesson
from datetime import timedelta
from django.utils import timezone
from pytz import timezone as ptimezone
from utils import send_notification
from celery_singleton import Singleton
import pytz

gmt7 = pytz.timezone('Asia/Bangkok')

# Send Notifications
@shared_task(base=Singleton)
def send_lesson_notification():
    now = timezone.now()
    end_time = now + timedelta(minutes=60)
    upcoming_lessons = list(Lesson.objects.select_related("registration__student__user", "registration__teacher__user").filter(
        booked_datetime__gte=now,
        booked_datetime__lte=end_time,
        status='CON',
        notified=False
    ))
    if upcoming_lessons:
        for lesson in upcoming_lessons:
            gmt_time = lesson.booked_datetime.astimezone(gmt7)
            send_notification(
                lesson.registration.student.user_id, 
                "Lesson Notification", 
                f'You have a lesson with {lesson.registration.teacher.user.first_name} on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.')
            send_notification(
                lesson.registration.teacher.user_id, 
                "Lesson Notification",  
                f'You have a lesson with {lesson.registration.student.user.first_name} on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.')
            lesson.notified = True
            
        Lesson.objects.bulk_update(upcoming_lessons, fields=["notified"])
    return len(upcoming_lessons)

@shared_task(base=Singleton)
def send_guest_lesson_notification():
    now = timezone.now()
    end_time = now + timedelta(minutes=60)
    upcoming_guest_lessons = list(GuestLesson.objects.select_related("teacher__user").filter(
        datetime__gte=now,
        datetime__lte=end_time,
        status='CON',
        notified=False
    ))
    if upcoming_guest_lessons:
        for lesson in upcoming_guest_lessons:
            gmt_time = lesson.datetime.astimezone(gmt7)
            send_notification(
                lesson.teacher.user_id, 
                "Lesson Notification",  
                f'You have a lesson with {lesson.name} on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.')
            send_mail(
                "Lesson Notification", 
                f'You have a lesson with {lesson.teacher.user.first_name} on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.',
                "hello.timeable@gmail.com", 
                [lesson.email], 
                fail_silently=True)
            lesson.notified = True
            
        GuestLesson.objects.bulk_update(upcoming_guest_lessons, fields=["notified"])