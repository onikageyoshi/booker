from django.db import models
from django.contrib.auth import get_user_model
from cloudinary.models import CloudinaryField


User = get_user_model()

CURRENCY = (
    ("GBP", "British Pound"),
    ("USD", "US Dollar"),
    ("EUR", "Euro")
)


class Amenity(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class Apartment(models.Model):
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='apartments')
    title = models.CharField(max_length=255)
    description = models.TextField()

    # Cloudinary image field with a default placeholder
    image = CloudinaryField(
        resource_type='auto',
        folder='apartments',
        null=True,
        blank=True,

    )
    is_cover = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    property_type = models.CharField(
        max_length=50,
        choices=[
            ('apartment', 'Apartment'),
            ('room', 'Private Room'),
            ('entire_home', 'Entire Home'),
            ('studio', 'Studio'),
            ('villa', 'Villa'),
        ],
        default='apartment'
    )

    total_bedrooms = models.PositiveIntegerField(default=1)
    total_bathrooms = models.PositiveIntegerField(default=1)
    max_guests = models.PositiveIntegerField(default=1)

    amenities = models.ManyToManyField(Amenity, related_name='apartments', blank=True)

    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ApartmentPricing(models.Model):
    apartment = models.OneToOneField(Apartment, on_delete=models.CASCADE, related_name='pricing')
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    cleaning_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    service_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    weekend_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default='GBP', choices=CURRENCY)

    def __str__(self):
        return f"Pricing for {self.apartment.title}"


class ApartmentAddress(models.Model):
    apartment = models.OneToOneField(Apartment, on_delete=models.CASCADE, related_name='address')
    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    street = models.CharField(max_length=255)

    def __str__(self):
        return f"Address for {self.apartment.title}"


class ApartmentAvailability(models.Model):
    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name='availability')
    date = models.DateField()
    is_available = models.BooleanField(default=True)

    class Meta:
        unique_together = ('apartment', 'date')
        ordering = ['date']

    def __str__(self):
        return f"{self.apartment.title} - {self.date}"


class ApartmentRule(models.Model):
    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name='rules')
    rule_text = models.CharField(max_length=255)

    def __str__(self):
        return f"Rule for {self.apartment.title}"
