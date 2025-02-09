from django.urls import path , re_path
from manager import views
from rest_framework.urlpatterns import format_suffix_patterns

app_name = 'manager'

insightViewSet = views.InsightViewSet.as_view({
    'get': 'retrieve'
})

lessonViewSet = views.LessonViewSet.as_view({
    'get': "list",
    'post': 'create'

})

lessonCancelViewSet = views.LessonViewSet.as_view({
    'put': 'cancel'
})

registrationViewSet = views.CourseRegistrationViewSet.as_view({
    'get': "list"
})

paymentViewset = views.CourseRegistrationViewSet.as_view({
    'put': "payment_validation"
})

staffViewSet = views.StaffViewSet.as_view({
    'get': "list",
    "post": "create"
})

staffDetailViewSet = views.StaffViewSet.as_view({
    'get': "retrieve",
    "put": 'edit'
})

staffClientViewSet = views.StaffViewSet.as_view({
    'get': "client"
})

availableTimeViewSet = views.AvailableTimeViewSet.as_view({
    'get': 'list',
    'put': 'bulk_manage'
})


clientViewSet = views.ClientViewSet.as_view({
    'get': "list",
    "post": "create"
})

clientDetailViewSet = views.ClientViewSet.as_view({
    "put": "edit",
    "get": "retrieve"
})

clientRegistrationViewSet = views.ClientViewSet.as_view({
    'get': "list_registration",
    'post': 'create_registration'
})

courseViewSet = views.CourseViewset.as_view({
    'get': 'list',
    'post': 'create'
})

bookingViewSet = views.BookingViewSet.as_view({
    'put': 'check_in',
})

bookingCheckOutViewSet = views.BookingViewSet.as_view({
    'put': 'check_out',
})

bookingClearViewSet = views.BookingViewSet.as_view({
    'put': 'clear',
})

profileViewSet = views.ProfileViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'delete': 'destroy'
})

# Enter URL path below
urlpatterns = format_suffix_patterns([
    path('insight', insightViewSet, name='insight'),

    path('lesson', lessonViewSet, name='profile-add'),
    path('lesson/<slug:code>/cancel', lessonCancelViewSet, name='lesson-cancel'),

    path('purchase', registrationViewSet, name='purchase'),
    path('purchase/<slug:uuid>/payment-validation', paymentViewset, name='purchase'),

    path('staff', staffViewSet, name='staff-list'),
    path('staff/<slug:uuid>', staffDetailViewSet, name='staff-detail'),
    path('staff/<slug:uuid>/client', staffClientViewSet, name='staff-client'),
    path('staff/<slug:uuid>/available-time', availableTimeViewSet, name='client-registration'),

    path('client', clientViewSet, name='client'),
    path('client/<slug:uuid>', clientDetailViewSet, name='client-detail'),
    path('client/<slug:uuid>/registration', clientRegistrationViewSet, name='client-registration'),

    path('course', courseViewSet, name='course'),

    path('booking/<slug:code>/clear', bookingClearViewSet, name='booking-check-in'),
    path('booking/<slug:code>/check-in', bookingViewSet, name='booking-check-in'),
    path('booking/<slug:code>/check-out', bookingCheckOutViewSet, name='booking-check-out'),

    path('profile', profileViewSet, name='profile'),  # Add this line
])
