import random
import string
from django.utils import timezone
from datetime import datetime
from cryptography.fernet import Fernet
from django.conf import settings
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import pytz
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

# Generate a key and store it securely (should be done once and stored securely)

gmt7 = pytz.timezone('Asia/Bangkok')
fernet = Fernet(settings.FERNET_KEY)
_timezone =  timezone.get_current_timezone().__str__()
base_datetime = datetime(1999,1, 1)

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