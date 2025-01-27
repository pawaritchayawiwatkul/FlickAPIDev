from django.urls import path
from .views import (
    school_info,
    ProfileViewSet,
    TeacherViewSet,
    RegistrationViewSet,
    CourseViewSet,
    LessonViewSet,
    BookingViewSet,
)

urlpatterns = [
    # Function-based view
    path("school-info/", school_info, name="school_info"),

    # Profile routes
    path("profile/", ProfileViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}), name="profile"),
    
    # Teacher routes
    path("teachers/", TeacherViewSet.as_view({"get": "list"}), name="teacher-list"),

    # Registration routes
    path("registrations", RegistrationViewSet.as_view({"get": "list", "post": "create"}), name="registration-list"),
    path("registrations/<slug:code>", RegistrationViewSet.as_view({"get": "retrieve"}), name="registration-retrieve"),

    # Course routes
    path("courses/private", CourseViewSet.as_view({"get": "list_private"}), name="course-list"),
    path("courses/group", CourseViewSet.as_view({"get": "list_group"}), name="course-list"),
    path("courses/<slug:uuid>", CourseViewSet.as_view({"get": "retrieve"}), name="course-list"),

    # Lesson routes
    path("lessons/list-private", LessonViewSet.as_view({"get": "list_private"}), name="lesson-list"),
    path("lessons/list-course", LessonViewSet.as_view({"get": "list_course"}), name="lesson-list"),

    # Booking routes
    path("bookings/", BookingViewSet.as_view({"get": "list"}), name="booking-list"),
    path("bookings/<slug:code>", BookingViewSet.as_view({ "post": "create"}), name="booking-create"),
]