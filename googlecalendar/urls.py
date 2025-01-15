# urls.py
from django.urls import path
from googlecalendar import views

urlpatterns = [
    path("init/", views.GoogleCalendarInitView.as_view(), name="google_calendar_init"),
    path("callback/", views.GoogleCalendarCallbackView.as_view(), name="google_calendar_callback"),
    path("events/", views.CreateGoogleCalendarEventView.as_view(), name="create_google_calendar_events"),
]