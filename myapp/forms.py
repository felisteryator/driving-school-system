from datetime import datetime
import re

from django import forms
from django.utils import timezone

from .models import AppointmentBooking, ContactMessage, Course


class ContactMessageForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message"]
        widgets = {
            "name": forms.TextInput(
                attrs={"autocomplete": "name", "placeholder": "Your name"}
            ),
            "email": forms.EmailInput(
                attrs={"autocomplete": "email", "placeholder": "Your email"}
            ),
            "subject": forms.TextInput(attrs={"placeholder": "Subject"}),
            "message": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Write your message",
                    "style": "height: 150px",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control border-0 bg-light"


class CourseCheckoutForm(forms.Form):
    customer_name = forms.CharField(
        max_length=120,
        label="Your name",
        widget=forms.TextInput(
            attrs={"class": "form-control border-0 bg-light", "autocomplete": "name"}
        ),
    )
    customer_email = forms.EmailField(
        required=False,
        label="Email address (optional)",
        widget=forms.EmailInput(
            attrs={"class": "form-control border-0 bg-light", "autocomplete": "email"}
        ),
    )
    phone_number = forms.CharField(
        max_length=20,
        label="M-PESA phone number",
        widget=forms.TelInput(
            attrs={
                "class": "form-control border-0 bg-light",
                "autocomplete": "tel",
                "placeholder": "07XXXXXXXX or 2547XXXXXXXX",
            }
        ),
    )

    def clean_phone_number(self):
        phone_number = re.sub(r"[\s()+-]", "", self.cleaned_data["phone_number"])
        if phone_number.startswith("0") and len(phone_number) == 10:
            phone_number = "254" + phone_number[1:]
        if not re.fullmatch(r"254[17]\d{8}", phone_number):
            raise forms.ValidationError(
                "Enter a valid Kenyan mobile number, such as 0712345678."
            )
        return phone_number


class AppointmentBookingForm(forms.ModelForm):
    class Meta:
        model = AppointmentBooking
        fields = [
            "name",
            "email",
            "course",
            "vehicle",
            "preferred_date",
            "preferred_time",
            "message",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"autocomplete": "name", "placeholder": "Your name"}
            ),
            "email": forms.EmailInput(
                attrs={"autocomplete": "email", "placeholder": "Your email"}
            ),
            "preferred_date": forms.DateInput(attrs={"type": "date"}),
            "preferred_time": forms.TimeInput(attrs={"type": "time"}),
            "message": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs["class"] = f"{css_class} border-0 bg-light"
        self.fields["course"].queryset = Course.objects.filter(is_active=True)
        self.fields["preferred_date"].widget.attrs["min"] = timezone.localdate().isoformat()

    def clean_preferred_date(self):
        preferred_date = self.cleaned_data["preferred_date"]
        if preferred_date < timezone.localdate():
            raise forms.ValidationError("Choose today or a future date.")
        return preferred_date

    def clean(self):
        cleaned_data = super().clean()
        preferred_date = cleaned_data.get("preferred_date")
        preferred_time = cleaned_data.get("preferred_time")

        if preferred_date and preferred_time:
            requested_slot = timezone.make_aware(
                datetime.combine(preferred_date, preferred_time),
                timezone.get_current_timezone(),
            )
            if requested_slot <= timezone.localtime():
                self.add_error("preferred_time", "Choose a future time.")
                return cleaned_data

            slot_is_taken = AppointmentBooking.objects.filter(
                preferred_date=preferred_date,
                preferred_time=preferred_time,
            ).exclude(status=AppointmentBooking.Status.CANCELLED).exists()

            if slot_is_taken:
                self.add_error(
                    "preferred_time",
                    "That date and time is already requested. Please choose another slot.",
                )

        return cleaned_data
