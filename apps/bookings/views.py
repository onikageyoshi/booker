from rest_framework import generics, permissions, status, serializers
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Booking
from .serializers import BookingSerializer
from apps.apartments.models import Apartment


class IsBookingGuestOrHost(permissions.BasePermission):
    """
    Guests can read/update their bookings.
    Hosts can only read bookings for their apartments.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.guest == request.user or obj.apartment.host == request.user
        return obj.guest == request.user


class ApartmentBookingListCreateView(generics.ListCreateAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        apartment_id = self.kwargs.get("apartment_id")
        return Booking.objects.filter(
            apartment_id=apartment_id
        ).order_by("-created_at")

    def get_serializer_context(self):
        return {"request": self.request}

    @swagger_auto_schema(
        operation_summary="List bookings for an apartment",
        responses={200: BookingSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a booking for an apartment",
        request_body=BookingSerializer,
        responses={201: BookingSerializer}
    )
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        apartment = get_object_or_404(
            Apartment, id=self.kwargs.get("apartment_id")
        )

        if not apartment.is_active:
            return Response(
                {"detail": "Apartment is not available for booking."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        apartment = get_object_or_404(
            Apartment, id=self.kwargs.get("apartment_id")
        )
        serializer.save(apartment=apartment)


class BookingDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated, IsBookingGuestOrHost]
    lookup_field = "id"

    def get_queryset(self):
        return Booking.objects.select_related("apartment")

    @swagger_auto_schema(
        operation_summary="Retrieve a booking",
        responses={200: BookingSerializer}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update a booking (pending only)",
        request_body=BookingSerializer,
        responses={200: BookingSerializer}
    )
    def put(self, request, *args, **kwargs):
        booking = self.get_object()

        if booking.status != "pending":
            return Response(
                {"detail": "Only pending bookings can be updated."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Cancel a booking",
        responses={200: BookingSerializer}
    )
    def delete(self, request, *args, **kwargs):
        booking = self.get_object()

        if booking.status not in ["pending", "confirmed"]:
            return Response(
                {"detail": "This booking cannot be cancelled."},
                status=status.HTTP_400_BAD_REQUEST
            )

        booking.status = "cancelled"
        booking.save(update_fields=["status"])

        serializer = BookingSerializer(booking)
        return Response(serializer.data, status=status.HTTP_200_OK)
