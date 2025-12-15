from django.contrib import admin
from .models import (
    Apartment, ApartmentImage, Amenity, ApartmentAmenity,
    ApartmentPricing, ApartmentAddress, ApartmentAvailability,
    ApartmentRule
)


class ApartmentImageInline(admin.TabularInline):
    model = ApartmentImage
    extra = 1


class ApartmentAmenityInline(admin.TabularInline):
    model = ApartmentAmenity
    extra = 1


class ApartmentRuleInline(admin.TabularInline):
    model = ApartmentRule
    extra = 1


@admin.register(Apartment)
class ApartmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'host', 'property_type', 'is_active', 'is_verified', 'created_at')
    list_filter = ('is_active', 'is_verified', 'property_type')
    search_fields = ('title', 'description', 'host__email')

    inlines = [
        ApartmentImageInline,
        ApartmentAmenityInline,
        ApartmentRuleInline
    ]


@admin.register(ApartmentPricing)
class ApartmentPricingAdmin(admin.ModelAdmin):
    list_display = ('apartment', 'price_per_night', 'currency', 'cleaning_fee', 'service_fee')


@admin.register(ApartmentAddress)
class ApartmentAddressAdmin(admin.ModelAdmin):
    list_display = ('apartment', 'country', 'state', 'city')


@admin.register(ApartmentAvailability)
class ApartmentAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('apartment', 'date', 'is_available')
    list_filter = ('is_available',)


admin.site.register(Amenity)
admin.site.register(ApartmentImage)
admin.site.register(ApartmentAmenity)
admin.site.register(ApartmentRule)
