from django.core.management.base import BaseCommand
from apps.apartments.utils import get_cached_active_apartments, get_cached_apartment_detail
from apps.apartments.models import Apartment

class Command(BaseCommand):
    help = "Populate Redis cache for apartments"
    def handle(self, *args, **kwargs):
        get_cached_active_apartments()
        for apt in Apartment.objects.all():
            get_cached_apartment_detail(apt.id)
        self.stdout.write(self.style.SUCCESS("Apartment cache populated!"))
