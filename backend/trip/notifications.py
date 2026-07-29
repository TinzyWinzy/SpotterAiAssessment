from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def send_whatsapp(driver_phone: str, message: str) -> bool:
    """Send a WhatsApp message via Twilio. Returns True if sent successfully."""
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_WHATSAPP_NUMBER]):
        logger.info("Twilio WhatsApp not configured — skipping send to %s", driver_phone)
        return False

    if not driver_phone:
        logger.warning("No driver phone — skipping WhatsApp")
        return False

    whatsapp_from = f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}"
    whatsapp_to = f"whatsapp:{driver_phone}"

    try:
        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        msg = client.messages.create(body=message, from_=whatsapp_from, to=whatsapp_to)
        logger.info("WhatsApp sent to %s (sid=%s)", driver_phone, msg.sid)
        return True
    except Exception as e:
        logger.error("WhatsApp failed for %s: %s", driver_phone, e, exc_info=True)
        return False


STATUS_LABELS = {
    "dispatched": "Dispatched",
    "at_border": "At Border",
    "in_transit": "In Transit",
    "delivered": "Delivered",
    "paid": "Paid",
    "cancelled": "Cancelled",
}


BOOKING_STATUS_LABELS = {
    "inquiry": "Inquiry Received",
    "quoted": "Quote Sent",
    "confirmed": "Booking Confirmed",
    "assigned": "Driver Assigned",
    "dispatched": "Driver En Route",
    "at_border": "At Border",
    "in_transit": "In Transit",
    "delivered": "Delivered",
    "paid": "Paid",
    "cancelled": "Cancelled",
}


def send_booking_whatsapp(
    customer_phone: str,
    booking_ref: str,
    status: str,
    tracking_url: str = "",
    customer_name: str = "",
) -> bool:
    """Send WhatsApp notification to a customer about their booking status."""
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_WHATSAPP_NUMBER]):
        logger.info("Twilio WhatsApp not configured — skipping booking notification to %s", customer_phone)
        return False

    if not customer_phone:
        logger.warning("No customer phone — skipping WhatsApp for %s", booking_ref)
        return False

    label = BOOKING_STATUS_LABELS.get(status, status)
    greeting = f"Hi {customer_name}, " if customer_name else ""
    message = f"{greeting}your Trucki booking {booking_ref} is now: {label}."
    if tracking_url:
        message += f"\n\nTrack it here: {tracking_url}"
    message += "\n\nThank you for choosing Trucki! 🚛"

    whatsapp_from = f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}"
    whatsapp_to = f"whatsapp:{customer_phone}"

    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        msg = client.messages.create(body=message, from_=whatsapp_from, to=whatsapp_to)
        logger.info("Booking WhatsApp sent to %s for %s (sid=%s)", customer_phone, booking_ref, msg.sid)
        return True
    except Exception as e:
        logger.error("Booking WhatsApp failed for %s (%s): %s", customer_phone, booking_ref, e, exc_info=True)
        return False


def send_trip_status_sms(driver_phone: str, trip_id: int, status: str, origin: str, destination: str) -> bool:
    """Send SMS notification of trip status change. Returns True if sent successfully."""
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_FROM_NUMBER]):
        logger.info("Twilio SMS not configured — skipping send to %s", driver_phone)
        return False

    if not driver_phone:
        logger.warning("No driver phone — skipping SMS for trip #%s", trip_id)
        return False

    label = STATUS_LABELS.get(status, status)
    message = f"Spotter: Trip #{trip_id} ({origin} → {destination}) is now: {label}."

    try:
        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        msg = client.messages.create(body=message, from_=settings.TWILIO_FROM_NUMBER, to=driver_phone)
        logger.info("SMS sent to %s for trip #%s (sid=%s)", driver_phone, trip_id, msg.sid)
        return True
    except Exception as e:
        logger.error("SMS failed for %s (trip #%s): %s", driver_phone, trip_id, e, exc_info=True)
        return False
