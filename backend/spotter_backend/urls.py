"""URL configuration for spotter_backend project."""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("trip.urls")),
    path("api/whatsapp/", include("whatsapp.urls")),
]
