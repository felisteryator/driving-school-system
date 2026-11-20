import uuid

from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "contact message"
        verbose_name_plural = "contact messages"

    def __str__(self):
        return f"{self.subject} — {self.name}"


class Testimonial(models.Model):
    customer_name = models.CharField(max_length=120)
    course_taken = models.CharField(max_length=120, blank=True)
    review = models.TextField()
    photo = models.ImageField(upload_to="testimonials/", blank=True)
    photo_url = models.URLField(blank=True)
    consent_confirmed = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False, db_index=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "-created_at"]
        verbose_name = "testimonial"
        verbose_name_plural = "testimonials"

    def __str__(self):
        return f"Review by {self.customer_name}"


class Course(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField()
    price_kes = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        blank=True,
        null=True,
        help_text="Course price in whole Kenyan shillings (KSh).",
    )
    duration_weeks = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        blank=True,
        null=True,
    )
    image = models.ImageField(upload_to="courses/", blank=True)
    is_active = models.BooleanField(default=False, db_index=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class CourseOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending payment"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    customer_name = models.CharField(max_length=120)
    customer_email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=16)
    amount_kes = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Price copied from the course when the order is created.",
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.reference} - {self.course.name}"


class PaymentAttempt(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        TIMED_OUT = "timed_out", "Timed out"
        UNKNOWN = "unknown", "Unknown result"

    order = models.ForeignKey(
        CourseOrder,
        on_delete=models.CASCADE,
        related_name="payment_attempts",
    )
    amount_kes = models.PositiveIntegerField()
    phone_number = models.CharField(max_length=16)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.CREATED,
        db_index=True,
    )
    merchant_request_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )
    checkout_request_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )
    mpesa_receipt_number = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        unique=True,
    )
    result_code = models.CharField(max_length=30, blank=True)
    result_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment attempt for order {self.order.reference} ({self.get_status_display()})"


class AppointmentBooking(models.Model):
    class Vehicle(models.TextChoices):
        MANUAL = "manual", "Manual"
        AUTOMATIC = "automatic", "Automatic"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    name = models.CharField(max_length=120)
    email = models.EmailField()
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="appointment_bookings",
    )
    vehicle = models.CharField(max_length=20, choices=Vehicle.choices)
    preferred_date = models.DateField()
    preferred_time = models.TimeField()
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "appointment booking"
        verbose_name_plural = "appointment bookings"
        constraints = [
            models.UniqueConstraint(
                fields=["preferred_date", "preferred_time"],
                condition=Q(status__in=["pending", "confirmed"]),
                name="unique_active_appointment_slot",
            )
        ]

    def __str__(self):
        return f"{self.name} — {self.course.name} on {self.preferred_date}"
