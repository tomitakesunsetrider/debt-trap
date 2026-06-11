"""Deterministic mock-payment outcome rules.

A charge result is determined by the card number's last four digits and the
amount. Decoupled from view / serializer code so it can be unit tested.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


# Last-4 -> (error_code, error_message)
LAST4_DECLINE_TABLE: dict[str, tuple[str, str]] = {
    "0000": ("card_declined", "The card was declined."),
    "0001": ("insufficient_funds", "The card has insufficient funds."),
    "0002": ("expired_card", "The card has expired."),
    "0119": ("processing_error", "An error occurred while processing the card."),
}

AMOUNT_TOO_LARGE_THRESHOLD = Decimal("1000000")


@dataclass(frozen=True)
class ChargeOutcome:
    succeeded: bool
    error_code: str = ""
    error_message: str = ""


def extract_last4(card_number: str) -> str:
    digits = "".join(ch for ch in (card_number or "") if ch.isdigit())
    return digits[-4:] if len(digits) >= 4 else ""


def evaluate_charge(amount: Decimal, card_number: str) -> ChargeOutcome:
    """Decide whether a charge succeeds or fails based on test rules."""
    last4 = extract_last4(card_number)
    if last4 in LAST4_DECLINE_TABLE:
        code, message = LAST4_DECLINE_TABLE[last4]
        return ChargeOutcome(succeeded=False, error_code=code, error_message=message)

    if amount >= AMOUNT_TOO_LARGE_THRESHOLD:
        return ChargeOutcome(
            succeeded=False,
            error_code="amount_too_large",
            error_message="The amount exceeds the allowed maximum.",
        )

    return ChargeOutcome(succeeded=True)
