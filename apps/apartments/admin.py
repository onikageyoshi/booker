from django.contrib import admin
from .models import (
    Apartment, Amenity, ApartmentPricing, ApartmentAddress,
    ApartmentAvailability, ApartmentRule
)

@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')
    search_fields = ('name',)


class ApartmentPricingInline(admin.StackedInline):
    model = ApartmentPricing
    extra = 0
    readonly_fields = ()
    fields = ('price_per_night', 'cleaning_fee', 'service_fee', 'weekend_price', 'currency')


class ApartmentAddressInline(admin.StackedInline):
    model = ApartmentAddress
    extra = 0
    fields = ('country', 'state', 'city', 'street')


class ApartmentAvailabilityInline(admin.TabularInline):
    model = ApartmentAvailability
    extra = 1
    fields = ('date', 'is_available')


class ApartmentRuleInline(admin.TabularInline):
    model = ApartmentRule
    extra = 1
    fields = ('rule_text',)


@admin.register(Apartment)
class ApartmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'host', 'property_type', 'total_bedrooms', 'total_bathrooms', 'max_guests', 'is_active', 'is_verified', 'created_at')
    list_filter = ('property_type', 'is_active', 'is_verified', 'created_at')
    search_fields = ('title', 'description', 'host__email', 'host__first_name', 'host__last_name')
    readonly_fields = ('uploaded_at',)
    inlines = [ApartmentPricingInline, ApartmentAddressInline, ApartmentAvailabilityInline, ApartmentRuleInline]

    fieldsets = (
        (None, {
            'fields': ('host', 'title', 'description', 'property_type', 'total_bedrooms', 'total_bathrooms', 'max_guests')
        }),
        ('Image', {
            'fields': ('image', 'is_cover', 'uploaded_at')
        }),
        ('Status', {
            'fields': ('is_active', 'is_verified')
        }),
        ('Amenities', {
            'fields': ('amenities',)
        }),
    )

    filter_horizontal = ('amenities',)


@admin.register(ApartmentPricing)
class ApartmentPricingAdmin(admin.ModelAdmin):
    list_display = ('apartment', 'price_per_night', 'cleaning_fee', 'service_fee', 'weekend_price', 'currency')
    search_fields = ('apartment__title',)


@admin.register(ApartmentAddress)
class ApartmentAddressAdmin(admin.ModelAdmin):
    list_display = ('apartment', 'country', 'state', 'city', 'street')
    search_fields = ('apartment__title', 'city', 'state', 'country')


@admin.register(ApartmentAvailability)
class ApartmentAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('apartment', 'date', 'is_available')
    list_filter = ('is_available',)
    search_fields = ('apartment__title',)


@admin.register(ApartmentRule)
class ApartmentRuleAdmin(admin.ModelAdmin):
    list_display = ('apartment', 'rule_text')
    search_fields = ('apartment__title', 'rule_text')
