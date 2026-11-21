from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("myapp", "0012_map_appointment_courses"),
    ]

    operations = [
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
