from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

User = get_user_model()


@admin.register(User)
class DebtTrapUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email")

    fieldsets = UserAdmin.fieldsets + (
        ("debt-trap", {"fields": ("role", "api_key", "api_key_issued_at")}),
    )
    readonly_fields = ("api_key", "api_key_issued_at")
