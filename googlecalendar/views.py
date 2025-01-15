from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from utils import encrypt_token, decrypt_token
from django.utils import timezone
from django.shortcuts import render

User = get_user_model()
_timezone =  timezone.get_current_timezone_name()

class GoogleCalendarInitView(APIView):
    """
    Start Google Calendar OAuth 2.0 flow.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Initialize OAuth flow
        flow = Flow.from_client_secrets_file(
            settings.GOOGLE_CLIENT_SECRET_FILE,
            scopes=settings.GOOGLE_SCOPES,
        )
        flow.redirect_uri = request.build_absolute_uri('/calendar/callback/')

        refresh = RefreshToken.for_user(request.user)
        state = str(refresh.access_token)
        encrypted_state = encrypt_token(state)

        # Generate authorization URL
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            state=encrypted_state  # The plain state is passed as part of the OAuth URL
        )

        return Response({"authorization_url": authorization_url})



class GoogleCalendarCallbackView(APIView):
    """
    Handle the OAuth 2.0 callback, validate the state, and save user credentials.
    """
    authentication_classes = []  # No authentication required for the callback
    permission_classes = []

    def get(self, request):
        # Decrypt the state stored in the session
        encrypted_state = request.GET.get('state')
        try:
            decrypted_state = decrypt_token(encrypted_state)
        except Exception as e:
            return render(request, "google_calendar_linked_confirmation.html", {"success": False})

        authorization_response = request.build_absolute_uri()
        try:
            access_token = AccessToken(decrypted_state)
            user_id = access_token['user_id']
            user = User.objects.get(id=user_id)
        except Exception as e:
            return render(request, "google_calendar_linked_confirmation.html", {"success": False})

        # Exchange authorization code for credentials
        flow = Flow.from_client_secrets_file(
            settings.GOOGLE_CLIENT_SECRET_FILE,
            scopes=settings.GOOGLE_SCOPES,
        )
        flow.redirect_uri = request.build_absolute_uri('/calendar/callback/')

        try:
            flow.fetch_token(authorization_response=authorization_response)
        except Exception as e:
            return render(request, "google_calendar_linked_confirmation.html", {"success": False})

        # Save encrypted credentials in user's database record
        credentials = flow.credentials
        encrypted_token = encrypt_token(credentials.token)

        # Check if a refresh_token exists
        if credentials.refresh_token:
            encrypted_refresh_token = encrypt_token(credentials.refresh_token)
        else:
            encrypted_refresh_token = None  # Handle cases where refresh_token might not be present

        user.google_credentials = {
            'token': encrypted_token,
            'refresh_token': encrypted_refresh_token,  # Include the refresh_token
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }

        credentials = Credentials(
            token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_uri=credentials.token_uri,
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            scopes=credentials.scopes
        )
        
        service = build("calendar", "v3", credentials=credentials)
        calendar_body = {
            "summary": "Timeable - Schedule",
            "timeZone": _timezone,
            "description": "Your institute schedule"
        }
        try:
            new_calendar = service.calendars().insert(body=calendar_body).execute()
            user.google_calendar_id = new_calendar['id']
        except Exception as e:
            return render(request, "google_calendar_linked_confirmation.html", {"success": False})

        user.save()
        return render(request, "google_calendar_linked_confirmation.html", {"success": True})

class CreateGoogleCalendarEventView(APIView):
    """
    Create a Google Calendar event for the authenticated user.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check if the user has linked Google Calendar
        user = request.user
        credentials_data = user.google_credentials
        if not credentials_data:
            return Response({"error": "Google Calendar is not linked."}, status=400)

        # Decrypt the credentials
        try:
            token = decrypt_token(credentials_data['token'])
        except Exception as e:
            return Response({"error": "Failed to decrypt credentials."}, status=500)

        # Rebuild the credentials object
        credentials = Credentials(
            token=token,
            token_uri=credentials_data['token_uri'],
            client_id=credentials_data['client_id'],
            client_secret=credentials_data['client_secret'],
            scopes=credentials_data['scopes']
        )
        service = build("calendar", "v3", credentials=credentials)

        # Event data from the request
        event_data = request.data
        event = {
            "summary": event_data.get("summary", "New Event"),
            "location": event_data.get("location", ""),
            "description": event_data.get("description", ""),
            "start": {
                "dateTime": event_data.get("start"),
                "timeZone": event_data.get("timeZone", "UTC"),
            },
            "end": {
                "dateTime": event_data.get("end"),
                "timeZone": event_data.get("timeZone", "UTC"),
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
            # Create the event
            created_event = service.events().insert(calendarId=user.google_calendar_id, body=event).execute()
            return Response({"message": "Event created successfully!", "event": created_event})
        except Exception as e:
            return Response({"error": str(e)}, status=500)
