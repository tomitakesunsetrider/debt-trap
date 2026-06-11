"""API key authentication for the payment endpoints."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions

User = get_user_model()


class ApiKeyAuthentication(authentication.BaseAuthentication):
    """Authenticate users by the `X-API-Key` HTTP header.

    Only `end_user` role accounts can hold an API key. Admin accounts have
    `api_key = NULL` and therefore cannot authenticate here.
    """

    header_name = "HTTP_X_API_KEY"

    def authenticate(self, request):
        key = request.META.get(self.header_name)
        if not key:
            return None
        try:
            user = User.objects.get(api_key=key)
        except User.DoesNotExist as exc:
            raise exceptions.AuthenticationFailed("Invalid or missing API key.") from exc

        if not user.is_active:
            raise exceptions.AuthenticationFailed("This account is disabled.")
        if not user.is_end_user_role:
            raise exceptions.AuthenticationFailed("API keys are only valid for end users.")

        return (user, key)

    def authenticate_header(self, request):
        return "X-API-Key"
