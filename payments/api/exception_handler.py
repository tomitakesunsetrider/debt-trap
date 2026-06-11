"""Translate DRF / domain exceptions into the project-wide error envelope."""
from __future__ import annotations

from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

from payments.exceptions import PaymentDomainError


def _envelope(code: str, message: str, details: dict | None = None) -> dict:
    body: dict = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


def api_exception_handler(exc, context):
    if isinstance(exc, PaymentDomainError):
        return Response(
            _envelope(exc.code, exc.message),
            status=exc.status_code,
        )

    response = drf_default_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, exceptions.AuthenticationFailed) or isinstance(
        exc, exceptions.NotAuthenticated
    ):
        return Response(
            _envelope("unauthorized", str(exc.detail) if hasattr(exc, "detail") else "Unauthorized."),
            status=status.HTTP_401_UNAUTHORIZED,
        )
    if isinstance(exc, exceptions.PermissionDenied):
        return Response(
            _envelope("forbidden", str(exc.detail)),
            status=status.HTTP_403_FORBIDDEN,
        )
    if isinstance(exc, exceptions.NotFound):
        return Response(
            _envelope("not_found", str(exc.detail)),
            status=status.HTTP_404_NOT_FOUND,
        )
    if isinstance(exc, exceptions.ValidationError):
        details = exc.detail
        return Response(
            _envelope("validation_error", "Request validation failed.", details),
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        _envelope("internal_error", "An unexpected error has occurred."),
        status=response.status_code,
    )
