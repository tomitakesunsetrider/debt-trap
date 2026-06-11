"""Serializers for payment API requests and responses."""
from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from payments.models import Transaction


SUPPORTED_CURRENCIES = {"JPY", "USD", "EUR", "GBP"}
ZERO_DECIMAL_CURRENCIES = {"JPY"}


class ChargeRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    currency = serializers.CharField(max_length=3)
    card_number = serializers.CharField(max_length=32)
    card_holder = serializers.CharField(max_length=64, required=False, allow_blank=True)
    card_exp_month = serializers.IntegerField(required=False, min_value=1, max_value=12)
    card_exp_year = serializers.IntegerField(required=False, min_value=2000, max_value=2099)
    card_cvc = serializers.CharField(max_length=4, required=False, allow_blank=True)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_currency(self, value: str) -> str:
        upper = value.upper()
        if upper not in SUPPORTED_CURRENCIES:
            raise serializers.ValidationError(f"Unsupported currency: {value}")
        return upper

    def validate(self, attrs):
        currency = attrs.get("currency", "").upper()
        amount: Decimal = attrs["amount"]
        if currency in ZERO_DECIMAL_CURRENCIES and amount != amount.to_integral_value():
            raise serializers.ValidationError(
                {"amount": [f"{currency} does not support fractional amounts."]}
            )
        attrs["currency"] = currency
        return attrs


class RefundRequestSerializer(serializers.Serializer):
    transaction_id = serializers.CharField(max_length=36)
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        min_value=Decimal("0.01"),
    )
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)


class TransactionResponseSerializer(serializers.ModelSerializer):
    error = serializers.SerializerMethodField()
    related_transaction_id = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = (
            "transaction_id",
            "kind",
            "status",
            "amount",
            "currency",
            "card_last4",
            "description",
            "reason",
            "related_transaction_id",
            "error",
            "created_at",
        )

    def get_error(self, obj: Transaction):
        if obj.is_succeeded or not obj.error_code:
            return None
        return {"code": obj.error_code, "message": obj.error_message}

    def get_related_transaction_id(self, obj: Transaction):
        return obj.related_transaction.transaction_id if obj.related_transaction_id else None

    def to_representation(self, instance: Transaction):
        data = super().to_representation(instance)
        if instance.kind == Transaction.KIND_CHARGE:
            data.pop("reason", None)
            data.pop("related_transaction_id", None)
        else:
            data.pop("description", None)
        return data


class TransactionListQuerySerializer(serializers.Serializer):
    kind = serializers.ChoiceField(
        choices=[Transaction.KIND_CHARGE, Transaction.KIND_REFUND],
        required=False,
    )
    status = serializers.ChoiceField(
        choices=[Transaction.STATUS_SUCCEEDED, Transaction.STATUS_FAILED],
        required=False,
    )
    from_ = serializers.DateTimeField(required=False)
    to = serializers.DateTimeField(required=False)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)
    offset = serializers.IntegerField(required=False, min_value=0, default=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["from"] = self.fields.pop("from_")
