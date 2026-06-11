from django.contrib import admin

from payments.models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_id",
        "user",
        "kind",
        "status",
        "amount",
        "currency",
        "created_at",
    )
    list_filter = ("kind", "status", "currency")
    search_fields = ("transaction_id", "user__username", "user__email")
    readonly_fields = ("transaction_id", "created_at")
