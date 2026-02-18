import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from apps.apartments.models import Apartment
from apps.bookings.models import Booking
from .serializers import BookingSerializer

stripe.api_key = settings.STRIPE_SECRET_KEY

class IsBookingGuestOrHost(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.guest == request.user or obj.apartment.host == request.user
        return obj.guest == request.user

class ApartmentBookingListCreateView(generics.ListCreateAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        apartment_id = self.kwargs.get("apartment_id")
        return Booking.objects.filter(apartment_id=apartment_id).order_by("-created_at")

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
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        apartment = get_object_or_404(Apartment, id=self.kwargs.get("apartment_id"))
        if not apartment.is_active:
            return Response({"detail": "Apartment is not available for booking."}, status=status.HTTP_400_BAD_REQUEST)

        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        apartment = get_object_or_404(Apartment, id=self.kwargs.get("apartment_id"))
        serializer.save(apartment=apartment, guest=self.request.user)

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
            return Response({"detail": "Only pending bookings can be updated."}, status=status.HTTP_400_BAD_REQUEST)
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Cancel a booking",
        responses={200: BookingSerializer}
    )
    def delete(self, request, *args, **kwargs):
        booking = self.get_object()
        if booking.status not in ["pending", "confirmed"]:
            return Response({"detail": "This booking cannot be cancelled."}, status=status.HTTP_400_BAD_REQUEST)

        booking.status = "cancelled"
        booking.save(update_fields=["status"])
        return Response(BookingSerializer(booking).data, status=status.HTTP_200_OK)

class CreateCheckoutSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id, guest=request.user)
        
        if not booking.total_price or booking.total_price <= 0:
            return Response({"error": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)
        
        supported_currencies = ['gbp', 'usd', 'eur']
        currency_code = booking.apartment.pricing.currency.lower()

        if currency_code not in supported_currencies:
            return Response({"error": f"Currency {booking.apartment.pricing.currency} not supported."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            unit_amount = int(booking.total_price * 100)  # Stripe expects amount in cents
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': currency_code,
                        'product_data': {'name': f"Booking: {booking.apartment.title}"},
                        'unit_amount': unit_amount,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=request.build_absolute_uri(f'/bookings/success/'),
                cancel_url=request.build_absolute_uri(f'/bookings/{booking.id}/'),
                metadata={"booking_id": str(booking.id)}
            )
            return Response({"url": checkout_session.url}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=endpoint_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        booking_id = session.get('metadata', {}).get('booking_id')
        payment_intent_id = session.get('payment_intent')

        if booking_id:
            try:
                booking = Booking.objects.get(id=booking_id)
                booking.payment_status = "paid"
                booking.status = "confirmed"
                booking.provider_transaction_id = payment_intent_id
                booking.save(update_fields=["payment_status", "status", "provider_transaction_id"])
            except Booking.DoesNotExist:
                return HttpResponse(status=404)

    return HttpResponse(status=200)



