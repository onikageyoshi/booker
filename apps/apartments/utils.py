import os
import cloudinary
import cloudinary.uploader
import cloudinary.api



cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)


def upload_apartment_image(file, folder="apartments"):
    try:
        result = cloudinary.uploader.upload(file, folder=folder)
        return result.get("secure_url")
    except Exception as e:
        raise Exception(f"Cloudinary upload failed: {e}")
    

from django.core.cache import cache
from .models import Apartment

CACHE_TIMEOUT = 60 * 500


def get_cached_active_apartments():
    """
    Returns cached active & verified apartments with all relations
    """
    cache_key = "apartments:active_verified"

    apartments = cache.get(cache_key)
    if apartments is None:
        apartments = (
            Apartment.objects
            .filter(is_active=True, is_verified=True)
            .select_related("pricing", "address")
            .prefetch_related("amenities", "rules", "availability")
        )
        apartments = list(apartments)  
        cache.set(cache_key, apartments, CACHE_TIMEOUT)

    return apartments


def get_cached_apartment_detail(apartment_id):
    """
    Cache single apartment detail
    """
    cache_key = f"apartments:detail:{apartment_id}"

    apartment = cache.get(cache_key)
    if apartment is None:
        apartment = (
            Apartment.objects
            .select_related("pricing", "address")
            .prefetch_related("amenities", "rules", "availability")
            .filter(id=apartment_id, is_active=True)
            .first()
        )
        cache.set(cache_key, apartment, CACHE_TIMEOUT)

    return apartment

    





