from django.db import models


class WhatsAppSession(models.Model):
    """Tracks a WhatsApp conversation with a driver."""
    phone_number = models.CharField(max_length=30, unique=True)
    trip_id = models.IntegerField(null=True, blank=True)
    state = models.CharField(
        max_length=30,
        choices=[
            ("idle", "Idle"),
            ("awaiting_trip_accept", "Awaiting Trip Accept"),
            ("awaiting_status", "Awaiting Status"),
            ("sos", "SOS"),
        ],
        default="idle",
    )
    last_message_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_message_at"]

    def __str__(self):
        return f"{self.phone_number} ({self.state})"
