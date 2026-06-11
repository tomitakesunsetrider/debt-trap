"""Service layer for charge and refund operations.

Keeps domain logic (rules, persistence, validation) separate from HTTP
serialization so it can be reused and unit-tested in isolation.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction as db_transaction

from accounts.models import User
from payments.exceptions import (
    AlreadyRefunded,
    RefundAmountExceeded,
    RefundNotAllowed,
    TransactionNotFound,
)
from payments.models import Transaction
from payments.rules import evaluate_charge, extract_last4


def create_charge(
    user: User,
    *,
    amount: Decimal,
    currency: str,
    card_number: str,
    description: str = "",
) -> Transaction:
    """Apply mock-payment rules and persist a `charge` transaction."""
    outcome = evaluate_charge(amount=amount, card_number=card_number)
    last4 = extract_last4(card_number)

    tx = Transaction.objects.create(
        user=user,
        kind=Transaction.KIND_CHARGE,
        amount=amount,
        currency=currency.upper(),
        card_last4=last4,
        status=(
            Transaction.STATUS_SUCCEEDED if outcome.succeeded else Transaction.STATUS_FAILED
        ),
        error_code=outcome.error_code,
        error_message=outcome.error_message,
        description=description or "",
    )
    return tx


@db_transaction.atomic
def create_refund(
    user: User,
    *,
    transaction_id: str,
    amount: Decimal | None = None,
    reason: str = "",
) -> Transaction:
    """Validate refund rules and persist a `refund` transaction."""
    try:
        original = (
            Transaction.objects.select_for_update()
            .get(transaction_id=transaction_id, user=user)
        )
    except Transaction.DoesNotExist as exc:
        raise TransactionNotFound("The specified transaction was not found.") from exc

    if original.kind != Transaction.KIND_CHARGE:
        raise RefundNotAllowed("Only charge transactions can be refunded.")
    if not original.is_succeeded:
        raise RefundNotAllowed("Only succeeded charges can be refunded.")
    if Transaction.objects.filter(
        related_transaction=original,
        kind=Transaction.KIND_REFUND,
        status=Transaction.STATUS_SUCCEEDED,
    ).exists():
        raise AlreadyRefunded("This transaction has already been refunded.")

    refund_amount = amount if amount is not None else original.amount
    if refund_amount <= 0:
        raise RefundAmountExceeded("Refund amount must be greater than 0.")
    if refund_amount > original.amount:
        raise RefundAmountExceeded(
            "Refund amount exceeds the original charge amount."
        )

    refund = Transaction.objects.create(
        user=user,
        kind=Transaction.KIND_REFUND,
        amount=refund_amount,
        currency=original.currency,
        card_last4=original.card_last4,
        status=Transaction.STATUS_SUCCEEDED,
        related_transaction=original,
        reason=reason or "",
    )
    return refund


def get_user_transaction(user: User, transaction_id: str) -> Transaction:
    try:
        return Transaction.objects.select_related("related_transaction").get(
            transaction_id=transaction_id, user=user
        )
    except Transaction.DoesNotExist as exc:
        raise TransactionNotFound("The specified transaction was not found.") from exc
