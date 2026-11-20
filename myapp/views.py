from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import AppointmentBookingForm, ContactMessageForm, CourseCheckoutForm
from .models import (
    AppointmentBooking,
    Course,
    CourseOrder,
    PaymentAttempt,
    Testimonial,
)
from .mpesa import MpesaAPIError, MpesaConfigurationError, initiate_stk_push
from .mpesa_callbacks import mpesa_callback
from .notifications import send_appointment_notifications

# Create your views here.
def about(request):
    return render(request, 'about.html')
def appointment(request):
    if request.method == "POST":
        form = AppointmentBookingForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    booking = form.save()
            except IntegrityError:
                slot_is_taken = AppointmentBooking.objects.filter(
                    preferred_date=form.cleaned_data["preferred_date"],
                    preferred_time=form.cleaned_data["preferred_time"],
                ).exclude(status=AppointmentBooking.Status.CANCELLED).exists()
                if not slot_is_taken:
                    raise
                form.add_error(
                    "preferred_time",
                    "That date and time was just requested. Please choose another slot.",
                )
            else:
                send_appointment_notifications(booking)
                return redirect("myapp:appointment_success")
    else:
        form = AppointmentBookingForm()

    return render(request, "appointment.html", {"form": form})


def appointment_success(request):
    return render(request, "appointment_success.html")
def contact(request):
    if request.method == "POST":
        form = ContactMessageForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("myapp:contact_success")
    else:
        form = ContactMessageForm()

    return render(request, "contact.html", {"form": form})


def contact_success(request):
    return render(request, "contact_success.html")
def courses(request):
    courses = Course.objects.filter(is_active=True)
    return render(request, "courses.html", {"courses": courses})


def course_checkout(request, slug):
    course = get_object_or_404(
        Course, slug=slug, is_active=True, price_kes__gt=0
    )
    if request.method == "POST":
        form = CourseCheckoutForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                order = CourseOrder.objects.create(
                    course=course,
                    customer_name=form.cleaned_data["customer_name"],
                    customer_email=form.cleaned_data["customer_email"],
                    phone_number=form.cleaned_data["phone_number"],
                    amount_kes=course.price_kes,
                )
                PaymentAttempt.objects.create(
                    order=order,
                    amount_kes=order.amount_kes,
                    phone_number=order.phone_number,
                )
            return redirect("myapp:course_order_status", reference=order.reference)
    else:
        form = CourseCheckoutForm()

    return render(
        request,
        "course_checkout.html",
        {"course": course, "form": form},
    )


def course_order_status(request, reference):
    order = get_object_or_404(
        CourseOrder.objects.select_related("course"),
        reference=reference,
    )
    payment_attempt = order.payment_attempts.first()
    return render(
        request,
        "course_order_status.html",
        {"order": order, "payment_attempt": payment_attempt},
    )


@require_POST
def initiate_course_payment(request, reference):
    with transaction.atomic():
        order = get_object_or_404(
            CourseOrder.objects.select_for_update().select_related("course"),
            reference=reference,
        )
        if order.status == CourseOrder.Status.PAID:
            return redirect("myapp:course_order_status", reference=order.reference)

        payment_attempt = order.payment_attempts.select_for_update().first()
        if payment_attempt and payment_attempt.status in {
            PaymentAttempt.Status.PENDING,
            PaymentAttempt.Status.SUCCEEDED,
        }:
            return redirect("myapp:course_order_status", reference=order.reference)

        if payment_attempt is None or payment_attempt.status != PaymentAttempt.Status.CREATED:
            payment_attempt = PaymentAttempt.objects.create(
                order=order,
                amount_kes=order.amount_kes,
                phone_number=order.phone_number,
            )

        # Reserve this attempt before making a network request so repeated
        # clicks do not submit the same attempt twice.
        payment_attempt.status = PaymentAttempt.Status.PENDING
        payment_attempt.result_description = "Sending payment request to M-PESA."
        payment_attempt.save(update_fields=["status", "result_description", "updated_at"])

    try:
        response = initiate_stk_push(payment_attempt)
    except (MpesaConfigurationError, MpesaAPIError) as exc:
        if isinstance(exc, MpesaAPIError) and exc.outcome_unknown:
            payment_attempt.status = PaymentAttempt.Status.UNKNOWN
        else:
            payment_attempt.status = PaymentAttempt.Status.FAILED
        payment_attempt.result_description = str(exc)
        payment_attempt.save(update_fields=["status", "result_description", "updated_at"])
        return redirect("myapp:course_order_status", reference=order.reference)

    response_code = str(response.get("ResponseCode", ""))
    payment_attempt.merchant_request_id = response.get("MerchantRequestID") or None
    payment_attempt.checkout_request_id = response.get("CheckoutRequestID") or None
    payment_attempt.result_code = response_code
    payment_attempt.result_description = (
        response.get("CustomerMessage")
        or response.get("ResponseDescription")
        or ""
    )
    if response_code != "0":
        payment_attempt.status = PaymentAttempt.Status.FAILED
    payment_attempt.save(
        update_fields=[
            "merchant_request_id",
            "checkout_request_id",
            "result_code",
            "result_description",
            "status",
            "updated_at",
        ]
    )
    return redirect("myapp:course_order_status", reference=order.reference)
def feature(request):
    return render(request, 'feature.html')
def home(request):
    courses = Course.objects.filter(is_active=True)
    testimonials = Testimonial.objects.filter(
        consent_confirmed=True,
        is_approved=True,
    )
    return render(
        request,
        "index.html",
        {"courses": courses, "testimonials": testimonials},
    )
def team(request):
    return render(request, 'team.html')
def testimonial(request):
    testimonials = Testimonial.objects.filter(
        consent_confirmed=True,
        is_approved=True,
    )
    return render(request, "testimonial.html", {"testimonials": testimonials})
