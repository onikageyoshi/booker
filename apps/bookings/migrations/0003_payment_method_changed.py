from django.db import migrations

def update_payment_statuses(apps, schema_editor):
    try:
        Booking = apps.get_model('bookings', 'Booking')
        Booking.objects.filter(
            provider_transaction_id__isnull=False,
            payment_status="unpaid"
        ).exclude(
            provider_transaction_id=""
        ).update(
            payment_status="paid",
            status="confirmed"
        )
    except LookupError:
        pass

class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0002_alter_booking_total_price'),
    ]

    operations = [
        migrations.RunPython(update_payment_statuses),
    ]