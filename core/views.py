from fcm_django.models import FCMDevice
from rest_framework.decorators import permission_classes, api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import Response
from rest_framework.viewsets import ViewSet
from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet
from django.shortcuts import render
from rest_framework import status
import random
from django.utils.timezone import now
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import make_password, check_password
from utils.sms import SMSClient
from django.core.cache import cache
import hashlib
import secrets
from core.models import User
from core.serializers import NotificationSerializer
from phonenumbers import is_valid_number, parse, NumberParseException, region_code_for_country_code

# Create your views here.


smsManager = SMSClient()

def forgot_password(request, uuid, token):
    context = {
        'uuid': uuid,
        'token': token
    }
    return render(request, "forgot_password.html", context)


class NotificationViewSet(ViewSet):
    """
    API endpoint that allows users to view their notifications.
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        List all unread notifications for the authenticated user.
        """
        notifications = request.user.notifications.unread()
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)
    
@api_view(['GET'])
def check_usertype(request, type):
    if type == 'teacher':
        filters = {'is_teacher': True}
    elif type == 'student':
        filters = {'is_teacher': False, 'is_manager': False}
    else:
        return Response({'error': 'Invalid user type'}, status=400)
    
    phone_number = request.GET.get('phone_number')
    if not phone_number:
        return Response({'error': 'Phone number is required'}, status=400)
    filters['phone_number'] = phone_number
    try:
        user = User.objects.get(**filters)  # Assuming phone_number is a field in the User model
    except User.DoesNotExist:
        return Response({'user_type': 0})  # User not found

    # Check if the user has a PIN
    if not user.pin:
        return Response({'user_type': 2})  # User exists but has no PIN

    return Response({'user_type': 1})  # User exists and has a PIN

@permission_classes([IsAuthenticated])
class DeviceViewSet(FCMDeviceAuthorizedViewSet):
    def remove(self, request):
        try:
            device_id = request.data.get("device_id")
            if device_id == None:
                return Response({"error" : "Please Provide Device Id"}, status=400)
            device = FCMDevice.objects.get(user_id=request.user.id, registration_id=device_id)
            device.delete()
            return Response(status=200)
        except FCMDevice.DoesNotExist:
            return Response({"error" : "FCMDevice Not Found"}, status=404)

class OTPViewSet(ViewSet):
    def send(self, request):
        phone_number = request.data.get('phone_number')
        country_code = request.data.get('country_code', 66)  # Default to '66' if not provided
        if not phone_number:
            return Response({'error': 'Phone number is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            country_code = int(country_code)
            region = region_code_for_country_code(country_code)
            parsed_number = parse(phone_number, region)

            if not is_valid_number(parsed_number):
                return Response({'error': 'Invalid phone number'}, status=status.HTTP_400_BAD_REQUEST)
        except (NumberParseException, ValueError):
            return Response({'error': 'Invalid country code or phone number'}, status=status.HTTP_400_BAD_REQUEST)


        try:
            user = User.objects.get(phone_number=phone_number, country_code=country_code)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Generate and save OTP
        otp = f"{random.randint(0, 999999):06d}"
        user.otp = str(otp)
        user.otp_created_at = now()
        user.save()

        # Mock sending OTP (replace with real SMS/email integration)
        print(f"Sending OTP {otp} to {phone_number}")
        smsManager.send_sms(str(country_code), phone_number, f"Your MindChoice OTP is: {otp}. Use this to verify your account. Do not share this code with anyone.")
        return Response({'message': 'OTP sent successfully'}, status=status.HTTP_200_OK)

    def check(self, request):
        phone_number = request.data.get('phone_number')
        country_code = request.data.get('country_code', 66)  # Default to '66' if not provided
        otp = request.data.get('otp')

        if not phone_number or not otp:
            return Response({'error': 'Phone number and OTP are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            country_code = int(country_code)
            region = region_code_for_country_code(country_code)
            parsed_number = parse(phone_number, region)

            if not is_valid_number(parsed_number):
                return Response({'error': 'Invalid phone number'}, status=status.HTTP_400_BAD_REQUEST)
        except (NumberParseException, ValueError):
            return Response({'error': 'Invalid country code or phone number'}, status=status.HTTP_400_BAD_REQUEST)


        try:
            user = User.objects.get(phone_number=phone_number, country_code=country_code)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        if user.otp == otp and user.otp_created_at:
            if (now() - user.otp_created_at).total_seconds() <= 300:
                # Generate a temporary key for setting the PIN
                # Generate a more complex temporary key
                secret_key = secrets.token_hex(16)  # Generate a secure random secret key

                raw_key = f"{phone_number}:{secret_key}"
                temp_key = hashlib.sha256(raw_key.encode()).hexdigest()
                
                cache.set(temp_key, True, timeout=300)  # Valid for 5 minutes

                # Clear OTP after successful verification
                user.otp = None
                user.otp_created_at = None
                user.save()

                return Response({
                    'message': 'OTP verified successfully',
                    'temp_key': raw_key
                }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)
        
class PinViewSet(ViewSet):
    def check(self, request):
        phone_number = request.data.get('phone_number')
        country_code = request.data.get('country_code', 66)  # Default to '66' if not provided
        pin = request.data.get('pin')

        if not phone_number or not pin:
            return Response({'error': 'Phone number and pin are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            country_code = int(country_code)
            region = region_code_for_country_code(country_code)
            parsed_number = parse(phone_number, region)

            if not is_valid_number(parsed_number):
                return Response({'error': 'Invalid phone number'}, status=status.HTTP_400_BAD_REQUEST)
        except (NumberParseException, ValueError):
            return Response({'error': 'Invalid country code or phone number'}, status=status.HTTP_400_BAD_REQUEST)


        try:
            user = User.objects.get(phone_number=phone_number, country_code=country_code)  # Assuming `username` stores phone_number
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Verify PIN (hashed in the database)
        if user.pin is None:
            return Response({'error': 'User not set pin.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not check_password(pin, user.pin):  # Assuming the `pin` field is stored in the User model or profile
            return Response({'error': 'Invalid PIN.'}, status=status.HTTP_400_BAD_REQUEST)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        return Response({
            'access': access_token,
            'refresh': str(refresh),
        }, status=status.HTTP_200_OK)

    def set_pin(self, request):
        phone_number = request.data.get('phone_number')
        country_code = request.data.get('country_code', '66')  # Default to '66' if not provided
        pin = request.data.get('pin')
        temp_key = request.data.get('temp_key')

        if not phone_number or not pin or not temp_key:
            return Response({'error': 'Phone number, PIN, and temp key are required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            country_code = int(country_code)
            region = region_code_for_country_code(country_code)
            parsed_number = parse(phone_number, region)

            if not is_valid_number(parsed_number):
                return Response({'error': 'Invalid phone number'}, status=status.HTTP_400_BAD_REQUEST)
        except (NumberParseException, ValueError):
            return Response({'error': 'Invalid country code or phone number'}, status=status.HTTP_400_BAD_REQUEST)


        try:
            # Extract and validate the phone number from the temp_key
            temp_key_parts = temp_key.split(':')
            if temp_key_parts[0] != phone_number:
                return Response({'error': 'Invalid temp key for the given phone number.'}, status=status.HTTP_400_BAD_REQUEST)
            
            hased_temp = hashlib.sha256(temp_key.encode()).hexdigest()
            # Validate the temp_key in cache
            if not cache.get(hased_temp):
                return Response({'error': 'Invalid or expired temp key.'}, status=status.HTTP_400_BAD_REQUEST)

            # Fetch user by phone number
            user = User.objects.get(phone_number=phone_number, country_code=country_code)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Hash the PIN before saving it
        user.pin = make_password(pin)  # Hash the PIN for security
        user.save()

        # Invalidate the temp key
        cache.delete(temp_key)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        return Response({
            'access': access_token,
            'refresh': str(refresh),
        }, status=status.HTTP_200_OK)