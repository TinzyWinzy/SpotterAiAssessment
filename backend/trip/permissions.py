"""Custom DRF permission classes and helpers for organisation isolation."""
from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import Organisation


def get_user_organisation(user):
    """Resolve the organisation for a given user.

    Checks UserProfile first, falls back to Driver profile, then default org.
    """
    if hasattr(user, "profile") and user.profile.organisation_id:
        return user.profile.organisation
    if hasattr(user, "driver_profile") and user.driver_profile and user.driver_profile.organisation_id:
        return user.driver_profile.organisation
    return None


def scope_organisation(qs, user, org_field="organisation"):
    """Filter a queryset to the user's organisation."""
    org = get_user_organisation(user)
    if org is None:
        return qs.none()
    if user.is_staff:
        return qs
    return qs.filter(**{org_field: org})


def belongs_to_organisation(obj, user):
    """Check if an object belongs to the user's organisation."""
    if user.is_staff:
        return True
    org = get_user_organisation(user)
    if org is None:
        return False
    obj_org = getattr(obj, "organisation", None)
    if obj_org is None:
        obj_org = getattr(obj, "organisation_id", None)
    return obj_org == org


VALID_STATUS_TRANSITIONS = {
    "inquiry": ["quoted", "cancelled"],
    "quoted": ["confirmed", "cancelled"],
    "confirmed": ["assigned", "cancelled"],
    "assigned": ["dispatched", "cancelled"],
    "dispatched": ["at_border", "cancelled"],
    "at_border": ["in_transit", "cancelled"],
    "in_transit": ["delivered", "cancelled"],
    "delivered": ["paid"],
    "paid": [],
    "cancelled": [],
}


def validate_status_transition(old_status, new_status):
    """Return True if the status transition is valid."""
    allowed = VALID_STATUS_TRANSITIONS.get(old_status, [])
    return new_status in allowed


class IsAdmin(BasePermission):
    """Allow only Django staff/admin users (fleet owner)."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)



class IsOwnerOrReadOnly(BasePermission):
    """Allow staff users full access; others read-only."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_staff


class IsInOrganisation(BasePermission):
    """Allow access only if user belongs to the same org as the object."""

    def has_object_permission(self, request, view, obj):
        return belongs_to_organisation(obj, request.user)
