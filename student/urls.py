from django.urls import path , re_path
from student import views
from rest_framework.urlpatterns import format_suffix_patterns

app_name = 'student'

courseView = views.CourseViewset.as_view({
    'get': 'list',
})

courseDetailView = views.CourseViewset.as_view({
    'get': 'retrieve',
})

courseFavoriteView = views.CourseViewset.as_view({
    'put': 'favorite'
})
courseATview = views.CourseViewset.as_view({
    'get': 'get_available_time',
})

lessonView = views.LessonViewset.as_view({
    'post': 'create'
})

lessonDayView = views.LessonViewset.as_view({
    'get': 'day',
})

lessonWeekView = views.LessonViewset.as_view({
    'get': 'week',
})

lessonRecentView = views.LessonViewset.as_view({
    'get': 'recent',
})

lessonStatusView = views.LessonViewset.as_view({
    'get': 'status',
})

lessonCancelView = views.LessonViewset.as_view({
    'put': 'cancel',
})

lessonConfirmView = views.LessonViewset.as_view({
    'put': 'confirm',
})

teacherListView = views.TeacherViewset.as_view({
    'get': 'list',
})

teacherFavView = views.TeacherViewset.as_view({
    'put': 'favorite',
})

profileView = views.ProfileViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'delete': 'destroy'
})

profileAddView = views.ProfileViewSet.as_view({
    'post': 'add'
})

guestBookingView = views.GuestViewset.as_view({
    'get': 'booking_screen',
    'post': 'create_guest_lesson'
})

guestGetAvailable = views.GuestViewset.as_view({
    'get': "get_available_time"
})
# Enter URL path below
urlpatterns = format_suffix_patterns([
    path('profile/', profileView, name='profile'),
    path('profile/add/<slug:teacher_uuid>', profileAddView, name='profile-add'),

    path('course/', courseView, name='course'),
    path('course/<slug:code>/', courseDetailView, name='course-detail'),
    path('course/<slug:code>/availabletime', courseATview, name='course-available-time'),
    path('course/<slug:code>/favorite', courseFavoriteView, name='course-fav'),

    path('lesson/', lessonView, name='lesson'),
    path('lesson/status/<slug:status>', lessonStatusView, name='lesson'),
    path('lesson/day', lessonDayView, name='lesson-day'),
    path('lesson/week', lessonWeekView, name='lesson-week'),
    path('lesson/recent', lessonRecentView, name='lesson-recent'),
    path('lesson/<slug:code>/cancel', lessonCancelView, name='course-detail'),
    path('lesson/<slug:code>/confirm', lessonConfirmView, name='course-detail'),

    path('guest/<slug:code>', guestBookingView, name='makeup-lesson'),
    path('guest/<slug:code>/availability', guestGetAvailable, name='makeup-lesson'),

    path('teacher/', teacherListView, name='lesson-day'),
    path('teacher/<slug:code>/favorite', teacherFavView, name='lesson-fav'),

])