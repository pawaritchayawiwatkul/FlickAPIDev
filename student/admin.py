# Register your models here.
from django.contrib import admin
from .models import CourseRegistration, Student, StudentTeacherRelation

# Register your models here.
# admin.site.register(ProfilePicture)
admin.site.register(Student)

@admin.register(CourseRegistration)
class CourseRegistrationAdmin(admin.ModelAdmin):
    list_display = ('registered_date', 'course', 'student', 'teacher', 'lessons_left')
    search_fields = ( 'course', 'student', 'teacher',)
    list_filter = ('course', 'student', 'teacher')


class StudentTeacherRelationAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'teacher',
        'favorite_teacher',
        'favorite_student',
        'student_first_name',
        'student_last_name',
        'student_color'
    )
    list_filter = ('favorite_teacher', 'favorite_student', 'student_color')
    search_fields = (
        'student__user__first_name',
        'student__user__last_name',
        'teacher__user__first_name',
        'teacher__user__last_name'
    )
    ordering = ('student__user__first_name', 'teacher__user__first_name')
    fieldsets = (
        ('Relation Details', {
            'fields': ('student', 'teacher', 'favorite_teacher', 'favorite_student')
        }),
        ('Student Info', {
            'fields': ('student_first_name', 'student_last_name', 'student_color')
        }),
    )
    readonly_fields = ('student_first_name', 'student_last_name')

# Register the StudentTeacherRelation model with the admin site
admin.site.register(StudentTeacherRelation, StudentTeacherRelationAdmin)