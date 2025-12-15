from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta

from .models import Booking
from apps.apartments.models import ApartmentPricing, Apartment
from django.db.models import Q


class BookingSerializer(serializers.ModelSerializer):
    guest = serializers.StringRelatedField(read_only=True)
    apartment = serializers.PrimaryKeyRelatedField(queryset=Apartment.objects.all())

    class Meta:
        model = Booking
        fields = [
            "id", "apartment", "guest", "check_in", "check_out",
            "nights", "guests_count", "total_price",
            "status", "payment_status", "created_at", "updated_at",
            "provider_transaction_id",
        ]
        read_only_fields = ["id", "guest", "nights", "total_price", "status", "payment_status", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None

        apartment = attrs.get("apartment") or self.instance and self.instance.apartment
        check_in = attrs.get("check_in") or self.instance and self.instance.check_in
        check_out = attrs.get("check_out") or self.instance and self.instance.check_out
        guests_count = attrs.get("guests_count") or getattr(self.instance, "guests_count", 1)

        if not apartment:
            raise serializers.ValidationError("Apartment is required.")

        if not check_in or not check_out:
            raise serializers.ValidationError("check_in and check_out dates are required.")

        if check_in >= check_out:
            raise serializers.ValidationError("check_out must be after check_in.")

        if check_in < timezone.localdate():
            raise serializers.ValidationError("check_in cannot be in the past.")

        # optional: enforce max guests
        if guests_count > apartment.max_guests:
            raise serializers.ValidationError(f"Max guests for this apartment: {apartment.max_guests}")

        # check for overlapping bookings (pending or confirmed)
        overlap_q = Q(check_in__lt=check_out) & Q(check_out__gt=check_in) & Q(status__in=("pending", "confirmed"))
        conflicts = Booking.objects.filter(apartment=apartment).filter(overlap_q)
        # If updating an existing booking, exclude itself
        if self.instance:
            conflicts = conflicts.exclude(pk=self.instance.pk)

        if conflicts.exists():
            raise serializers.ValidationError("The apartment is already booked for the selected dates.")

        return attrs

    def create(self, validated_data):
        # compute nights and total_price
        check_in = validated_data["check_in"]
        check_out = validated_data["check_out"]
        nights = (check_out - check_in).days
        validated_data["nights"] = nights

        apartment = validated_data["apartment"]
        # fetch price info, fallback to apartment field if no pricing set
        try:
            pricing = apartment.pricing
            base_price = pricing.price_per_night
            cleaning_fee = pricing.cleaning_fee or 0
            service_fee = pricing.service_fee or 0
        except ApartmentPricing.DoesNotExist:
            # fallback: try attribute price_per_night on apartment (if present)
            base_price = getattr(apartment, "price_per_night", 0)
            cleaning_fee = 0
            service_fee = 0

        subtotal = base_price * nights
        total = subtotal + cleaning_fee + service_fee

        validated_data["total_price"] = total

        # guest from context
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["guest"] = request.user

        return super().create(validated_data)

    def update(self, instance, validated_data):
        # disallow changing apartment or guest via update
        validated_data.pop("apartment", None)
        validated_data.pop("guest", None)
        # recompute nights and total price if dates changed
        check_in = validated_data.get("check_in", instance.check_in)
        check_out = validated_data.get("check_out", instance.check_out)
        nights = (check_out - check_in).days
        instance.nights = nights

        # recompute price
        apartment = instance.apartment
        try:
            pricing = apartment.pricing
            base_price = pricing.price_per_night
            cleaning_fee = pricing.cleaning_fee or 0
            service_fee = pricing.service_fee or 0
        except ApartmentPricing.DoesNotExist:
            base_price = getattr(apartment, "price_per_night", 0)
            cleaning_fee = 0
            service_fee = 0

        subtotal = base_price * nights
        total = subtotal + cleaning_fee + service_fee
        instance.total_price = total

        return super().update(instance, validated_data)
