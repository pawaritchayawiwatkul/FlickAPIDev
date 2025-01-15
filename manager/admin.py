from django.contrib import admin
from .models import Admin

# Customize the admin display for the Admin model
@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    # Fields to display in the admin list view
    list_display = ('id', 'user', 'school')
    # Fields to search by in the admin interface
    search_fields = ('user__username', 'user__email', 'school__name')
    # Fields that allow filtering in the admin interface
    list_filter = ('school',)
    # Fields to display in the detail view
    fields = ('user', 'school')
    # Read-only fields
    readonly_fields = ('id',)