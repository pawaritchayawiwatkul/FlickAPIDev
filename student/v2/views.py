from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.db.models import Q
from functools import reduce
from operator import or_

from student.models import CourseRegistration, Student, StudentTeacherRelation, Booking
from teacher.models import Teacher, Lesson
from school.models import Course
from student.v2.serializers import (
    CreateBookingSerializer,
    ListBookingSerializer,
    ListLessonCourseSerializer,
    CourseRegistrationDetailSerializer,
    ListCourseSerializer,
    CourseDetailSerializer,
    CourseRegistrationSerializer,
    ListTeacherSerializer,
    ListCourseRegistrationSerializer,
    ListLessonPrivateSerializer,
    BookingDetailSerializer
)
from school.models import School
from core.serializers import ProfileSerializer
from internal.permissions import IsStudent
from uuid import UUID
from datetime import datetime
import pytz

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

        # Fetch confirmed course registrations with their courses and teachers
        registered_courses = CourseRegistration.objects.filter(
            student=student, payment_status="confirm", course__is_group=False
        )

        # Collect valid course and teacher pairs
        course_teacher_pairs = registered_courses.values_list("course_id", "teacher_id")

        # Create a list of Q objects for OR filtering
        conditions = [Q(course_id=course, teacher_id=teacher) for course, teacher in course_teacher_pairs]
        
        if not conditions:
            return Response([], status=200)
        
        # Combine all Q objects with OR using reduce
        combined_conditions = reduce(or_, conditions) 

        # Filter lessons that match the combined conditions
        lessons = Lesson.objects.filter(
            combined_conditions,
            course__is_group=False,
            status="AVA",
            datetime__lte=datetime.now(gmt7)  # Ensure lessons are before or on today's date
        ).select_related(
            "course__school", "teacher__user"
        )

        # Serialize and return the lessons
        ser = ListLessonPrivateSerializer(instance=lessons, many=True)
        return Response(ser.data, status=200)


    def list_course(self, request):
        student = request.user.student

        # Fetch confirmed course registrations with their courses and teachers
        registered_courses = CourseRegistration.objects.filter(
            student=student, payment_status="confirm", course__is_group=True
        ).values_list("course_id", flat=True)  # Extract only course IDs

        # Filter lessons that match the registered courses
        lessons = Lesson.objects.filter(
            course_id__in=registered_courses,  # Use __in for filtering multiple course IDs
            course__is_group=True,
            status="AVA",
            datetime__lte=datetime.now(gmt7)  # Ensure lessons are before or on today's date
        ).select_related(
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
        if lesson_status and lesson_status not in self.VALID_STATUSES:
            raise ValidationError(
                {"status": f"Invalid status value. Valid choices are: {', '.join(self.VALID_STATUSES.keys())}"}
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
        # ser = ListBookingSerializer(instance=bookings, many=True)

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

    def create(self, request, code):
        student = request.user.student

        # Fetch the lesson using the provided code and conditions
        lesson = get_object_or_404(
            Lesson.objects.select_related('course', 'teacher').filter(
                Q(course__is_group=True, status="CON") | Q(course__is_group=False, status="AVA"),
                code=code
            )
        )

        # Check if the lesson is a group course and validate group size
        if lesson.course.is_group and lesson.number_of_client >= lesson.course.group_size:
            return Response({"error": "This lesson has reached the maximum number of clients."}, status=400)
        

        # Fetch course registration based on the provided UUIDs
        filter_conditions = {
            "course_id": lesson.course.id,
            "student": student,
            "payment_status": "confirm",
        }

        # If the course is not a group course, add the specific teacher condition
        if not lesson.course.is_group:
            filter_conditions["teacher_id"] = lesson.teacher.id

        # Fetch the first matching course registration
        registration = CourseRegistration.objects.filter(**filter_conditions).first()

        # Check if a valid registration exists
        if not registration:
            return Response({"error": "No course registration found for the provided instructor and course."}, status=404)


        # Validate if the registration course matches the lesson course
        if registration.course_id != lesson.course_id:
            return Response({"error": "The registration course couldn't be used for this course."}, status=400)

        # Validate teacher match only for private courses
        if not lesson.course.is_group and registration.teacher_id != lesson.teacher_id:
            return Response({"error": "The registration course couldn't be used for this course."}, status=400)

        # Determine the booking status based on whether the course is a group class

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
            lesson.number_of_client += 1  # Update client count only for group courses
            lesson.status = "CON" if lesson.course.is_group else "PENTE"
            lesson.save()
            return Response({"message": "Booking created successfully."}, status=201)

        # Return validation errors if the serializer is invalid
        return Response(ser.errors, status=400)