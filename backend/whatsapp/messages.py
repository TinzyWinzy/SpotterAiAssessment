"""WhatsApp message templates."""


def trip_assigned(driver_name: str, trip_id: int, origin: str, destination: str, distance_km: float, cargo: str = "") -> str:
    lines = [
        f"*TruckLedger — Trip #{trip_id}*",
        "",
        f"Hi {driver_name}, you have a new trip!",
        "",
        f"*From:* {origin}",
        f"*To:* {destination}",
        f"*Distance:* {distance_km:,.0f} km",
    ]
    if cargo:
        lines.append(f"*Cargo:* {cargo}")
    lines.extend([
        "",
        "Reply *ACCEPT* to take this trip.",
        "Reply *REJECT* to decline.",
        "Reply *HELP* for available commands.",
    ])
    return "\n".join(lines)


def trip_accepted(trip_id: int) -> str:
    return (
        f"✅ Trip #{trip_id} accepted! You can now share your live location.\n\n"
        f"Send your location via WhatsApp, or reply with:\n"
        f"• *STATUS* — update trip status (dispatched/at_border/in_transit/delivered)\n"
        f"• *SOS* — emergency alert to dispatcher\n"
        f"• *WHERE* — get your last reported position\n"
        f"• *SUMMARY* — fleet summary"
    )


def trip_rejected(trip_id: int) -> str:
    return f"❌ Trip #{trip_id} declined. Dispatcher has been notified."


def status_confirmed(trip_id: int, new_status: str) -> str:
    label = new_status.replace("_", " ").title()
    return f"✅ Trip #{trip_id} updated to: *{label}*"


def position_received(trip_id: int, lat: float, lon: float) -> str:
    maps_url = f"https://www.google.com/maps?q={lat},{lon}"
    return (
        f"📍 Position received for Trip #{trip_id}!\n"
        f"`{lat:.5f}, {lon:.5f}`\n"
        f"View on map: {maps_url}"
    )


def sos_alerted(trip_id: int) -> str:
    return (
        f"🚨 *SOS ALERT SENT* 🚨\n\n"
        f"Trip #{trip_id}\n"
        f"Your dispatcher has been notified with your location.\n"
        f"Help is on the way."
    )


def sos_acknowledged(trip_id: int) -> str:
    return f"✅ SOS for Trip #{trip_id} has been acknowledged by dispatcher."


def current_position(lat: float, lon: float, timestamp: str) -> str:
    maps_url = f"https://www.google.com/maps?q={lat},{lon}"
    return (
        f"📍 *Your last reported position:*\n"
        f"`{lat:.5f}, {lon:.5f}`\n"
        f"Reported: {timestamp}\n"
        f"Map: {maps_url}"
    )


def no_active_trip() -> str:
    return "You have no active trip. Contact your dispatcher for assignment."


def help_text() -> str:
    return (
        "*Available commands:*\n\n"
        "• Send your *location* — share GPS position\n"
        "• *ACCEPT* — accept assigned trip\n"
        "• *REJECT* — decline assigned trip\n"
        "• *STATUS* — trip status options\n"
        "• *SOS* — emergency alert\n"
        "• *WHERE* — my last position\n"
        "• *SUMMARY* — fleet summary\n"
        "• *HELP* — this message"
    )


def unknown_command() -> str:
    return "I didn't understand that. Reply *HELP* for available commands."


def internal_error() -> str:
    return "Sorry, something went wrong. Please try again or contact support."
