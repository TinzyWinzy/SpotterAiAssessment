"""WhatsApp webhook — Twilio inbound message handler."""
import logging
from urllib.parse import parse_qs

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from twilio.twiml.messaging_response import MessagingResponse

from .handlers import handle_incoming

logger = logging.getLogger(__name__)


@csrf_exempt
def webhook(request):
    """Twilio WhatsApp webhook: receive messages and reply."""
    if request.method != "POST":
        return HttpResponse(status=405)

    try:
        body_text = request.body.decode("utf-8")
        params = parse_qs(body_text)

        from_number = params.get("From", [""])[0].replace("whatsapp:", "")
        message_body = params.get("Body", [""])[0].strip()
        num_media = int(params.get("NumMedia", ["0"])[0])

        lat = None
        lon = None

        if num_media > 0:
            media_type = params.get("MediaContentType0", [""])[0]
            if media_type == "image/jpeg" or "location" in message_body.lower() or num_media > 0:
                lat_str = params.get("Latitude", [None])[0]
                lon_str = params.get("Longitude", [None])[0]
                if lat_str and lon_str:
                    lat = float(lat_str)
                    lon = float(lon_str)

        logger.info(
            "WhatsApp from %s: body=%s lat=%s lon=%s",
            from_number, message_body[:50], lat, lon,
        )

        reply = handle_incoming(
            phone=from_number,
            body=message_body,
            lat=lat,
            lon=lon,
        )

        resp = MessagingResponse()
        resp.message(reply)
        return HttpResponse(str(resp), content_type="application/xml")

    except Exception as e:
        logger.exception("WhatsApp webhook error")
        resp = MessagingResponse()
        resp.message("Sorry, an error occurred. Please try again.")
        return HttpResponse(str(resp), content_type="application/xml")
