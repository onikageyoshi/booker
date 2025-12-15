from django.db import models
from django.conf import settings
from apps.apartments.models import Apartment


class Review(models.Model):
    apartment = models.ForeignKey(
        Apartment, on_delete=models.CASCADE,
        related_name="reviews"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="apartment_reviews"
    )
    rating = models.PositiveSmallIntegerField()  # 1–5 stars
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("apartment", "user")  # A user reviews once
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating}★ by {self.user} on {self.apartment.title}"
