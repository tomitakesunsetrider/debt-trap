"""Seed the database with a handful of demo users and transactions.

Useful for manual UI walkthroughs:

    python manage.py seed_demo
"""
from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from payments.services import create_charge, create_refund

User = get_user_model()


DEMO_ADMIN = ("demo_admin", "demo_admin@example.com", "Comp1ex-Passw0rd!")
DEMO_USERS = [
    ("alice", "alice@example.com", "Comp1ex-Passw0rd!"),
    ("bob", "bob@example.com", "Comp1ex-Passw0rd!"),
]


class Command(BaseCommand):
    help = "Create demo admin / end users and a few sample transactions."

    def handle(self, *args, **options):
        admin_user, created = User.objects.get_or_create(
            username=DEMO_ADMIN[0],
            defaults={
                "email": DEMO_ADMIN[1],
                "role": User.ROLE_ADMIN,
                "is_staff": True,
            },
        )
        if created:
            admin_user.set_password(DEMO_ADMIN[2])
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f"Created admin: {admin_user.username}"))

        for username, email, password in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "role": User.ROLE_END_USER},
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created user: {user.username}"))

            tx = create_charge(
                user,
                amount=Decimal("1500"),
                currency="JPY",
                card_number="4242424242424242",
                description="Demo successful charge",
            )
            create_charge(
                user,
                amount=Decimal("2000"),
                currency="JPY",
                card_number="4000000000000000",
                description="Demo declined charge",
            )
            create_refund(
                user,
                transaction_id=tx.transaction_id,
                reason="Demo refund",
            )

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
