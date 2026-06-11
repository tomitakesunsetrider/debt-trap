"""Transaction model for the mock payment API."""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


def _generate_transaction_id() -> str:
    return str(uuid.uuid4())


class Transaction(models.Model):
    KIND_CHARGE = "charge"
    KIND_REFUND = "refund"
    KIND_CHOICES = (
        (KIND_CHARGE, "Charge"),
        (KIND_REFUND, "Refund"),
    )

    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_SUCCEEDED, "Succeeded"),
        (STATUS_FAILED, "Failed"),
    )

    transaction_id = models.CharField(
        max_length=36,
        unique=True,
        default=_generate_transaction_id,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    card_last4 = models.CharField(max_length=4, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    error_code = models.CharField(max_length=32, blank=True)
    error_message = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    related_transaction = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="refunds",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["kind"]),
        ]

    def __str__(self) -> str:
        return f"{self.kind}:{self.transaction_id} ({self.status})"

    @property
    def is_succeeded(self) -> bool:
        return self.status == self.STATUS_SUCCEEDED

    @property
    def is_failed(self) -> bool:
        return self.status == self.STATUS_FAILED
