from fcm_django.models import FCMDevice
from rest_framework.decorators import permission_classes, api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import Response
from rest_framework.viewsets import ViewSet
from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet
from django.shortcuts import render
from core.models import User
from rest_framework import status
import random
from django.utils.timezone import now
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import make_password, check_password
from utils.sms import SMSClient
# Create your views here.


smsManager = SMSClient()

def forgot_password(request, uuid, token):
    context = {
        'uuid': uuid,
        'token': token
    }
    return render(request, "forgot_password.html", context)


@api_view(['GET'])
def check_usertype(request):
    phone_number = request.GET.get('phone_number')

    if not phone_number:
        return Response({'error': 'Phone number is required'}, status=400)

    try:
        user = User.objects.get(phone_number=phone_number)  # Assuming phone_number is a field in the User model
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
        if not phone_number:
            return Response({'error': 'Phone number is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(phone_number=phone_number)  # Assuming phone_number is used as username
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Generate and save OTP
        otp = f"{random.randint(0, 999999):06d}"
        user.otp = str(otp)
        user.otp_created_at = now()
        user.save()

        # Mock sending OTP (replace with real SMS/email integration)
        print(f"Sending OTP {otp} to {phone_number}")
        smsManager.send_sms("66", phone_number, f"OTP: {otp}")
        return Response({'message': 'OTP sent successfully'}, status=status.HTTP_200_OK)

    def check(self, request):
        phone_number = request.data.get('phone_number')
        otp = request.data.get('otp')

        if not phone_number or not otp:
            return Response({'error': 'Phone number and OTP are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


        if user.otp == otp and user.otp_created_at:
            if (now() - user.otp_created_at).total_seconds() <= 300:
                user.otp = None  # Clear OTP after successful verification
                user.otp_created_at = None
                user.save()
                return Response({'message': 'OTP verified successfully'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)
        
class PinViewSet(ViewSet):
    def check(self, request):
        phone_number = request.data.get('phone_number')
        pin = request.data.get('pin')

        if not phone_number or not pin:
            return Response({'error': 'Phone number and pin are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(phone_number=phone_number)  # Assuming `username` stores phone_number
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
        pin = request.data.get('pin')

        if not phone_number or not pin:
            return Response({'error': 'Phone number and new PIN are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Hash the PIN before saving it
        user.pin = make_password(pin)  # Hash the PIN for security
        user.save()

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        return Response({
            'access': access_token,
            'refresh': str(refresh),
        }, status=status.HTTP_200_OK)    