"""Domain-level exceptions thrown from the payments service layer.

The DRF exception handler in `payments.api.exception_handler` converts these
into the project-wide error envelope.
"""
from __future__ import annotations


class PaymentDomainError(Exception):
    """Base class for payment-domain errors with a stable machine code."""

    code: str = "internal_error"
    status_code: int = 500

    def __init__(self, message: str = "", *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message or self.__class__.__doc__ or ""
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class TransactionNotFound(PaymentDomainError):
    """The requested transaction does not exist or is not yours."""

    code = "transaction_not_found"
    status_code = 404


class RefundNotAllowed(PaymentDomainError):
    """Only succeeded charges can be refunded."""

    code = "refund_not_allowed"
    status_code = 422


class AlreadyRefunded(PaymentDomainError):
    """This transaction has already been refunded."""

    code = "already_refunded"
    status_code = 409


class RefundAmountExceeded(PaymentDomainError):
    """Refund amount exceeds the original charge amount."""

    code = "refund_amount_exceeded"
    status_code = 400
