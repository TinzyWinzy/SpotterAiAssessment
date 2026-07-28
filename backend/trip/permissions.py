"""Custom DRF permission classes for TruckLedger roles."""
from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Allow only Django staff/admin users (fleet owner)."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsAuthenticated(BasePermission):
    """Allow any authenticated user."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsOwnerOrReadOnly(BasePermission):
    """Allow staff users full access; others read-only."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.is_staff
