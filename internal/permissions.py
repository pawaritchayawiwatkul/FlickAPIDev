from rest_framework.permissions import BasePermission
from student.models import Student

class IsStudent(BasePermission):
    """
    Custom permission to allow access only to students.
    """

    def has_permission(self, request, view):
        # Check if the user is authenticated and has a related Student object
        return request.user.is_authenticated and hasattr(request.user, "student")

    def has_object_permission(self, request, view, obj):
        # Optionally enforce object-level permissions (e.g., ownership)
        # Ensure the student has access to the object
        if hasattr(request.user, "student"):
            if hasattr(obj, "student"):
                return obj.student == request.user.student
            # If the object is not directly linked to a student, grant access
            return True
        return False