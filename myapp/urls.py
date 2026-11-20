from django.urls import path

from . import views

app_name = "myapp"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("appointment/success/", views.appointment_success, name="appointment_success"),
    path("appointment/", views.appointment, name="appointment"),
    path("contact/success/", views.contact_success, name="contact_success"),
    path("contact/", views.contact, name="contact"),
    path("checkout/<slug:slug>/", views.course_checkout, name="course_checkout"),
    path("courses/", views.courses, name="courses"),
    path("feature/", views.feature, name="feature"),
    path("orders/<uuid:reference>/pay/", views.initiate_course_payment, name="initiate_course_payment"),
    path("orders/<uuid:reference>/", views.course_order_status, name="course_order_status"),
    path("payments/mpesa/callback/", views.mpesa_callback, name="mpesa_callback"),
    path("team/", views.team, name="team"),
    path("testimonial/", views.testimonial, name="testimonial"),
]
