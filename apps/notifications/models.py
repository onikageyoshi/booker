# apps/notifications/models.py

from django.db import models
import uuid
from django.conf import settings
from apps.user.models import User

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ("apartment_available", "Apartment Available"),
        ("apartment_pending", "Apartment Pending Approval"),
        ("apartment_approved", "Apartment Approved"),
        ("apartment_rejected", "Apartment Rejected"),
        ("system", "System"),
    )

    TARGET_AUDIENCE = (
        ("user", "User"),
        ("admin", "Admin"),
        ("both", "User & Admin"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    related_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="related_admin_notifications",
    )

    user = models.ForeignKey("user.User", on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")

    title = models.CharField(max_length=255)
    message = models.TextField()

    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    target_audience = models.CharField(max_length=10, choices=TARGET_AUDIENCE)

    apartment_id = models.UUIDField(null=True, blank=True)
    booking_id = models.UUIDField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
