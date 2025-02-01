from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from teacher.models import Teacher
from teacher.serializers import ProfileSerializer
from rest_framework.views import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from django.utils import timezone
import pytz

_timezone =  timezone.get_current_timezone()
gmt7 = pytz.timezone('Asia/Bangkok')

@permission_classes([IsAuthenticated])
class ProfileViewSet(ViewSet):
    def retrieve(self, request):
        user = request.user
        try:
            ser = ProfileSerializer(instance=user)
            return Response(ser.data)
        except Teacher.DoesNotExist:
            return Response(status=404)
    
    def update(self, request):
        user = request.user
        ser = ProfileSerializer(data=request.data)
        if ser.is_valid():
            user = ser.update(user, ser.validated_data)
            return Response(status=200)
        else:
            return Response(ser.errors, status=400)

    def destroy(self, request):
        request.user.delete()
        return Response(status=200)


@permission_classes([IsAuthenticated])
class TeacherViewset(ViewSet):
    def list(self, request):
        return Response()

    def favorite(self, request, code):
        return Response()

@permission_classes([IsAuthenticated])
class RegistrationViewset(ViewSet):
    def favorite(self, request, code):
        return Response()

    def list(self, request):
        return Response()

    def get_available_time(self, request, code):
        return Response()

    def retrieve(self, request, code):
        return Response()

    def create(self, request):
        return Response()

@permission_classes([IsAuthenticated])
class LessonViewset(ViewSet):
    def cancel(self, request, code):
        return Response()

    def confirm(self, request, code):
        return Response()

    def status(self, request, status):
        return Response()

    def recent(self, request):
        return Response()

    def week(self, request):
        return Response()

    def day(self, request):
        return Response()

    def create(self, request):
        return Response()

@permission_classes([IsAuthenticated])
class GuestViewset(ViewSet):
    def booking_screen(self, request, code):
        return Response()

    def create_guest_lesson(self, request, code):
        return Response()

    def get_available_time(self, request, code):
        return Response()

@permission_classes([IsAuthenticated])
class UnavailableTimeViewset(ViewSet):
    def one_time(self, request):
        return Response()

    def regular(self, request):
        return Response()

    def retrieve(self, request):
        return Response()

    def remove(self, request, code):
        return Response()

@permission_classes([IsAuthenticated])
class CourseViewset(ViewSet):
    def favorite(self, request, code):
        return Response()

    def list(self, request):
        return Response()

    def create(self, request):
        return Response()

    def remove(self, request, code):
        return Response()

    def retrieve(self, request, code):
        return Response()

    def retrieve_with_student(self, request, code):
        return Response()

@permission_classes([IsAuthenticated])
class SchoolViewSet(ViewSet):
    def retrieve(self, request):
        return Response()

    def update(self, request):
        return Response()

@permission_classes([IsAuthenticated])
class StudentViewset(ViewSet):
    def create(self, request):
        return Response()

    def update(self, request, code):
        return Response()

    def add(self, request, code):
        return Response()

    def search(self, request):
        return Response()

    def list(self, request):
        return Response()

    def favorite(self, request, code):
        return Response()
