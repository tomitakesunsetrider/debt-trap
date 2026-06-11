"""REST endpoints for the mock payment API."""
from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from payments import services
from payments.api.serializers import (
    ChargeRequestSerializer,
    RefundRequestSerializer,
    TransactionListQuerySerializer,
    TransactionResponseSerializer,
)
from payments.models import Transaction


class ChargeView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ChargeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        tx = services.create_charge(
            user=request.user,
            amount=data["amount"],
            currency=data["currency"],
            card_number=data["card_number"],
            description=data.get("description", ""),
        )
        return Response(
            TransactionResponseSerializer(tx).data,
            status=status.HTTP_201_CREATED,
        )


class RefundView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = RefundRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        tx = services.create_refund(
            user=request.user,
            transaction_id=data["transaction_id"],
            amount=data.get("amount"),
            reason=data.get("reason", ""),
        )
        return Response(
            TransactionResponseSerializer(tx).data,
            status=status.HTTP_201_CREATED,
        )


class TransactionDetailView(APIView):
    def get(self, request, transaction_id, *args, **kwargs):
        tx = services.get_user_transaction(request.user, transaction_id)
        return Response(TransactionResponseSerializer(tx).data)


class TransactionListView(APIView):
    def get(self, request, *args, **kwargs):
        query = TransactionListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data

        qs = Transaction.objects.filter(user=request.user).select_related(
            "related_transaction"
        )
        if "kind" in params:
            qs = qs.filter(kind=params["kind"])
        if "status" in params:
            qs = qs.filter(status=params["status"])
        if "from" in params:
            qs = qs.filter(created_at__gte=params["from"])
        if "to" in params:
            qs = qs.filter(created_at__lte=params["to"])

        limit = params.get("limit", 20)
        offset = params.get("offset", 0)
        total = qs.count()
        results = list(qs.order_by("-created_at")[offset : offset + limit])

        return Response(
            {
                "count": total,
                "limit": limit,
                "offset": offset,
                "results": TransactionResponseSerializer(results, many=True).data,
            }
        )
