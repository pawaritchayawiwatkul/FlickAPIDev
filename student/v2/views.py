from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, F, Prefetch
from manager.models import Admin
from student.models import CourseRegistration, Student, StudentTeacherRelation, Booking
from teacher.models import Teacher, Lesson
from school.models import Course
from student.v2.serializers import (
    CreateBookingSerializer,
    ListLessonCourseSerializer,
    CourseRegistrationDetailSerializer,
    ListCourseSerializer,
    CourseDetailSerializer,
    CourseRegistrationSerializer,
    ListTeacherSerializer,
    ListCourseRegistrationSerializer,
    BookingDetailSerializer
)
from django.core.exceptions import ValidationError
from school.models import School, SchoolSettings
from core.serializers import ProfileSerializer
from internal.permissions import IsStudent
from utils.notification_utils import send_notification
from utils.gen_upcomming import generate_upcoming_private
from datetime import datetime, timedelta
import pytz
from django.utils import timezone
from datetime import timedelta

gmt7 = pytz.timezone('Asia/Bangkok')


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStudent])
def school_info(request):
    """
    Returns basic school information.
    """
    school = get_object_or_404(School, id=request.user.student.school.first().id)
    return Response({
        "school_name": school.name,
        "payment_qr_code": school.payment_qr_code.url if school.payment_qr_code else None,
        "location": school.location,
    })


class ProfileViewSet(ViewSet):
    """
    ViewSet to manage user profiles.
    """
    permission_classes = [IsAuthenticated, IsStudent]

    def retrieve(self, request):
        user = request.user
        ser = ProfileSerializer(instance=user)
        return Response(ser.data, status=200)

    def update(self, request):
        user = request.user
        ser = ProfileSerializer(data=request.data)
        if ser.is_valid():
            user = ser.update(user, ser.validated_data)
            return Response(status=200)
        return Response(ser.errors, status=400)

    def destroy(self, request):
        request.user.delete()
        return Response(status=204)


class TeacherViewSet(ViewSet):
    """
    ViewSet to manage teachers related to a student.
    """
    permission_classes = [IsAuthenticated, IsStudent]

    def list(self, request):
        user = request.user
        teachers = StudentTeacherRelation.objects.select_related("teacher__school", "teacher__user") \
            .filter(student__user_id=user.id).order_by("favorite_teacher")
        ser = ListTeacherSerializer(instance=teachers, many=True)
        return Response(ser.data, status=200)


class RegistrationViewSet(ViewSet):
    """
    ViewSet to manage course registrations.
    """
    permission_classes = [IsAuthenticated, IsStudent]

    def list(self, request):
        filters = {'student__user_id': request.user.id}

        teacher_uuid = request.GET.get("teacher_uuid")
        if teacher_uuid:
            teacher = get_object_or_404(Teacher, user__uuid=teacher_uuid)
            filters['teacher'] = teacher

        if request.GET.get("has_lesson_left") == "true":
            filters['lessons_left__gt'] = 0

        courses = CourseRegistration.objects.select_related("course").filter(**filters)
        ser = ListCourseRegistrationSerializer(instance=courses, many=True)
        return Response(ser.data, status=200)

    def retrieve(self, request, code):
        instance = get_object_or_404(
            CourseRegistration, uuid=code, student__user_id=request.user.id
        )
        ser = CourseRegistrationDetailSerializer(instance=instance)
        return Response(ser.data, status=200)

    def create(self, request):
        data = request.data.copy()
        data["student_id"] = request.user.student.id
        ser = CourseRegistrationSerializer(data=data)
        if ser.is_valid():
            obj = ser.save()
            # Fetch the CourseRegistration with prefetch_related for school admins and their user details
            regis = CourseRegistration.objects.prefetch_related(
                Prefetch(
                    "course__school__admins", 
                    queryset=Admin.objects.select_related("user"), 
                    to_attr='cached_admins')
            ).get(id=obj.id)

            # Notify all admins using the cached attribute
            for admin in regis.course.school.cached_admins:
                send_notification(
                    admin.user,
                    "New Course Registration",
                    f"A new course registration has been made by {request.user.first_name}. Please review and confirm the registration."
                )
            return Response({"registration_id": obj.uuid}, status=201)
        return Response(ser.errors, status=400)


class CourseViewSet(ViewSet):
    """
    ViewSet to list courses available for a student.
    """
    permission_classes = [IsAuthenticated, IsStudent]

    def list_group(self, request):
        # Get the student associated with the current user
        student = get_object_or_404(Student, user_id=request.user.id)

        # Determine is_group filter based on course_type
        is_group = True 

        # Filter courses based on school and is_group
        courses = Course.objects.filter(school_id__in=student.school.all(), is_group=is_group)

        # Serialize the results
        ser = ListCourseSerializer(instance=courses, many=True)
        return Response(ser.data, status=200)

    def list_private(self, request):
        # Get the student associated with the current user
        student = get_object_or_404(Student, user_id=request.user.id)

        # Determine is_group filter based on course_type
        is_group = False 

        # Filter courses based on school and is_group
        courses = Course.objects.filter(school_id__in=student.school.all(), is_group=is_group)

        # Serialize the results
        ser = ListCourseSerializer(instance=courses, many=True)
        return Response(ser.data, status=200)

    def retrieve(self, request, uuid):
        course = get_object_or_404(Course, uuid=uuid)
        ser = CourseDetailSerializer(instance=course)
        return Response(ser.data, status=200)


class LessonViewSet(ViewSet):
    """
    ViewSet to manage lessons and their bookings.
    """
    permission_classes = [IsAuthenticated, IsStudent]


    def list_private(self, request):
        student = request.user.student

        # Fetch the month and year from query parameters
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        filters = {}
        if start_date and end_date:
            try:
                start_date = timezone.datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
                end_date = timezone.datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
                filters["datetime__range"] = (start_date, end_date)
            except ValueError:
                return Response({"error": "Invalid start_date or end_date"}, status=400)

        # Fetch confirmed course registrations with their courses and teachers
        registered_courses = CourseRegistration.objects.select_related("course").prefetch_related(
             Prefetch('teacher', 
                queryset=Teacher.objects.prefetch_related(
                Prefetch('unavailable_once', to_attr='cached_unavailables'),
                Prefetch('lesson', queryset=Lesson.objects.filter(status__in=["CON", "PENTE"]),to_attr='cached_lessons'),
                Prefetch('course',
                    queryset=Course.objects.filter(is_group=False), to_attr='cached_courses'),
                Prefetch('available_time', to_attr='cached_available_times'),  # Prefetch available times
            ), to_attr='cached_teacher'),
        ).filter(
            student=student, payment_status="confirm", course__is_group=False
        )

        # Serialize and return the lessons
        lessons = generate_upcoming_private(student.school.first(), registered_courses)
        return Response(lessons, status=200)


    def list_course(self, request):
        student = request.user.student

        # Fetch the month and year from query parameters
        month = request.query_params.get("month")
        year = request.query_params.get("year")
        filters = {}
        if month and year:
            try:
                month = int(month)
                year = int(year)
                start_date = timezone.datetime(year, month, 1, tzinfo=timezone.utc)
                end_date = (start_date + timedelta(days=32)).replace(day=1)
                filters["datetime__range"] = (start_date, end_date)
            except ValueError:
                return Response({"error": "Invalid month or year"}, status=400)

        # Fetch confirmed course registrations with their courses and teachers
        registered_courses = CourseRegistration.objects.filter(
            student=student, payment_status="confirm", course__is_group=True
        ).values_list("course_id", flat=True)  # Extract only course IDs

        # Fetch already booked lesson IDs for the student
        booked_lessons = Booking.objects.filter(student=student).values_list('lesson_id', flat=True)

        # Filter lessons that match the registered courses, have number_of_client less than group_size, are not booked, and match the specified date range
        lessons = Lesson.objects.filter(
            course_id__in=registered_courses,  # Use __in for filtering multiple course IDs
            course__is_group=True,
            status="CON",
            number_of_client__lt=F('course__group_size'),  # Ensure number_of_client is less than group_size
            **filters,
            datetime__gte=datetime.now(),  # Ensure lessons are after or on today's date
        ).exclude(id__in=booked_lessons).select_related(
            "course__school", "teacher__user"
        )

        # Serialize and return the lessons
        ser = ListLessonCourseSerializer(instance=lessons, many=True)
        return Response(ser.data, status=200)


class BookingViewSet(ViewSet):
    """
    ViewSet to manage bookings.
    """
    permission_classes = [IsAuthenticated, IsStudent]

    VALID_STATUSES = {
        "pending": "PENTE",
        "upcoming": "CON",
        "complete": "COM"
    }

    def list(self, request):
        # Get the lesson status from query parameters
        lesson_status = request.query_params.get("status")
        student = request.user.student

        # Validate the lesson status query parameter
        if (lesson_status and lesson_status not in self.VALID_STATUSES):
            return Response(
                {"error": f"Invalid status value. Valid choices are: {', '.join(self.VALID_STATUSES.keys())}"},
                status=400
            )

        # Translate status to the corresponding value in VALID_STATUSES
        translated_status = self.VALID_STATUSES.get(lesson_status)

        # Apply filters
        filters = {"student": student}
        if translated_status:
            filters["status"] = "COM"
            filters["lesson__status"] = translated_status

        # Query and serialize bookings
        bookings = Booking.objects.filter(**filters).select_related("lesson__course", "lesson__teacher")
        ser = BookingDetailSerializer(instance=bookings, many=True)

        return Response(ser.data, status=200)
    
    def retrieve(self, request, code):
        student = request.user.student

        # Get the booking object
        booking = get_object_or_404(
            Booking.objects.select_related("lesson__course__school", "lesson__teacher"),
            code=code,
            student=student
        )

        # Serialize and return the response
        ser = BookingDetailSerializer(instance=booking)
        return Response(ser.data, status=200)

    def create(self, request):
        registration_uuid = request.data.get("registration_uuid")
        if not registration_uuid:
            return Response({"error": "Registration UUID is required."}, status=400)
        user_id = request.user.id
        registration = get_object_or_404(
            CourseRegistration,
            uuid=registration_uuid,
            student__user_id=user_id,
            payment_status="confirm",
        )

        # Fetch lesson data from request body
        lesson_data = request.data.get("lesson")
        if not lesson_data:
            return Response({"error": "Lesson data is required."}, status=400)

        # If the course is not a group course, create a new lesson
        if not registration.course.is_group:
            # Validate datetime
            try:
                booking_datetime = lesson_data.get("datetime")
                lesson_datetime = timezone.datetime.fromisoformat(booking_datetime
                )
            except (TypeError, ValueError):
                return Response({"error": "Invalid datetime format."}, status=400)

            try:
                lesson = Lesson.objects.create(
                    code=Lesson()._generate_unique_code(12),
                    datetime=lesson_datetime,
                    end_datetime=lesson_datetime + timedelta(hours=1),
                    status="PENTE",
                    course=registration.course,
                    teacher=registration.teacher,
                    number_of_client=1,
                )
            except ValidationError as e:
                return Response({"error": str(e)}, status=400)
        else:
            # Fetch the lesson using the provided code and conditions
            code = request.data.get("lesson_code")
            lesson = get_object_or_404(
                Lesson.objects.select_related('course', 'teacher').filter(
                    Q(course__is_group=True, status="CON"),
                    code=code,
                )
            )
            if registration.course_id != lesson.course_id:
                return Response({"error": "The registration course couldn't be used for this course."}, status=400)
            # Check if the lesson is a group course and validate group size
            if lesson.course.is_group and lesson.number_of_client >= lesson.course.group_size:
                return Response({"error": "This lesson has reached the maximum number of clients."}, status=400)
            
        # Prepare booking data
        data = {
            "user_type": request.data.get("user_type"),
            "registration_id": registration.id,
            "student_id": registration.student.id,
            "lesson_id": lesson.id,
        }

        # Validate and save the booking
        ser = CreateBookingSerializer(data=data)
        if ser.is_valid():
            ser.save(lesson=lesson)
            if lesson.course.is_group:
                lesson.number_of_client += 1  # Update client count only for group courses
                lesson.status = "CON"
            lesson.save()
            send_notification(lesson.teacher.user, "New Booking Alert", f"{request.user.first_name} has booked a class with you. Check your schedule for details.")
            return Response({"message": "Booking created successfully."}, status=201)

        # Return validation errors if the serializer is invalid
        return Response(ser.errors, status=400)

    def cancel(self, request, code):
        student = request.user.student

        # Get the booking object
        booking = get_object_or_404(    
            Booking.objects.select_related("lesson"),
            code=code,
            student=student
        )

        # Check if the booking can be canceled
        if booking.lesson.status not in ["PENTE", "CON"]:
            return Response({"error": "Only pending or confirmed bookings can be canceled."}, status=400)

        # Update the booking and lesson status
        booking.status = "CAN"
        booking.save()

        lesson = booking.lesson
        lesson.number_of_client -= 1
        if not lesson.course.is_group:
            lesson.status = "CAN"
        lesson.save()

        settings = SchoolSettings.objects.select_related("settings").get(school_id=student.school.first().id)
        cancel_b4_hours = settings.cancel_b4_hours
        if lesson.datetime - timedelta(hours=cancel_b4_hours) < timezone.now():
            if booking.registration.lessons_left > 0:  # Prevent negative balance
                booking.registration.lessons_left -= 1
                booking.registration.save()
        send_notification(lesson.teacher.user, "Class Cancellation", f"{request.user.first_name} has canceled a class with you. Check your schedule for details.")

        return Response({"message": "Booking canceled successfully."}, status=200)
