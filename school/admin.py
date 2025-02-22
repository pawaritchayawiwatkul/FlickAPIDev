# Register your models here.
from django.contrib import admin
from .models import School, Course, SchoolSettings, Facilities

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', )

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'number_of_lessons', 'duration')
    search_fields = ('name',)
    list_filter = ('school',)

@admin.register(SchoolSettings)
class SchoolSettingsAdmin(admin.ModelAdmin):
    list_display = ('days_ahead', 'interval', 'cancel_b4_hours', 'teacher_break')

@admin.register(Facilities)
class FacilitiesAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity', 'school')
    search_fields = ('name',)
    list_filter = ('school',)
