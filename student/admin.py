# Register your models here.
from django.contrib import admin
from .models import CourseRegistration, Student, StudentTeacherRelation, Booking

# Register your models here.
# admin.site.register(ProfilePicture)
admin.site.register(Student)

@admin.register(CourseRegistration)
class CourseRegistrationAdmin(admin.ModelAdmin):
    list_display = ('registered_date', 'course', 'student', 'teacher', 'lessons_left')
    search_fields = ( 'course', 'student', 'teacher',)
    list_filter = ('course', 'student', 'teacher')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('code', 'lesson', 'student', 'guest', 'user_type', 'booked_datetime', 'status')
    search_fields = ('code', 'lesson__code', 'student__user__first_name', 'guest__name')
    list_filter = ('status', 'user_type')
    ordering = ('-booked_datetime',)