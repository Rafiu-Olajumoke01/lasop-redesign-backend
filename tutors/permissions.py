# tutors/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdmin(BasePermission):
    """Full admin access. Assumes User.is_staff marks LASOP admins."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsTutor(BasePermission):
    """Logged-in user has a Tutor profile."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "tutor_profile")
        )


class IsAdminOrTutor(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return user.is_staff or hasattr(user, "tutor_profile")


class IsOwnCohortTutor(BasePermission):
    """
    For cohort-nested endpoints (attendance, class-session, assignments):
    admin can do anything, tutor can only act on cohorts assigned to them.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff:
            return True
        if hasattr(user, "tutor_profile"):
            return getattr(obj, "tutor_id", None) == user.tutor_profile.id
        return False