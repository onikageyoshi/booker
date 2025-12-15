from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Booking
from .serializers import BookingSerializer
from apps.apartments.models import Apartment


class IsBookingGuestOrHost(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.guest == request.user or obj.apartment.host == request.user
        return obj.guest == request.user


class ApartmentBookingListCreateView(generics.ListCreateAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Booking.objects.none()

    def get_queryset(self):
        apartment_id = self.kwargs.get("apartment_id")
        return Booking.objects.filter(apartment_id=apartment_id).order_by("-created_at")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    @swagger_auto_schema(responses={200: BookingSerializer(many=True)})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(request_body=BookingSerializer, responses={201: BookingSerializer})
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        apartment_id = self.kwargs.get("apartment_id")
        apartment = get_object_or_404(Apartment, id=apartment_id)

        if not apartment.is_active:
            return Response({"detail": "Apartment is not available for booking."}, status=status.HTTP_400_BAD_REQUEST)

        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save()


class BookingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated, IsBookingGuestOrHost]
    lookup_field = "id"  

    @swagger_auto_schema(responses={200: BookingSerializer})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(request_body=BookingSerializer, responses={200: BookingSerializer})
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(responses={204: "Deleted"})
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
