from django.urls import path

from .views import (
    CourseViewset,
    ProfileViewSet,
    StudentViewSet,
    RegistrationViewset,
    LessonViewset,
    UnavailableTimeViewSet,
    get_availables
)

app_name = 'teacher'


urlpatterns = [
    # Course endpoints
    path('get-available/', get_availables, name='get-available'),
    path('courses/', CourseViewset.as_view({'get': 'list', 'post': 'create'}), name='course-list-create'),
    path('courses/<uuid:uuid>', CourseViewset.as_view({'get': 'retrieve', 'put': 'edit'}), name='course-detail'),

    # Profile endpoints
    path('profile/', ProfileViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='profile'),

    # Student endpoints
    path('students/', StudentViewSet.as_view({'get': 'list', 'post': 'create'}), name='student-list-create'),
    path('students/<uuid:uuid>/', StudentViewSet.as_view({'put': 'update'}), name='student-detail'),
    path('students/<uuid:uuid>/bookings', StudentViewSet.as_view({'get': 'list_bookings'}), name='student-detail'),
    path('students/<uuid:uuid>/purchases', StudentViewSet.as_view({'get': 'list_purchases'}), name='student-detail'),

    # Registration endpoints
    path('registrations/', RegistrationViewset.as_view({'get': 'list', 'post': 'create'}), name='registration-list-create'),
    path('registrations/simple/', RegistrationViewset.as_view({'get': 'simple_list'}), name='registration-simple-list'),
    path('registrations/<uuid:code>/', RegistrationViewset.as_view({'get': 'retrieve'}), name='registration-detail'),

    # Lesson endpoints
    path('lessons/', LessonViewset.as_view({'get': 'list', 'post': 'create'}), name='lesson-list'),
    path('lessons/<str:code>', LessonViewset.as_view({'get': 'retrieve'}), name='lesson-retrieve'),

    path('lessons/<str:code>/cancel/', LessonViewset.as_view({'put': 'cancel'}), name='lesson-cancel'),
    path('lessons/<str:code>/confirm/', LessonViewset.as_view({'put': 'confirm'}), name='lesson-confirm'),

    # Unavailable Time endpoints
    path('unavailable/', UnavailableTimeViewSet.as_view({'get': 'list', 'post': 'create_onetime'}), name='unavailable-list'),
    # path('unavailable/onetime', UnavailableTimeViewSet.as_view({'post': 'create_onetime',}), name='unavailable-onetime'),
    path('unavailable/<slug:code>', UnavailableTimeViewSet.as_view({'delete': 'remove'}), name='unavailable-remove'),
]