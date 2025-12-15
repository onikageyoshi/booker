from django.db import models
import uuid
from django.conf import settings

NOTIF_TYPE_CHOICES = (
    ("booking", "Booking"),
    ("payment", "Payment"),
    ("review", "Review"),
    ("system", "System")
)


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIF_TYPE_CHOICES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    booking_id = models.UUIDField(null=True, blank=True)
    payment_id = models.UUIDField(null=True, blank=True)
    review_id = models.UUIDField(null=True, blank=True)


    class Meta:
        ordering = ['-created_at']


    def __str__(self):
        return f"Notification for {self.user}: {self.title}"
