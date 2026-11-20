from django.db import migrations


COURSES = [
    {
        "name": "Automatic Car Lessons",
        "slug": "automatic-car-lessons",
        "description": "Learn to operate an automatic car and handle everyday road situations safely.",
        "duration_weeks": 3,
        "display_order": 1,
    },
    {
        "name": "Highway Driving Lesson",
        "slug": "highway-driving-lesson",
        "description": "Practise safe lane changes, following distances, and hazard awareness on faster roads.",
        "duration_weeks": 3,
        "display_order": 2,
    },
    {
        "name": "International Driving",
        "slug": "international-driving",
        "description": "Prepare for driving abroad with guidance on road signs, local rules, and safe habits.",
        "duration_weeks": 3,
        "display_order": 3,
    },
]


def seed_course_drafts(apps, schema_editor):
    Course = apps.get_model("myapp", "Course")
    database = schema_editor.connection.alias
    for course in COURSES:
        Course.objects.using(database).get_or_create(
            slug=course["slug"],
            defaults={
                **course,
                "price_kes": None,
                "is_active": False,
            },
        )


def remove_unedited_drafts(apps, schema_editor):
    Course = apps.get_model("myapp", "Course")
    database = schema_editor.connection.alias
    slugs = [course["slug"] for course in COURSES]
    Course.objects.using(database).filter(
        slug__in=slugs,
        price_kes__isnull=True,
        is_active=False,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("myapp", "0009_alter_course_price_kes_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_course_drafts, remove_unedited_drafts),
    ]
