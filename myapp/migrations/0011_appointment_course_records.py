from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


COURSES = [
    {
        "name": "Beginner driving course",
        "slug": "beginner-driving-course",
        "description": "Learn vehicle controls, road signs, and the foundations of safe driving.",
        "display_order": 1,
    },
    {
        "name": "Refresher course",
        "slug": "refresher-course",
        "description": "Refresh your knowledge of road rules and practise your driving skills.",
        "display_order": 2,
    },
    {
        "name": "Defensive driving",
        "slug": "defensive-driving",
        "description": "Build hazard awareness and practise anticipating risks on the road.",
        "display_order": 3,
    },
    {
        "name": "Advanced driving course",
        "slug": "advanced-driving-course",
        "description": "Develop confident driving skills for more demanding road situations.",
        "display_order": 4,
    },
]

OLD_COURSE_SLUGS = {
    "beginner": "beginner-driving-course",
    "refresher": "refresher-course",
    "defensive": "defensive-driving",
    "advanced": "advanced-driving-course",
}


def create_courses_and_map_bookings(apps, schema_editor):
    Course = apps.get_model("myapp", "Course")
    Booking = apps.get_model("myapp", "AppointmentBooking")
    database = schema_editor.connection.alias

    # The three rows were generated as unpriced inactive drafts. Remove only
    # untouched rows so any admin edits remain intact.
    Course.objects.using(database).filter(
        slug__in=[
            "automatic-car-lessons",
            "highway-driving-lesson",
            "international-driving",
        ],
        price_kes__isnull=True,
        is_active=False,
    ).delete()

    for details in COURSES:
        course, _ = Course.objects.using(database).get_or_create(
            slug=details["slug"],
            defaults={
                **details,
                "price_kes": None,
                "duration_weeks": None,
                "is_active": True,
            },
        )
        # These four records are the appointment choices. Keep them active,
        # and preserve any price or duration already entered by an admin.
        if not course.is_active:
            Course.objects.using(database).filter(pk=course.pk).update(is_active=True)

    for old_value, slug in OLD_COURSE_SLUGS.items():
        course_id = Course.objects.using(database).get(slug=slug).pk
        Booking.objects.using(database).filter(course=old_value).update(
            course_record_id=course_id
        )

    if Booking.objects.using(database).filter(course_record__isnull=True).exists():
        raise RuntimeError("An appointment has an unknown course value; refusing to lose it.")


class Migration(migrations.Migration):
    dependencies = [
        ("myapp", "0010_seed_course_drafts"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="course",
            name="active_course_requires_price",
        ),
        migrations.AlterField(
            model_name="course",
            name="duration_weeks",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[django.core.validators.MinValueValidator(1)],
            ),
        ),
        migrations.AddField(
            model_name="appointmentbooking",
            name="course_record",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="legacy_appointment_bookings",
                to="myapp.course",
            ),
        ),
        migrations.RunPython(create_courses_and_map_bookings, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="appointmentbooking",
            name="course",
        ),
        migrations.RenameField(
            model_name="appointmentbooking",
            old_name="course_record",
            new_name="course",
        ),
        migrations.AlterField(
            model_name="appointmentbooking",
            name="course",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="appointment_bookings",
                to="myapp.course",
            ),
        ),
    ]
