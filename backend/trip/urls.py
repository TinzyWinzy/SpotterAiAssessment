"""URL routes."""
from django.urls import path
from . import views, auth_views, admin_views

urlpatterns = [
    path("health/", views.health),
    # Admin trip planning
    path("trip/", views.trip_plan),
    path("trip/estimate/", views.trip_estimate),
    path("trips/", views.trips_list),
    path("trips/<int:pk>/", views.trip_detail),
    path("trips/<int:pk>/status/", views.trip_update_status),
    path("trips/<int:pk>/positions/", views.trip_positions),
    path("trips/<int:pk>/sos/", views.trip_sos),
    path("trips/<int:pk>/sos/acknowledge/", views.trip_sos_acknowledge),
    # Admin CRUD
    path("drivers/", views.drivers_list),
    path("drivers/<int:pk>/", views.driver_detail),
    path("vehicles/", views.vehicles_list),
    path("vehicles/<int:pk>/", views.vehicle_detail),
    path("fuel/", views.fuel_list),
    path("commodities/", views.commodity_list),
    path("commodity-categories/", views.commodity_categories),
    # Admin booking operations
    path("bookings/", views.bookings_list),
    path("bookings/<int:pk>/assign/", views.booking_assign),
    path("bookings/<int:pk>/images/", views.booking_images),
    # Public booking endpoints
    path("public/quote/", views.public_quote),
    path("public/book/", views.public_book),
    path("public/book/<str:ref>/", views.public_booking_lookup),
    path("public/book/<str:ref>/confirm/", views.public_booking_confirm),
    path("public/track/<str:ref>/", views.public_track),
    # Services
    path("services/", views.service_types_list),
    # Auth
    path("auth/register/", auth_views.register),
    path("auth/login/", auth_views.login_view),
    path("auth/logout/", auth_views.logout_view),
    path("auth/me/", auth_views.me),
    # Admin
    path("admin/metrics/", admin_views.metrics),
    path("admin/trips/", admin_views.trips_list),
    path("admin/summary/", admin_views.fleet_summary_text),
    path("admin/active-trips/", admin_views.active_trips),
]
