from rest_framework import permissions


class IsTeacher(permissions.BasePermission):
    """
    Permission check for teacher users.
    """
    message = "You must be a teacher to access this resource."

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'teacher'
        )


class IsTeacherOrAdmin(permissions.BasePermission):
    """
    Permission check for teacher or admin users.
    """
    message = "You must be a teacher or admin to access this resource."

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ['teacher', 'admin']
        )


class IsTeacherProfileOwner(permissions.BasePermission):
    """
    Permission to check if the user owns the teacher profile.
    """
    message = "You can only access your own teacher profile."

    def has_object_permission(self, request, view, obj):
        # obj is TeacherProfile
        return obj.user == request.user


class CanAccessCourse(permissions.BasePermission):
    """
    Permission to check if teacher is assigned to the course.
    """
    message = "You are not assigned to this course."

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        if request.user.role == 'teacher':
            try:
                teacher_profile = request.user.teacher_profile
                return obj in teacher_profile.assigned_courses.all()
            except:
                return False
        return False
