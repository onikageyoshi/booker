from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from .models import Apartment, ApartmentAvailability


@receiver([post_save, post_delete], sender=Apartment)
def clear_apartment_cache(sender, instance, **kwargs):
    cache.delete("apartment:list")
    cache.delete(f"apartment:detail:{instance.id}")


@receiver([post_save, post_delete], sender=ApartmentAvailability)
def clear_availability_cache(sender, instance, **kwargs):
    cache.delete(f"apartment:availability:{instance.apartment.id}")
