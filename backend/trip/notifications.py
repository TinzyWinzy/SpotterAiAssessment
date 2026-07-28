from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def send_whatsapp(driver_phone: str, message: str) -> bool:
    """Send a WhatsApp message via Twilio."""
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_WHATSAPP_NUMBER]):
        logger.debug("Twilio WhatsApp not configured — skipping")
        return False

    if not driver_phone:
        logger.debug("No driver phone — skipping WhatsApp")
        return False

    whatsapp_from = f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}"
    whatsapp_to = f"whatsapp:{driver_phone}"

    try:
        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(body=message, from_=whatsapp_from, to=whatsapp_to)
        logger.info("WhatsApp sent to %s", driver_phone)
        return True
    except Exception as e:
        logger.warning("WhatsApp failed for %s: %s", driver_phone, e)
        return False


STATUS_LABELS = {
    "dispatched": "Dispatched",
    "at_border": "At Border",
    "in_transit": "In Transit",
    "delivered": "Delivered",
    "paid": "Paid",
    "cancelled": "Cancelled",
}


def send_trip_status_sms(driver_phone: str, trip_id: int, status: str, origin: str, destination: str) -> bool:
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_FROM_NUMBER]):
        logger.debug("Twilio not configured — skipping SMS")
        return False

    if not driver_phone:
        logger.debug("No driver phone — skipping SMS")
        return False

    label = STATUS_LABELS.get(status, status)
    message = f"Spotter: Trip #{trip_id} ({origin} → {destination}) is now: {label}."

    try:
        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(body=message, from_=settings.TWILIO_FROM_NUMBER, to=driver_phone)
        logger.info("SMS sent to %s for trip #%s", driver_phone, trip_id)
        return True
    except Exception as e:
        logger.warning("SMS failed for %s: %s", driver_phone, e)
        return False
