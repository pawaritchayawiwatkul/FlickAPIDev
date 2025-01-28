from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.db.models import Prefetch
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
import pytz
from dateutil.parser import isoparse

from teacher.models import Teacher, TeacherCourses
from teacher.v2.serializers import (
    ListCourseSerializer, CourseDetailSerializer, CreateCourseSerializer,
    ListCourseRegistrationSerializer, CourseRegistrationDetailSerializer, CreateCourseRegistrationSerializer,
    ListStudentSerializer, ProfileSerializer,
    LessonDetailSerializer, ListLessonSerializer,
    ListBookingSerializer
)
from student.models import Student, StudentTeacherRelation, CourseRegistration, Lesson, Booking
from school.models import Course
from core.serializers import CreateUserSerializer
from utils.util import send_notification, create_calendar_event, delete_google_calendar_event

_timezone = timezone.get_current_timezone()
gmt7 = pytz.timezone('Asia/Bangkok')

@permission_classes([IsAuthenticated])
class CourseViewset(ViewSet):
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
            course = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def remove(self, request, uuid):
        teacher_course = get_object_or_404(
            TeacherCourses, teacher__user_id=request.user.id, course__uuid=uuid
        )
        teacher_course.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

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

@permission_classes([IsAuthenticated])
class ProfileViewSet(ViewSet):
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

@permission_classes([IsAuthenticated])
class StudentViewSet(ViewSet):
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
            StudentTeacherRelation.objects.create(
                student=student,
                teacher=teacher,
                student_first_name=student.user.first_name,
                student_last_name=student.user.last_name,
            )
            return Response({"success": True}, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
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
    
@permission_classes([IsAuthenticated])
class RegistrationViewset(ViewSet):
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
        serializer = CreateCourseRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            registration = serializer.save()
            return Response({"registration_id": registration.uuid}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated])
class LessonViewset(ViewSet):
    def list(self, request):
        filters = {
            "teacher__user_id": request.user.id,
            "datetime__gte": timezone.now().date(),
        }

        lesson_status = request.query_params.getlist("status")  # Allows multiple statuses
        status_mapping = {
            "pending": "PENTE",
            "confirm": "CON",
            "available": "AVA",
        }

        if lesson_status:
            filters["status__in"] = [status_mapping[status] for status in lesson_status if status in status_mapping]

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
        return Response(response_data, status=status.HTTP_200_OK)

    def retrieve(self, request, code):
        filters = {
            "teacher__user_id": request.user.id,
            "datetime__gte": timezone.now().date(),
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

        gmt_time = lesson.datetime.astimezone(gmt7)
        # send_notification(
        #     lesson.registration.student.user_id,
        #     "Lesson Canceled!",
        #     f'{request.user.first_name} on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.'
        # )

        # if lesson.student_event_id:
        #     delete_google_calendar_event(lesson.registration.student, lesson.student_event_id)
        if lesson.teacher_event_id:
            delete_google_calendar_event(request.user, lesson.teacher_event_id)

        return Response({"success": "Lesson canceled successfully."}, status=status.HTTP_200_OK)

    def confirm(self, request, code):
        lesson = get_object_or_404(
            Lesson.objects.select_related("registration__course", "registration__student__user"),
            code=code, registration__teacher__user_id=request.user.id, status="PENTE"
        )

        lesson.status = "CON"
        finished = lesson.datetime + timedelta(minutes=lesson.registration.course.duration)
        start_time_str = lesson.datetime.strftime("%Y-%m-%dT%H:%M:%S%z")
        end_time_str = finished.strftime("%Y-%m-%dT%H:%M:%S%z")

        student_event_id = create_calendar_event(
            lesson.registration.student.user,
            summary=lesson.generate_title(is_teacher=False),
            description=lesson.generate_description(is_teacher=False),
            start=start_time_str,
            end=end_time_str
        )
        teacher_event_id = create_calendar_event(
            request.user,
            summary=lesson.generate_title(is_teacher=True),
            description=lesson.generate_description(is_teacher=True),
            start=start_time_str,
            end=end_time_str
        )

        if student_event_id:
            lesson.student_event_id = student_event_id
        if teacher_event_id:
            lesson.teacher_event_id = teacher_event_id
        lesson.save()

        gmt_time = lesson.datetime.astimezone(gmt7)
        send_notification(
            lesson.registration.student.user_id,
            "Lesson Confirmed!",
            f'{request.user.first_name} on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.'
        )

        return Response({"success": "Lesson confirmed successfully."}, status=status.HTTP_200_OK)

    def attended(self, request, code):
        lesson = get_object_or_404(
            Lesson.objects.select_related("registration__course", "registration__student"),
            code=code, registration__teacher__user_id=request.user.id, status="CON"
        )

        if lesson.datetime >= timezone.now():
            return Response({"failed": "Lesson has not passed the booked datetime."}, status=status.HTTP_400_BAD_REQUEST)

        lesson.status = "COM"
        lesson.save()
        # lesson.registration.lessons_left = max(0, lesson.registration.lessons_left - 1)
        # lesson.registration.save()

        gmt_time = lesson.datetime.astimezone(gmt7)
        send_notification(
            lesson.registration.student.user_id,
            "Lesson Attended!",
            f'{request.user.first_name} on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.'
        )

        return Response({"success": "Lesson attended successfully."}, status=status.HTTP_200_OK)

    def missed(self, request, code):
        lesson = get_object_or_404(
            Lesson.objects.select_related("registration__course", "registration__student"),
            code=code, registration__teacher__user_id=request.user.id, status="CON"
        )

        if lesson.datetime >= timezone.now():
            return Response({"failed": "Lesson has not passed the booked datetime."}, status=status.HTTP_400_BAD_REQUEST)

        lesson.status = "MIS"
        lesson.save()

        gmt_time = lesson.datetime.astimezone(gmt7)
        send_notification(
            lesson.registration.student.user_id,
            "Lesson Missed!",
            f'{request.user.first_name} on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.'
        )

        return Response({"success": "Lesson marked as missed."}, status=status.HTTP_200_OK)
    
