from django.contrib import admin
from .models import (
    Apartment, ApartmentImage, Amenity,
    ApartmentPricing, ApartmentAddress,
    ApartmentAvailability, ApartmentRule
)


class ApartmentImageInline(admin.TabularInline):
    model = ApartmentImage
    extra = 1
    fields = ('image', 'is_cover', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


class ApartmentRuleInline(admin.TabularInline):
    model = ApartmentRule
    extra = 1
    fields = ('rule_text',)


class ApartmentAvailabilityInline(admin.TabularInline):
    model = ApartmentAvailability
    extra = 1
    fields = ('date', 'is_available')


class ApartmentPricingInline(admin.StackedInline):
    model = ApartmentPricing
    extra = 0


class ApartmentAddressInline(admin.StackedInline):
    model = ApartmentAddress
    extra = 0


@admin.register(Apartment)
class ApartmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'host', 'property_type', 'max_guests', 'is_active', 'is_verified', 'created_at')
    list_filter = ('property_type', 'is_active', 'is_verified')
    search_fields = ('title', 'description', 'host__username', 'host__email')
    inlines = [
        ApartmentImageInline,
        ApartmentPricingInline,
        ApartmentAddressInline,
        ApartmentRuleInline,
        ApartmentAvailabilityInline
    ]
    filter_horizontal = ('amenities',)  # Makes ManyToManyField easier to select


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')
    search_fields = ('name',)


@admin.register(ApartmentImage)
class ApartmentImageAdmin(admin.ModelAdmin):
    list_display = ('apartment', 'is_cover', 'uploaded_at')
    list_filter = ('is_cover',)
    readonly_fields = ('uploaded_at',)


@admin.register(ApartmentPricing)
class ApartmentPricingAdmin(admin.ModelAdmin):
    list_display = ('apartment', 'price_per_night', 'cleaning_fee', 'service_fee', 'weekend_price', 'currency')


@admin.register(ApartmentAddress)
class ApartmentAddressAdmin(admin.ModelAdmin):
    list_display = ('apartment', 'country', 'state', 'city', 'street')


@admin.register(ApartmentAvailability)
class ApartmentAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('apartment', 'date', 'is_available')
    list_filter = ('is_available',)
    ordering = ('date',)


@admin.register(ApartmentRule)
class ApartmentRuleAdmin(admin.ModelAdmin):
    list_display = ('apartment', 'rule_text')
