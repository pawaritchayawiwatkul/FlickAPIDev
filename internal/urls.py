"""
URL configuration for natural_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.urls import path, include
from core.views import DeviceViewSet

urlpatterns = [
    path('admin/', admin.site.urls),
    path('manager/', include('manager.urls', namespace='manager')),
    path('student/', include('student.urls', namespace='student')),
    path('teacher/', include('teacher.urls', namespace='teacher')),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    path('auth/', include('core.urls')),
    path('calendar/', include('googlecalendar.urls')),

    path('devices', DeviceViewSet.as_view({'delete': 'remove', 'post': 'create'}), name='create_fcm_device'),
    path('notification', DeviceViewSet.as_view({'put': 'update'}), name='create_fcm_device'),

    path("__debug__/", include("debug_toolbar.urls")),
]

# if settings.DEBUG:
#     urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)