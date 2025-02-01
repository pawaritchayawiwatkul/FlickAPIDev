from django.contrib import admin
from teacher.models import Teacher, UnavailableTimeOneTime, UnavailableTimeRegular, Lesson

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('user', 'school')
    search_fields = ('user__first_name', 'school__name')

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'course',
        'teacher',
        'datetime',
        'status',
        'number_of_client',
        'notified'
    )
    list_filter = ('status', 'course', 'teacher', 'notified', 'datetime')
    search_fields = ('code', 'course__name', 'teacher__user__first_name', 'teacher__user__last_name')
    ordering = ('-datetime',)
    readonly_fields = ('code', 'number_of_client')
    fieldsets = (
        ('Lesson Details', {
            'fields': ('code', 'course', 'teacher', 'status', 'datetime', 'number_of_client')
        }),
        ('Notification & Events', {
            'fields': ('notified', 'student_event_id', 'teacher_event_id')
        }),
    )

@admin.register(UnavailableTimeOneTime)
class UnavailableTimeOneTimeAdmin(admin.ModelAdmin):
    list_display = ('date', 'start', 'stop', 'teacher')
    search_fields = ('teacher__user__first_name', 'teacher__user__last_name')
    list_filter = ('date',)

@admin.register(UnavailableTimeRegular)
class UnavailableTimeRegularAdmin(admin.ModelAdmin):
    list_display = ('day', 'start', 'stop', 'teacher')
    search_fields = ('teacher__user__first_name', 'teacher__user__last_name')
    list_filter = ('day',)
