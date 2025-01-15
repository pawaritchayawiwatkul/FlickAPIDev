# Register your models here.
from django.contrib import admin
from .models import CourseRegistration, Student, Lesson

# Register your models here.
# admin.site.register(ProfilePicture)
admin.site.register(Student)

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('registration', 'booked_datetime', 'status', 'notes')
    search_fields = ( 'registration',)
    list_filter = ('registration__student', 'registration__lesson',)

@admin.register(CourseRegistration)
class CourseRegistrationAdmin(admin.ModelAdmin):
    list_display = ('registered_date', 'course', 'student', 'teacher', 'used_lessons')
    search_fields = ( 'course', 'student', 'teacher',)
    list_filter = ('course', 'student', 'teacher', 'status')