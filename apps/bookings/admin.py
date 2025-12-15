from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "apartment", "guest", "check_in", "check_out", "nights", "total_price", "status", "payment_status", "created_at")
    list_filter = ("status", "payment_status", "check_in", "check_out")
    search_fields = ("apartment__title", "guest__email", "id")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
