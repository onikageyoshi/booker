from django.urls import path
from .views import ApartmentBookingListCreateView, BookingDetailView

urlpatterns = [
    path("apartments/<int:apartment_id>/bookings/", ApartmentBookingListCreateView.as_view(), name="apartment-bookings"),
    path("bookings/<uuid:id>/", BookingDetailView.as_view(), name="booking-detail"),
]
