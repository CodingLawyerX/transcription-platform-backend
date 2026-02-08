from django.contrib.auth.hashers import make_password
from django.db import migrations


USERNAME = "steffen_test"
EMAIL = "mail@steffen-gross.de"
PASSWORD = "TestPassword123!"


def create_default_user(apps, schema_editor):
    user_model = apps.get_model("users", "User")
    email_model = apps.get_model("account", "EmailAddress")

    user, _ = user_model.objects.get_or_create(
        username=USERNAME,
        defaults={
            "email": EMAIL,
            "name": "Steffen Gross",
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
        },
    )

    # Ensure fields stay in sync even if the user already existed
    user.email = EMAIL
    user.name = "Steffen Gross"
    user.is_active = True
    user.password = make_password(PASSWORD)
    user.save()

    email_entry, _ = email_model.objects.get_or_create(
        user=user,
        email=EMAIL,
        defaults={
            "verified": True,
            "primary": True,
        },
    )

    if not email_entry.verified or not email_entry.primary:
        email_entry.verified = True
        email_entry.primary = True
        email_entry.save()


def remove_default_user(apps, schema_editor):
    user_model = apps.get_model("users", "User")
    user_model.objects.filter(username=USERNAME, email=EMAIL).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
        ("account", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_user, remove_default_user),
    ]
