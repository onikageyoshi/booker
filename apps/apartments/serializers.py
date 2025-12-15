from rest_framework import serializers
from .models import (
    Apartment, ApartmentImage, Amenity, ApartmentAmenity,
    ApartmentPricing, ApartmentAddress, ApartmentAvailability,
    ApartmentRule
)


class ApartmentImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApartmentImage
        fields = ['id', 'image', 'is_cover', 'uploaded_at']


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ['id', 'name', 'icon']


class ApartmentRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApartmentRule
        fields = ['id', 'rule_text']


class ApartmentPricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApartmentPricing
        fields = [
            'price_per_night', 'cleaning_fee', 'service_fee',
            'weekend_price', 'currency'
        ]


class ApartmentAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApartmentAddress
        fields = [
            'country', 'state', 'city', 'street'
        ]


class ApartmentAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApartmentAvailability
        fields = ['date', 'is_available']


class ApartmentSerializer(serializers.ModelSerializer):
    images = ApartmentImageSerializer(many=True, read_only=True)
    pricing = ApartmentPricingSerializer(read_only=True)
    address = ApartmentAddressSerializer(read_only=True)
    apartment_amenities = serializers.SerializerMethodField()
    rules = ApartmentRuleSerializer(many=True, read_only=True)
    availability = ApartmentAvailabilitySerializer(many=True, read_only=True)

    class Meta:
        model = Apartment
        fields = [
            'id', 'host', 'title', 'description', 'property_type',
            'total_bedrooms', 'total_bathrooms', 'max_guests',
            'is_active', 'is_verified',
            'created_at', 'updated_at',

            'images', 'pricing', 'address',
            'apartment_amenities', 'rules', 'availability'
        ]

    def get_apartment_amenities(self, obj):
        return AmenitySerializer(
            [a.amenity for a in obj.apartment_amenities.all()],
            many=True
        ).data
