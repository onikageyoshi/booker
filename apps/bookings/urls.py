from django.urls import path
from .views import (
    ApartmentBookingListCreateView,
    BookingDetailView,
)

urlpatterns = [
    # List & create bookings for an apartment
    path(
        "apartments/<int:apartment_id>/bookings/",
        ApartmentBookingListCreateView.as_view(),
        name="apartment-bookings"
    ),

    # Retrieve, update, cancel a booking
    path(
        "bookings/<int:id>/",
        BookingDetailView.as_view(),
        name="booking-detail"
    ),
]
