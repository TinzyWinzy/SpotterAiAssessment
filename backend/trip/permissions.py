"""Custom DRF permission classes."""
from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Allow only Django staff/admin users."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
