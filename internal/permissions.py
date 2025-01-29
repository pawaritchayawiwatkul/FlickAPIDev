from rest_framework.permissions import BasePermission

class IsTeacher(BasePermission):
    """
    Custom permission to allow access only to teachers.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_teacher

    def has_object_permission(self, request, view, obj):
        return request.user.is_teacher


class IsManager(BasePermission):
    """
    Custom permission to allow access only to managers.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_manager

    def has_object_permission(self, request, view, obj):
        return request.user.is_manager


class IsStudent(BasePermission):
    """
    Custom permission to allow access only to students.
    A student is defined as a user who is NOT a teacher and NOT a manager.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            not request.user.is_teacher and 
            not request.user.is_manager
        )

    def has_object_permission(self, request, view, obj):
        return (
            request.user.is_authenticated and 
            not request.user.is_teacher and 
            not request.user.is_manager
        )