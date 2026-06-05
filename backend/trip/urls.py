"""URL routes for the trip app."""
from django.urls import path
from . import views, auth_views, admin_views

urlpatterns = [
    path("health/", views.health),
    path("trip/", views.trip_plan),
    path("drivers/", views.drivers_list),
    path("drivers/<int:pk>/", views.driver_detail),
    path("drivers/<int:pk>/history/", views.driver_add_history),
    path("auth/register/", auth_views.register),
    path("auth/login/", auth_views.login_view),
    path("auth/logout/", auth_views.logout_view),
    path("auth/me/", auth_views.me),
    path("admin/metrics/", admin_views.metrics),
    path("admin/trips/", admin_views.trips_list),
]
