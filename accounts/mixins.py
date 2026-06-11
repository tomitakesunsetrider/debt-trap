"""Role-based access mixins for class-based views."""
from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only allow authenticated admin-role users."""

    raise_exception = True

    def test_func(self) -> bool:
        user = self.request.user
        return bool(user.is_authenticated and getattr(user, "is_admin_role", False))


class EndUserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only allow authenticated end-user-role users."""

    raise_exception = True

    def test_func(self) -> bool:
        user = self.request.user
        return bool(user.is_authenticated and getattr(user, "is_end_user_role", False))
