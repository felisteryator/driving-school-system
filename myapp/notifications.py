import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_appointment_notifications(booking):
    date = booking.preferred_date.strftime("%A, %B %d, %Y")
    time = booking.preferred_time.strftime("%I:%M %p")
    course = booking.course.name
    vehicle = booking.get_vehicle_display()

    messages = [
        (
            "We received your appointment request",
            (
                f"Hello {booking.name},\n\n"
                "We received your driving lesson appointment request. It is pending "
                "confirmation by our team.\n\n"
                f"Requested date: {date}\n"
                f"Requested time: {time}\n"
                f"Course: {course}\n"
                f"Vehicle: {vehicle}\n\n"
                "We will contact you to confirm your appointment."
            ),
            [booking.email],
        ),
        (
            "New driving lesson appointment request",
            (
                "A new appointment request was submitted.\n\n"
                f"Name: {booking.name}\n"
                f"Email: {booking.email}\n"
                f"Course: {course}\n"
                f"Vehicle: {vehicle}\n"
                f"Requested date: {date}\n"
                f"Requested time: {time}\n"
                f"Message: {booking.message or '(none)'}\n\n"
                "Review and manage this request in the Django admin."
            ),
            [settings.APPOINTMENT_NOTIFICATION_EMAIL],
        ),
    ]

    for subject, body, recipients in messages:
        try:
            sent = send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                recipients,
                fail_silently=False,
            )
            if not sent:
                logger.error("Appointment notification was not sent: %s", subject)
        except Exception:
            # Keep a saved booking successful even if the mail server is unavailable.
            logger.exception("Could not send appointment notification: %s", subject)
