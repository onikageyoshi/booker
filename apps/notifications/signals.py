from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

from apps.user.models import User
from apps.apartments.models import Apartment, ApartmentAvailability
from apps.bookings.models import Booking
from .models import Notification
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

@receiver(post_save, sender=User)
def welcome_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            user=instance,
            title="Welcome 🎉",
            message="Your account has been successfully created.",
            notification_type="system",
            target_audience="user",
        )

        html_content = render_to_string("emails/welcome_user.html", {"user": instance})
        msg = EmailMultiAlternatives(
            subject="Welcome to Apartment Booking",
            body="Your account has been successfully created.",  # fallback
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[instance.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

@receiver(post_save, sender=Apartment)
def apartment_verified_notification(sender, instance, **kwargs):
    try:
        old = Apartment.objects.get(pk=instance.pk)
    except Apartment.DoesNotExist:
        old = None

    if old and not old.is_verified and instance.is_verified:
        host = instance.host

        Notification.objects.create(
            user=host,
            title="Apartment Verified ✅",
            message=f"Your apartment '{instance.title}' has been verified by the admin.",
            notification_type="apartment_approved",
            target_audience="user",
            apartment_id=instance.id,
        )

        html_content = render_to_string("emails/apartment_verified.html", {
            "user": host,
            "apartment": instance
        })

        msg = EmailMultiAlternatives(
            subject=f"Your Apartment Verified: {instance.title}",
            body=f"Your apartment '{instance.title}' has been verified.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[host.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)


@receiver(post_save, sender=ApartmentAvailability)
def apartment_available_notification(sender, instance, **kwargs):
    if not instance.is_available:
        return

    apartment = instance.apartment
    users = User.objects.all()
    notifications = []

    for user in users:
        notifications.append(Notification(
            user=user,
            title="Apartment Available 🏡",
            message=f"{apartment.title} is available on {instance.date}.",
            notification_type="apartment_available",
            target_audience="user",
            apartment_id=apartment.id,
        ))

        html_content = render_to_string("emails/apartment_available.html", {
            "user": user,
            "apartment": apartment,
            "availability": instance
        })

        msg = EmailMultiAlternatives(
            subject=f"Apartment Available: {apartment.title}",
            body=f"{apartment.title} is available on {instance.date}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

    Notification.objects.bulk_create(notifications)

@receiver(post_save, sender=Booking)
def booking_confirmed_notification(sender, instance, created, **kwargs):
    if created:
        guest = instance.user
        host = instance.apartment.host

        # Guest notification
        Notification.objects.create(
            user=guest,
            title="Booking Confirmed ✅",
            message=f"You successfully booked '{instance.apartment.title}'.",
            notification_type="booking_confirmed",
            target_audience="user",
            booking_id=instance.id,
            apartment_id=instance.apartment.id,
        )
        html_content = render_to_string("emails/booking_confirmed.html", {"user": guest, "booking": instance})
        msg = EmailMultiAlternatives(
            subject="Booking Confirmed",
            body=f"You booked {instance.apartment.title}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[guest.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

        # Host notification
        Notification.objects.create(
            user=host,
            title="New Booking Received 📝",
            message=f"{guest.first_name} booked your apartment '{instance.apartment.title}'.",
            notification_type="booking_created",
            target_audience="user",
            booking_id=instance.id,
            apartment_id=instance.apartment.id,
        )
        html_content_host = render_to_string("emails/booking_confirmed.html", {"user": host, "booking": instance})
        msg_host = EmailMultiAlternatives(
            subject=f"New Booking Received: {instance.apartment.title}",
            body=f"{guest.first_name} booked your apartment '{instance.apartment.title}'.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[host.email],
        )
        msg_host.attach_alternative(html_content_host, "text/html")
        msg_host.send(fail_silently=False)


@receiver(post_save, sender=Booking)
def booking_cancelled_notification(sender, instance, **kwargs):
    if instance.status != "cancelled":
        return

    guest = instance.user
    host = instance.apartment.host

    # Guest
    Notification.objects.create(
        user=guest,
        title="Booking Cancelled ❌",
        message=f"You cancelled your booking for '{instance.apartment.title}'.",
        notification_type="booking_cancelled",
        target_audience="user",
        booking_id=instance.id,
        apartment_id=instance.apartment.id,
    )
    html_content_guest = render_to_string("emails/booking_cancelled.html", {"user": guest, "booking": instance})
    msg = EmailMultiAlternatives(
        subject="Booking Cancelled",
        body=f"You cancelled your booking for {instance.apartment.title}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[guest.email],
    )
    msg.attach_alternative(html_content_guest, "text/html")
    msg.send(fail_silently=False)

    # Host
    Notification.objects.create(
        user=host,
        title="Booking Cancelled ❌",
        message=f"{guest.first_name} cancelled their booking for '{instance.apartment.title}'.",
        notification_type="booking_cancelled",
        target_audience="user",
        booking_id=instance.id,
        apartment_id=instance.apartment.id,
    )
    html_content_host = render_to_string("emails/booking_cancelled.html", {"user": host, "booking": instance})
    msg_host = EmailMultiAlternatives(
        subject="Booking Cancelled",
        body=f"{guest.first_name} cancelled their booking for {instance.apartment.title}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[host.email],
    )
    msg_host.attach_alternative(html_content_host, "text/html")
    msg_host.send(fail_silently=False)
