"""WhatsApp message intent router and handlers."""
from __future__ import annotations

import logging
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from trip.models import Trip, TripPosition, TripStatusLog, Driver
from trip.notifications import send_trip_status_sms
from .models import WhatsAppSession
from . import messages

logger = logging.getLogger(__name__)

VALID_STATUS_TRANSITIONS = {
    "dispatched": ["at_border"],
    "at_border": ["in_transit"],
    "in_transit": ["delivered"],
    "delivered": [],
    "paid": [],
    "cancelled": [],
}


def get_or_create_session(phone: str) -> WhatsAppSession:
    session, _ = WhatsAppSession.objects.get_or_create(phone_number=phone)
    return session


def find_active_trip(driver: Driver) -> Trip | None:
    return Trip.objects.filter(
        driver=driver,
        status__in=["dispatched", "at_border", "in_transit"],
    ).first()


def handle_incoming(phone: str, body: str, lat: float | None = None, lon: float | None = None) -> str:
    """Route an incoming WhatsApp message to the right handler."""
    session = get_or_create_session(phone)

    try:
        driver = Driver.objects.filter(phone_number=phone).first()

        if lat is not None and lon is not None:
            return handle_location(phone, lat, lon, driver, session)

        text = body.strip().upper()
        known_keywords = {
            "ACCEPT": handle_accept,
            "REJECT": handle_reject,
            "STATUS": handle_status,
            "SOS": handle_sos,
            "WHERE": handle_where,
            "HELP": lambda *a: messages.help_text(),
            "SUMMARY": handle_summary,
        }

        handler = known_keywords.get(text)
        if handler:
            return handler(phone, driver, session, body.strip())

        if session.state == "awaiting_status":
            return handle_status_update(phone, body.strip().lower(), driver, session)

        return messages.unknown_command()

    except Exception as e:
        logger.exception("WhatsApp handler error for %s", phone)
        return messages.internal_error()


def handle_location(phone: str, lat: float, lon: float, driver: Driver | None, session: WhatsAppSession) -> str:
    if not driver:
        return "You are not registered as a driver. Contact your dispatcher."

    trip = find_active_trip(driver)
    if not trip:
        return messages.no_active_trip()

    TripPosition.objects.create(
        trip=trip,
        lat=lat,
        lon=lon,
        source="whatsapp",
        remark="via WhatsApp",
    )
    session.state = "idle"
    session.save(update_fields=["state"])
    return messages.position_received(trip.id, lat, lon)


def handle_accept(phone: str, driver: Driver | None, session: WhatsAppSession, raw: str) -> str:
    if not driver:
        return "You are not registered as a driver."

    trip_id = session.trip_id
    if not trip_id:
        return "No trip assigned to accept."

    try:
        trip = Trip.objects.get(pk=trip_id, driver=driver)
    except Trip.DoesNotExist:
        return "Trip not found."

    if trip.status != "dispatched":
        return f"Trip #{trip_id} cannot be accepted (status: {trip.status})."

    old_status = trip.status
    trip.status = "at_border"
    trip.actual_start = timezone.now()
    trip.save(update_fields=["status", "actual_start", "updated_at"])

    TripStatusLog.objects.create(
        trip=trip,
        from_status=old_status,
        to_status="at_border",
        notes="Accepted via WhatsApp",
    )

    session.state = "idle"
    session.save(update_fields=["state"])

    return messages.trip_accepted(trip.id)


def handle_reject(phone: str, driver: Driver | None, session: WhatsAppSession, raw: str) -> str:
    if not driver:
        return "You are not registered as a driver."

    trip_id = session.trip_id
    if not trip_id:
        return "No trip to reject."

    try:
        trip = Trip.objects.get(pk=trip_id, driver=driver)
    except Trip.DoesNotExist:
        return "Trip not found."

    # Set trip back to unassigned
    trip.driver = None
    trip.status = "cancelled"
    trip.save(update_fields=["driver", "status", "updated_at"])

    TripStatusLog.objects.create(
        trip=trip,
        from_status="dispatched",
        to_status="cancelled",
        notes="Rejected by driver via WhatsApp",
    )

    session.state = "idle"
    session.trip_id = None
    session.save(update_fields=["state", "trip_id"])

    return messages.trip_rejected(trip.id)


def handle_status(phone: str, driver: Driver | None, session: WhatsAppSession, raw: str) -> str:
    if not driver:
        return "You are not registered as a driver."

    trip = find_active_trip(driver)
    if not trip:
        return messages.no_active_trip()

    next_statuses = VALID_STATUS_TRANSITIONS.get(trip.status, [])
    if not next_statuses:
        return f"Trip #{trip.id} is already {trip.status}. No further updates needed."

    options = "\n".join([f"• `{s}`" for s in next_statuses])
    session.state = "awaiting_status"
    session.save(update_fields=["state"])

    return (
        f"Current status: *{trip.status.replace('_', ' ').title()}*\n\n"
        f"Available transitions:\n{options}\n\n"
        f"Reply with the status you want to set."
    )


def handle_status_update(phone: str, new_status: str, driver: Driver | None, session: WhatsAppSession) -> str:
    if not driver:
        return "You are not registered as a driver."

    trip = find_active_trip(driver)
    if not trip:
        session.state = "idle"
        session.save(update_fields=["state"])
        return messages.no_active_trip()

    next_statuses = VALID_STATUS_TRANSITIONS.get(trip.status, [])
    if new_status not in next_statuses:
        return f"Invalid status. Choose from: {', '.join(next_statuses)}"

    old_status = trip.status
    trip.status = new_status
    trip.save(update_fields=["status", "updated_at"])

    TripStatusLog.objects.create(
        trip=trip,
        from_status=old_status,
        to_status=new_status,
        notes="Updated via WhatsApp",
    )

    if new_status == "delivered":
        trip.actual_end = timezone.now()
        trip.save(update_fields=["actual_end"])

    session.state = "idle"
    session.save(update_fields=["state"])

    return messages.status_confirmed(trip.id, new_status)


def handle_sos(phone: str, driver: Driver | None, session: WhatsAppSession, raw: str) -> str:
    if not driver:
        return "You are not registered as a driver."

    trip = find_active_trip(driver)
    if not trip:
        return messages.no_active_trip()

    from django.utils import timezone
    trip.sos_triggered_at = timezone.now()
    trip.sos_message = "SOS via WhatsApp"
    trip.save(update_fields=["sos_triggered_at", "sos_message", "updated_at"])

    TripStatusLog.objects.create(
        trip=trip,
        from_status=trip.status,
        to_status=trip.status,
        notes="SOS triggered via WhatsApp",
    )

    session.state = "sos"
    session.save(update_fields=["state"])

    return messages.sos_alerted(trip.id)


def handle_where(phone: str, driver: Driver | None, session: WhatsAppSession, raw: str) -> str:
    if not driver:
        return "You are not registered as a driver."

    trip = find_active_trip(driver)
    if not trip:
        return messages.no_active_trip()

    last_pos = TripPosition.objects.filter(trip=trip).order_by("-timestamp").first()
    if not last_pos:
        return "No position reported yet for this trip."

    ts = timezone.localtime(last_pos.timestamp).strftime("%Y-%m-%d %H:%M")
    return messages.current_position(last_pos.lat, last_pos.lon, ts)


def handle_summary(phone: str, driver: Driver | None, session: WhatsAppSession, raw: str) -> str:
    if not driver:
        return "You are not registered as a driver."

    from trip.admin_views import fleet_summary_text
    from rest_framework.request import Request
    from django.http import HttpRequest

    # Reuse the existing fleet summary
    try:
        from django.test import RequestFactory
        factory = RequestFactory()
        drf_request = factory.get("/api/admin/summary/")
        drf_request.user = driver.user
        response = fleet_summary_text(drf_request)
        return response.data.get("text", "Summary unavailable.")
    except Exception:
        return "Summary unavailable right now. Try again later."
