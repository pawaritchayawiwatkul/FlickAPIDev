import random
import string
from django.utils import timezone
from datetime import datetime, timedelta
from student.models import Lesson, GuestLesson
from teacher.models import UnavailableTimeOneTime
from typing import List
from rest_framework.response import Response
from cryptography.fernet import Fernet
from django.conf import settings
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from django.utils.timezone import localtime
import pytz
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

# Generate a key and store it securely (should be done once and stored securely)

gmt7 = pytz.timezone('Asia/Bangkok')
fernet = Fernet(settings.FERNET_KEY)
_timezone =  timezone.get_current_timezone().__str__()
base_datetime = datetime(1999,1, 1)

def delete_google_calendar_event(user, event_id):
    credentials_data = user.google_credentials
    if not credentials_data:
        print("NO CRED")
        return 
        

    # Decrypt the credentials
    try:
        token = decrypt_token(credentials_data['token'])
        refresh_token = decrypt_token(credentials_data['refresh_token'])
    except Exception as e:
        return 

    # Rebuild the credentials object
    credentials = Credentials(
        token=token,
        refresh_token=refresh_token,
        token_uri=credentials_data['token_uri'],
        client_id=credentials_data['client_id'],
        client_secret=credentials_data['client_secret'],
        scopes=credentials_data['scopes']
    )
    service = build("calendar", "v3", credentials=credentials)

    try:
        # Delete the event by its eventId
        print("DELETING")
        service.events().delete(calendarId=user.google_calendar_id, eventId=event_id).execute()
        print("CANCEL")
        return 
    except Exception as e:
        print(e)
        return 

def create_calendar_event(user, summary, description, start, end):
    credentials_data = user.google_credentials
    if not credentials_data:
        return 

    # Decrypt the credentials
    try:
        token = decrypt_token(credentials_data['token'])
        refresh_token = decrypt_token(credentials_data['refresh_token'])
    except Exception as e:
        print(f"Error Failed to Decrypt : {e}")
        return 
    # Rebuild the credentials object
    credentials = Credentials(
        token=token,
        refresh_token=refresh_token,
        token_uri=credentials_data['token_uri'],
        client_id=credentials_data['client_id'],
        client_secret=credentials_data['client_secret'],
        scopes=credentials_data['scopes']
    )
    service = build("calendar", "v3", credentials=credentials)

    # Event data from the request
    event = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start,
            "timeZone": _timezone,
        },
        "end": {
            "dateTime": end,
            "timeZone": _timezone,
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 24 * 60},
                {"method": "popup", "minutes": 10},
            ],
        },
    }
    
    try:
        created_event = service.events().insert(calendarId=user.google_calendar_id, body=event).execute()
        return created_event["id"]
    except Exception as e:
        print(f"Error Failed to Insert : {e}")
        pass 
        

def send_notification(user_id, title, body):
    devices = FCMDevice.objects.filter(user_id=user_id)
    devices.send_message(
            message=Message(
                notification=Notification(
                    title=title,
                    body=body
                ),
            ),
        )
    
def encrypt_token(token: str) -> str:
    encrypted_token = fernet.encrypt(token.encode())
    return encrypted_token.decode()

def decrypt_token(encrypted_token: str) -> str:
    decrypted_token = fernet.decrypt(encrypted_token.encode())
    return decrypted_token.decode()

def generate_unique_code(length=8):
    """Generate a unique random code."""
    characters = string.ascii_letters + string.digits
    code = ''.join(random.choice(characters) for _ in range(length))
    return code

def merge_schedule(validated_data, unavailables):
    new_start = validated_data['start']
    new_stop = validated_data['stop']
    overlap = []
    for interval in unavailables:
        start = interval.start
        stop = interval.stop
        _ = False
        if start > new_stop:
            # print('1')
            continue
        elif stop < new_start:
            # print('2')
            continue
        if start <= new_start:
            # print('3')
            new_start = start
            _ = True
        if stop >= new_stop:
            # print('4')
            new_stop = stop
            _ = True
        overlap.append(interval)

    validated_data['start'] = new_start
    validated_data['stop'] = new_stop
    return validated_data, overlap

def compute_available_time(unavailables:List[UnavailableTimeOneTime], lessons:List[Lesson], guest_lessons:List[GuestLesson], date_time, start, stop, duration):
    duration = timedelta(minutes=duration)
    interval = timedelta(minutes=30)
    available_times = []

    current_time = timezone.make_aware(datetime.combine(date_time, start), timezone=gmt7)
    stop_time = timezone.make_aware(datetime.combine(date_time, stop), timezone=gmt7)

    while current_time + duration <= stop_time:
        end_time = current_time + duration
        
        _is_available = True
        for unavailable in unavailables:
            start_ = timezone.make_aware(datetime.combine(date_time, unavailable.start), timezone=gmt7)
            stop_ = timezone.make_aware(datetime.combine(date_time, unavailable.stop), timezone=gmt7)
            if (start_ <= current_time < stop_) or (start_ < end_time <= stop_):
                _is_available = False
                break
        for lesson in lessons:
            start_ = lesson.booked_datetime
            stop_ = start_ + timedelta(minutes=lesson.registration.course.duration)
            print(start_.tzinfo, start_, stop_)
            print(current_time)
            if (start_ <= current_time < stop_) or (start_ < end_time <= stop_):
                _is_available = False
                break
        for lesson in guest_lessons:
            start_ = lesson.datetime
            stop_ = start_ + timedelta(minutes=lesson.duration)
            if (start_ <= current_time < stop_) or (start_ < end_time <= stop_):
                _is_available = False
                break
        if _is_available:
            available_times.append({
                "start": current_time.strftime("%H:%M:%S"),
                "end": end_time.strftime("%H:%M:%S")
            })
        current_time += interval
    return available_times

def is_available(unavailables:List[UnavailableTimeOneTime], lessons:List[Lesson], guest_lessons:List[GuestLesson], date_time, start, stop, duration):
    start_time = date_time
    end_time = start_time + timedelta(minutes=duration)
    school_start = timezone.make_aware(datetime.combine(date_time, start), timezone=gmt7)
    school_close = timezone.make_aware(datetime.combine(date_time, stop), timezone=gmt7)
    if not (school_start <= start_time < school_close) or not (school_start <= end_time <= school_close):
        return False
    for unavailable in unavailables:
        start_ = timezone.make_aware(datetime.combine(start_time, unavailable.start), timezone=gmt7)
        stop_ = timezone.make_aware(datetime.combine(start_time, unavailable.stop), timezone=gmt7)
        if (start_ <= start_time < stop_) or (start_ < end_time <= stop_):
            return False
    for lesson in lessons:
        start_ = lesson.booked_datetime
        stop_ = start_ + timedelta(minutes=duration)
        if (start_ <= start_time < stop_) or (start_ < end_time <= stop_):
            return False
    for lesson in guest_lessons:
        start_ = lesson.datetime
        stop_ = start_ + timedelta(minutes=duration)
        if (start_ <= start_time < stop_) or (start_ < end_time <= stop_):
            return False
    return True

def send_cancellation_email_html(student_name, tutor_name, lesson_date, lesson_time, duration, mode, student_email):
    # Prepare the email subject
    email_subject = f"Lesson Cancellation : {tutor_name}"

    # Render the email content as HTML
    email_body = render_to_string("email/lesson_canceled.html", {
        "student_name": student_name,
        "tutor_name": tutor_name,
        "lesson_date": lesson_date,
        "lesson_time": lesson_time,
        "duration": duration,
        "mode": mode,
    })

    # Create the email object
    email = EmailMessage(
        subject=email_subject,
        body=email_body,
        from_email="hello.timeable@gmail.com",  # Sender email
        to=[student_email],                    # Recipient email
    )

    # Specify the content type as HTML
    email.content_subtype = "html"

    # Send the email
    email.send()

def send_lesson_requested_email(student_name, tutor_name, requested_date, requested_time, duration, mode, student_email):
    # Prepare the email subject
    email_subject = f"Lesson Requested: {tutor_name}"

    # Render the email content as HTML
    email_body = render_to_string("email/lesson_requested.html", {
        "student_name": student_name,
        "tutor_name": tutor_name,
        "requested_date": requested_date,
        "requested_time": requested_time,
        "duration": duration,
        "mode": mode,
    })

    # Create the email object
    email = EmailMessage(
        subject=email_subject,
        body=email_body,
        from_email="hello.timeable@gmail.com",  # Sender email
        to=[student_email],                    # Recipient email
    )

    # Specify the content type as HTML
    email.content_subtype = "html"

    # Send the email
    email.send()

def send_lesson_confirmation_email(user_name, tutor_name, student_name, lesson_date, lesson_time, lesson_duration, mode, user_email):
    # Prepare the email subject
    email_subject = "Lesson Confirmation"

    # Render the email content as HTML
    email_body = render_to_string("email/lesson_confirm.html", {
        "user_name": user_name,
        "tutor_name": tutor_name,
        "student_name": student_name,
        "lesson_date": lesson_date,
        "lesson_time": lesson_time,
        "lesson_duration": lesson_duration,
        "mode": mode,
    })

    # Create the email object
    email = EmailMessage(
        subject=email_subject,
        body=email_body,
        from_email="hello.timeable@gmail.com",  # Sender email
        to=[user_email],                       # Recipient email
    )

    # Specify the content type as HTML
    email.content_subtype = "html"

    # Send the email
    email.send()