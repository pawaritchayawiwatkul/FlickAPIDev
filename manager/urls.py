from django.urls import path , re_path
from manager import views
from rest_framework.urlpatterns import format_suffix_patterns

app_name = 'manager'

insightViewSet = views.InsightViewSet.as_view({
    'get': 'retrieve'
})

calendarViewSet = views.CalendarViewSet.as_view({
    'get': "month"
})

registrationViewSet = views.CourseRegistrationViewSet.as_view({
    'get': "list"
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

clientViewSet = views.ClientViewSet.as_view({
    'get': "list",
    "post": "create"
})

clientDetailViewSet = views.ClientViewSet.as_view({
    "put": "edit",
    "get": "retrieve"
})

clientRegistrationViewSet = views.RegistrationViewset.as_view({
    'get': "list",
    'post': 'create'
})

courseViewSet = views.CourseViewset.as_view({
    'get': 'list',
    'post': 'create'
})

# Enter URL path below
urlpatterns = format_suffix_patterns([
    path('insight', insightViewSet, name='insight'),

    path('calendar/month', calendarViewSet, name='profile-add'),
    path('purchase', registrationViewSet, name='purchase'),

    path('staff', staffViewSet, name='staff-list'),
    path('staff/<slug:uuid>', staffDetailViewSet, name='staff-detail'),
    path('staff/<slug:uuid>/client', staffClientViewSet, name='staff-client'),

    path('client', clientViewSet, name='client'),
    path('client/<slug:uuid>', clientDetailViewSet, name='client-detail'),
    path('client/<slug:uuid>/registration', clientRegistrationViewSet, name='client-registration'),

    path('course', courseViewSet, name='course'),
])
