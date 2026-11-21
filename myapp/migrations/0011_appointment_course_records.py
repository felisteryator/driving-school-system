from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


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
    ]
