from rest_framework import serializers
from django.utils import timezone
from decimal import Decimal
from django.db.models import Q

from .models import Booking
from apps.apartments.models import Apartment, ApartmentPricing


class BookingSerializer(serializers.ModelSerializer):
    guest = serializers.StringRelatedField(read_only=True)
    apartment = serializers.PrimaryKeyRelatedField(queryset=Apartment.objects.all())

    class Meta:
        model = Booking
        fields = [
            "id",
            "apartment",
            "guest",
            "check_in",
            "check_out",
            "nights",
            "guests_count",
            "total_price",
            "status",
            "payment_status",
            "provider_transaction_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "guest",
            "nights",
            "total_price",
            "status",
            "payment_status",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        apartment = attrs.get("apartment") or getattr(self.instance, "apartment", None)
        check_in = attrs.get("check_in") or getattr(self.instance, "check_in", None)
        check_out = attrs.get("check_out") or getattr(self.instance, "check_out", None)
        guests_count = attrs.get("guests_count") or getattr(self.instance, "guests_count", 1)

        if not apartment:
            raise serializers.ValidationError({"apartment": "Apartment is required."})

        if not check_in or not check_out:
            raise serializers.ValidationError("check_in and check_out are required.")

        if check_in >= check_out:
            raise serializers.ValidationError("check_out must be after check_in.")

        if check_in < timezone.localdate():
            raise serializers.ValidationError("check_in cannot be in the past.")

        if guests_count > apartment.max_guests:
            raise serializers.ValidationError(
                f"Maximum guests allowed: {apartment.max_guests}"
            )

        overlap_q = (
            Q(check_in__lt=check_out) &
            Q(check_out__gt=check_in) &
            Q(status__in=["pending", "confirmed"])
        )

        conflicts = Booking.objects.filter(
            apartment=apartment
        ).filter(overlap_q)

        if self.instance:
            conflicts = conflicts.exclude(pk=self.instance.pk)

        if conflicts.exists():
            raise serializers.ValidationError(
                "The apartment is already booked for the selected dates."
            )

        return attrs

    def _compute_total_price(self, apartment, nights):
        try:
            pricing = apartment.pricing
            base_price = Decimal(pricing.price_per_night)
            cleaning_fee = Decimal(pricing.cleaning_fee or 0)
            service_fee = Decimal(pricing.service_fee or 0)
        except ApartmentPricing.DoesNotExist:
            base_price = Decimal("0.00")
            cleaning_fee = Decimal("0.00")
            service_fee = Decimal("0.00")

        return (base_price * nights) + cleaning_fee + service_fee

    def create(self, validated_data):
        check_in = validated_data["check_in"]
        check_out = validated_data["check_out"]

        nights = (check_out - check_in).days
        if nights <= 0:
            raise serializers.ValidationError("Invalid booking duration.")

        validated_data["nights"] = nights
        validated_data["total_price"] = self._compute_total_price(
            validated_data["apartment"], nights
        )

        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["guest"] = request.user

        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("apartment", None)
        validated_data.pop("guest", None)
        validated_data.pop("status", None)
        validated_data.pop("payment_status", None)

        check_in = validated_data.get("check_in", instance.check_in)
        check_out = validated_data.get("check_out", instance.check_out)

        nights = (check_out - check_in).days
        if nights <= 0:
            raise serializers.ValidationError("Invalid booking duration.")

        instance.nights = nights
        instance.total_price = self._compute_total_price(instance.apartment, nights)

        return super().update(instance, validated_data)
