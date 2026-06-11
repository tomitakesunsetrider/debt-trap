"""Forms for sign-up, admin user CRUD, and bootstrap-style widgets."""
from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserCreationForm,
)

User = get_user_model()


def _apply_form_control(fields):
    """Add Bootstrap `form-control` class to each form field widget."""
    for field in fields.values():
        widget = field.widget
        css_class = widget.attrs.get("class", "")
        if isinstance(widget, forms.CheckboxInput):
            new_class = (css_class + " form-check-input").strip()
        else:
            new_class = (css_class + " form-control").strip()
        widget.attrs["class"] = new_class


class BootstrapAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_form_control(self.fields)


class EndUserSignupForm(UserCreationForm):
    """Public sign-up form. Always creates an end-user-role account."""

    email = forms.EmailField(label="メールアドレス", required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_form_control(self.fields)

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        user.role = User.ROLE_END_USER
        if commit:
            user.save()
        return user


class AdminUserCreateForm(UserCreationForm):
    """Form used by an admin to create another admin."""

    email = forms.EmailField(label="メールアドレス", required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_form_control(self.fields)

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        user.role = User.ROLE_ADMIN
        if commit:
            user.save()
        return user


class AdminUserUpdateForm(forms.ModelForm):
    """Update form for admin users (no password change here)."""

    class Meta:
        model = User
        fields = ("username", "email", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_form_control(self.fields)
