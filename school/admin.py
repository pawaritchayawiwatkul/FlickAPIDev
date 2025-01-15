# Register your models here.
from django.contrib import admin
from .models import School, Course

# Register your models here.
@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'number_of_teachers')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'number_of_lessons', 'duration')
    search_fields = ('name',)
    list_filter = ('school',)