"""Bootstrap command to create the first admin user without using the web UI.

Usage:
    python manage.py createadmin --username admin --email admin@example.com

If --password is omitted, the command will prompt for it interactively.
"""
from __future__ import annotations

import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = "Create an admin-role user (for initial bootstrap)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument(
            "--password",
            default=None,
            help="If omitted, the command will prompt for one.",
        )

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]
        password = options["password"]

        if User.objects.filter(username=username).exists():
            raise CommandError(f"User '{username}' already exists.")

        if not password:
            password = getpass.getpass("Password: ")
            confirm = getpass.getpass("Password (again): ")
            if password != confirm:
                raise CommandError("Passwords do not match.")
        if not password:
            raise CommandError("Password is required.")

        user = User(
            username=username,
            email=email,
            role=User.ROLE_ADMIN,
            is_staff=True,
            is_superuser=False,
        )
        user.set_password(password)
        user.save()

        self.stdout.write(
            self.style.SUCCESS(f"Admin user '{username}' has been created.")
        )
