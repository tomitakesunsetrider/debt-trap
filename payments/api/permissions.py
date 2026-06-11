from __future__ import annotations

from rest_framework import permissions


class IsEndUser(permissions.BasePermission):
    """Only authenticated end-user-role accounts can call the payment API."""

    message = "Only end users can call the payment API."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if user is None or not getattr(user, "is_authenticated", False):
            return False
        return bool(getattr(user, "is_end_user_role", False))
