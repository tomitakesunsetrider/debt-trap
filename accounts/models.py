"""Custom user model for debt-trap.

The `User` model adds two project-specific attributes on top of Django's
`AbstractUser`:

* `role`: distinguishes "admin" (operators) from "end_user" (API consumers).
* `api_key`: secret string used to authenticate API requests. Only end users
  hold an API key; admin users are not allowed to call the payment API.
"""
from __future__ import annotations

import secrets

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone


API_KEY_PREFIX = "pk_live_"


def generate_api_key() -> str:
    """Return a fresh API key with the project-wide prefix."""
    return API_KEY_PREFIX + secrets.token_urlsafe(32)


class DebtTrapUserManager(UserManager):
    """Manager that ensures `createsuperuser` produces an admin-role user."""

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", User.ROLE_ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    ROLE_ADMIN = "admin"
    ROLE_END_USER = "end_user"
    ROLE_CHOICES = (
        (ROLE_ADMIN, "管理者"),
        (ROLE_END_USER, "一般ユーザー"),
    )

    email = models.EmailField("メールアドレス", unique=True)
    role = models.CharField(
        "ロール",
        max_length=16,
        choices=ROLE_CHOICES,
        default=ROLE_END_USER,
    )
    api_key = models.CharField(
        "APIキー",
        max_length=64,
        unique=True,
        null=True,
        blank=True,
    )
    api_key_issued_at = models.DateTimeField(
        "APIキー発行日時",
        null=True,
        blank=True,
    )

    objects = DebtTrapUserManager()

    class Meta:
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー"
        ordering = ("-date_joined",)

    @property
    def is_admin_role(self) -> bool:
        return self.role == self.ROLE_ADMIN

    @property
    def is_end_user_role(self) -> bool:
        return self.role == self.ROLE_END_USER

    def issue_api_key(self) -> str:
        """Generate a new API key and stamp the issuance time.

        Caller is responsible for saving the instance.
        """
        new_key = generate_api_key()
        self.api_key = new_key
        self.api_key_issued_at = timezone.now()
        return new_key

    def clear_api_key(self) -> None:
        self.api_key = None
        self.api_key_issued_at = None

    def save(self, *args, **kwargs):
        if self.is_admin_role:
            self.clear_api_key()
        elif self.is_end_user_role and not self.api_key:
            self.issue_api_key()
        super().save(*args, **kwargs)
