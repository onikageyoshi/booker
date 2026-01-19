from django.urls import path
from .views import (
    ApartmentBookingListCreateView,
    BookingDetailView,
    CreateCheckoutSessionView,
    stripe_webhook,
)

urlpatterns = [
    path(
        "apartments/<int:apartment_id>/bookings/",
        ApartmentBookingListCreateView.as_view(),
        name="apartment-bookings"
    ),
    path(
        "bookings/<uuid:id>/",
        BookingDetailView.as_view(),
        name="booking-detail"
    ),
    path(
        "bookings/<uuid:booking_id>/pay/",
        CreateCheckoutSessionView.as_view(),
        name="create-checkout-session"
    ),
    path(
        "webhooks/stripe/",
        stripe_webhook,
        name="stripe-webhook"
    ),
]