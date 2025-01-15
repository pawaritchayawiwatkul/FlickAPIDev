from fcm_django.models import FCMDevice
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import Response
from django.http import JsonResponse
from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet
from django.shortcuts import render
from core.models import User
# Create your views here.

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
        

def forgot_password(request, uuid, token):
    context = {
        'uuid': uuid,
        'token': token
    }
    return render(request, "forgot_password.html", context)

def account_activation(request, uuid, token):
    context = {
        'uuid': uuid,
        'token': token
    }
    return render(request, "account_activation.html", context)

def activate_account(request, uuid, token):
    try:
        # Here you will check the token and uid to see if it matches a user
        user = User.objects.get(uuid=uuid)  # Replace with your user lookup logic
        if user.check_activation_token(token):  # Replace with your token check logic
            user.is_active = True
            user.save()
            print("success")
            return JsonResponse({'success': 'User account activated successfully.'})
        else:
            print("invalid token")
            return JsonResponse({'error': 'Invalid token.'}, status=400)
    except User.DoesNotExist:
        print("dones")
        return JsonResponse({'error': 'User not found.'}, status=404)