from django.contrib import admin

from .models import (
    AppointmentBooking,
    ContactMessage,
    Course,
    CourseOrder,
    PaymentAttempt,
    Testimonial,
)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "price_kes", "duration_weeks", "is_active", "display_order")
    list_filter = ("is_active", "duration_weeks")
    list_editable = ("price_kes", "duration_weeks", "is_active", "display_order")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    ordering = ("display_order", "name")
    fieldsets = (
        ("Course details", {"fields": ("name", "slug", "description", "image")}),
        ("Pricing and availability", {"fields": ("price_kes", "duration_weeks", "is_active", "display_order")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


class PaymentAttemptInline(admin.TabularInline):
    model = PaymentAttempt
    extra = 0
    can_delete = False
    fields = (
        "id",
        "amount_kes",
        "phone_number",
        "status",
        "merchant_request_id",
        "checkout_request_id",
        "mpesa_receipt_number",
        "result_code",
        "result_description",
        "created_at",
        "completed_at",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(CourseOrder)
class CourseOrderAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "course",
        "customer_name",
        "phone_number",
        "amount_kes",
        "status",
        "created_at",
    )
    list_filter = ("status", "course", "created_at")
    search_fields = ("customer_name", "customer_email", "phone_number")
    readonly_fields = (
        "reference",
        "course",
        "customer_name",
        "customer_email",
        "phone_number",
        "amount_kes",
        "status",
        "created_at",
        "updated_at",
        "paid_at",
    )
    inlines = (PaymentAttemptInline,)
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "amount_kes",
        "phone_number",
        "status",
        "mpesa_receipt_number",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = (
        "order__customer_name",
        "order__phone_number",
        "checkout_request_id",
        "mpesa_receipt_number",
    )
    readonly_fields = (
        "order",
        "amount_kes",
        "phone_number",
        "status",
        "merchant_request_id",
        "checkout_request_id",
        "mpesa_receipt_number",
        "result_code",
        "result_description",
        "created_at",
        "updated_at",
        "completed_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = (
        "customer_name",
        "course_taken",
        "consent_confirmed",
        "is_approved",
        "display_order",
        "created_at",
    )
    list_filter = ("consent_confirmed", "is_approved", "created_at")
    list_editable = ("consent_confirmed", "is_approved", "display_order")
    search_fields = ("customer_name", "course_taken", "review")
    readonly_fields = ("created_at",)
    ordering = ("display_order", "-created_at")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "email", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("subject", "name", "email", "message")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(AppointmentBooking)
class AppointmentBookingAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "vehicle", "preferred_date", "preferred_time", "status", "created_at")
    list_filter = ("status", "course", "vehicle", "preferred_date")
    search_fields = ("name", "email")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
