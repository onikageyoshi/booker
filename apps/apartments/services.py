from django.core.cache import cache
from .models import Apartment, Amenity, ApartmentAvailability

CACHE_TTL = 60 * 10  


def get_apartment_list():
    key = "apartment:list"

    apartments = cache.get(key)
    if apartments is None:
        apartments = list(
            Apartment.objects
            .filter(is_active=True, is_verified=True)
            .select_related("pricing", "address")
            .prefetch_related("amenities", "rules")
        )
        cache.set(key, apartments, CACHE_TTL)

    return apartments


def get_apartment_detail(apartment_id):
    key = f"apartment:detail:{apartment_id}"

    apartment = cache.get(key)
    if apartment is None:
        apartment = (
            Apartment.objects
            .select_related("pricing", "address")
            .prefetch_related("amenities", "rules", "availability")
            .get(id=apartment_id)
        )
        cache.set(key, apartment, CACHE_TTL)

    return apartment



from django.core.cache import cache
from .models import ApartmentAvailability


def get_apartment_availability(apartment_id):
    key = f"apartment:availability:{apartment_id}"

    data = cache.get(key)
    if data is None:
        data = list(
            ApartmentAvailability.objects.filter(
                apartment_id=apartment_id,
                is_available=True
            )
        )
        cache.set(key, data, 300)  

    return data
