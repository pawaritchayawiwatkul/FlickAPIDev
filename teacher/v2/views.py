from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.utils import IntegrityError
from django.db.models import Prefetch
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from datetime import timedelta
import pytz
from dateutil.parser import isoparse
from teacher.models import Teacher, UnavailableTimeOneTime
from teacher.v2.serializers import (
    ListCourseSerializer, CourseDetailSerializer, CreateCourseSerializer,
    ListCourseRegistrationSerializer, CourseRegistrationDetailSerializer, CreateCourseRegistrationSerializer,
    ListStudentSerializer, ProfileSerializer,
    LessonDetailSerializer, ListLessonSerializer,
    ListBookingSerializer, 
    CreateUnavailableTimeOneTimeSerializer, CreateUnavailableTimeRegularSerializer,
    ListUnavailableTimeOneTimeSerializer, ListUnavailableTimeRegularSerializer
)
from student.models import Student, StudentTeacherRelation, CourseRegistration, Lesson, Booking
from school.models import Course
from core.serializers import CreateUserSerializer
from utils.notification_utils import send_notification, create_calendar_event, delete_google_calendar_event
from internal.permissions import IsTeacher, IsManager

gmt7 = pytz.timezone('Asia/Bangkok')

class CourseViewset(ViewSet):
    def get_permissions(self):
        """Apply IsManager only to the create, retrieve, and edit methods"""
        if self.action in ["create", "retrieve", "edit"]:
            return [IsAuthenticated(), IsTeacher(), IsManager()]
        return [IsAuthenticated(), IsTeacher()]
    
    def list(self, request):
        teacher_courses = Course.objects.filter(
            school_id=request.user.teacher.school_id
        )
        serializer = ListCourseSerializer(instance=teacher_courses, many=True)
        return Response(serializer.data)

    def create(self, request):
        data = request.data.copy()
        data["user_id"] = request.user.id
        serializer = CreateCourseSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, uuid):
        course = get_object_or_404(
            Course.objects.prefetch_related(Prefetch("registration")), uuid=uuid
        )
        serializer = CourseDetailSerializer(instance=course)
        return Response(serializer.data)

    def edit(self, request, uuid):
        course = get_object_or_404(Course, uuid=uuid)
        serializer = CourseDetailSerializer(course, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProfileViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]

    def retrieve(self, request):
        serializer = ProfileSerializer(instance=request.user)
        return Response(serializer.data)

    def update(self, request):
        serializer = ProfileSerializer(instance=request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request):
        request.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StudentViewSet(ViewSet):
    # permission_classes = [IsAuthenticated, IsTeacher]
    
    def get_permissions(self):
        """Apply IsManager only to the create method"""
        if self.action == "create":
            return [IsAuthenticated(), IsTeacher(), IsManager()]
        return [IsAuthenticated(), IsTeacher()]
    
    def list(self, request):
        students = StudentTeacherRelation.objects.filter(
            teacher__user_id=request.user.id
        ).select_related("student__user")
        serializer = ListStudentSerializer(instance=students, many=True)
        return Response(serializer.data)

    def create(self, request):
        teacher = get_object_or_404(Teacher, user_id=request.user.id)
        user_serializer = CreateUserSerializer(data=request.data)
        if not user_serializer.is_valid():
            return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = user_serializer.save(is_teacher=False, is_admin=False)
            student = Student.objects.create(user=user)
            student.school.add(teacher.school)
            student.teacher.add(teacher)
            student.save()
            return Response({"success": True}, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            # Check the exception message for details
            error_message = str(e)

            if "core_user_email_key" in error_message:
                return Response({"email": "This email is already in use."}, status=status.HTTP_400_BAD_REQUEST)
            elif "core_user_phone_number" in error_message:  # Example constraint for phone number
                return Response({"phone": "This phone number is already in use."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": "A unique constraint was violated."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list_bookings(self, request, uuid):

        # Get all bookings with optional student filter
        bookings = Booking.objects.select_related("lesson__course__school", "lesson__teacher").filter(student__user__uuid=uuid)
        
        # Serialize the data (assuming a BookingSerializer exists)
        serializer = ListBookingSerializer(bookings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def list_purchases(self, request, uuid):

        # Get all bookings with optional student filter
        registrations = CourseRegistration.objects.select_related("course").filter(student__user__uuid=uuid)
        
        # Serialize the data (assuming a BookingSerializer exists)
        serializer = ListCourseRegistrationSerializer(registrations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class RegistrationViewset(ViewSet):
    def get_permissions(self):
        """Apply IsManager only to the create method"""
        if self.action == "create":
            return [IsAuthenticated(), IsTeacher(), IsManager()]
        return [IsAuthenticated(), IsTeacher()]
    
    def list(self, request):
        filters = {"teacher__user_id": request.user.id}
        if student_uuid := request.GET.get("student_uuid"):
            student = get_object_or_404(Student, user__uuid=student_uuid)
            filters["student"] = student
        if request.GET.get("has_lesson_left") == "true":
            filters["lessons_left__gt"] = 0
        registrations = CourseRegistration.objects.filter(**filters).select_related("course")
        serializer = ListCourseRegistrationSerializer(instance=registrations, many=True)
        return Response(serializer.data)

    def retrieve(self, request, code):
        registration = get_object_or_404(
            CourseRegistration, uuid=code, teacher__user_id=request.user.id
        )
        serializer = CourseRegistrationDetailSerializer(instance=registration)
        return Response(serializer.data)

    def create(self, request):
        data = request.data.copy()
        data["teacher_id"] = request.user.id
        serializer = CreateCourseRegistrationSerializer(data=data)
        if serializer.is_valid():
            registration = serializer.create(serializer.validated_data)
            return Response({"registration_id": registration.uuid}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LessonViewset(ViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]

    def list(self, request):
        filters = {
            "teacher__user_id": request.user.id,
        }

        lesson_status = request.query_params.getlist("status")  # Allows multiple statuses
        status_mapping = {
            "pending": "PENTE",
            "confirm": "CON",
        }

        if lesson_status:
            filters["status__in"] = [status_mapping[status] for status in lesson_status if status in status_mapping]

        # Fetch lessons by month
        month = request.query_params.get("month")
        year = request.query_params.get("year")
        if month and year:
            try:
                month = int(month)
                year = int(year)
                start_date = timezone.datetime(year, month, 1, tzinfo=timezone.utc)
                end_date = (start_date + timedelta(days=32)).replace(day=1)
                filters["datetime__range"] = (start_date, end_date)
            except ValueError:
                return Response({"error": "Invalid month or year"}, status=status.HTTP_400_BAD_REQUEST)

        is_bangkok_time = request.GET.get("bangkok_time", "true").lower() == "true"

        lessons = Lesson.objects.prefetch_related(
            Prefetch(
                "booking",
                queryset=Booking.objects.select_related("student__user")[:1],  # Limit to one student
                to_attr="bookings"
            )
        ).select_related("course").filter(**filters).order_by("datetime")

        serializer = ListLessonSerializer(instance=lessons, many=True)
        response_data = serializer.data
        if is_bangkok_time:
            for data in response_data:
                dt = isoparse(data["datetime"])
                bangkok_time = timezone.make_naive(dt).astimezone(gmt7)
                data["datetime"] = bangkok_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                data["end_datetime"] = bangkok_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        return Response(response_data, status=status.HTTP_200_OK)

    def retrieve(self, request, code):
        filters = {
            "teacher__user_id": request.user.id,
            "code": code,  # Filter by the specific lesson code
        }

        is_bangkok_time = request.GET.get("bangkok_time", "true").lower() == "true"

        lesson = get_object_or_404(
            Lesson.objects.prefetch_related(
                Prefetch(
                    "booking",
                    queryset=Booking.objects.select_related("student__user"),  # Limit to one student
                    to_attr="bookings"
                )
            ).select_related("course"),
            **filters
        )

        serializer = LessonDetailSerializer(instance=lesson)
        response_data = serializer.data

        if is_bangkok_time:
            dt = isoparse(response_data["datetime"])
            bangkok_time = timezone.make_naive(dt).astimezone(gmt7)
            response_data["datetime"] = bangkok_time.strftime('%Y-%m-%dT%H:%M:%SZ')

        return Response(response_data, status=status.HTTP_200_OK)
    
    def cancel(self, request, code):
        lesson = get_object_or_404(
            Lesson,
            code=code, teacher__user_id=request.user.id
        )

        lesson.status = "CAN"
        lesson.save()
        if lesson.teacher_event_id:
            delete_google_calendar_event(request.user, lesson.teacher_event_id)

        return Response({"success": "Lesson canceled successfully."}, status=status.HTTP_200_OK)

    def confirm(self, request, code):
        lesson = get_object_or_404(
            Lesson.objects.select_related("course"),
            code=code, teacher__user_id=request.user.id, status="PENTE"
        )

        lesson.status = "CON"
        try:
            lesson.save()
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)
        return Response({"success": "Lesson confirmed successfully."}, status=status.HTTP_200_OK)

class UnavailableTimeViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]

    def create_onetime(self, request):
        data = request.data.copy()
        data["teacher"] = request.user.teacher.id
        serializer = CreateUnavailableTimeOneTimeSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request):
        teacher = request.user.teacher
        filters = {"teacher": teacher}

        # Fetch unavailable times by month
        month = request.query_params.get("month")
        year = request.query_params.get("year")
        if month and year:
            try:
                month = int(month)
                year = int(year)
                start_date = timezone.datetime(year, month, 1, tzinfo=timezone.utc)
                end_date = (start_date + timedelta(days=32)).replace(day=1)
                filters["date__range"] = (start_date, end_date)
            except ValueError:
                return Response({"error": "Invalid month or year"}, status=status.HTTP_400_BAD_REQUEST)

        onetime_unavailable = UnavailableTimeOneTime.objects.filter(**filters)
        # regular_unavailable = UnavailableTimeRegular.objects.filter(teacher=teacher)
        onetime_serializer = ListUnavailableTimeOneTimeSerializer(onetime_unavailable, many=True)
        # regular_serializer = ListUnavailableTimeRegularSerializer(regular_unavailable, many=True)
        return Response({
            "onetime": onetime_serializer.data,
        }, status=status.HTTP_200_OK)

    def remove(self, request, code):
        onetime_unavailable = get_object_or_404(UnavailableTimeOneTime, code=code, teacher=request.user.teacher)
        onetime_unavailable.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)