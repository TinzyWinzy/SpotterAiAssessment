from django.urls import path
from . import views

urlpatterns = [
    path("trip/", views.trip_plan),
    path("health/", views.health),
]
