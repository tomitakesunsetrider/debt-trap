"""Web views for browsing transaction history."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.views.generic import ListView

from accounts.mixins import AdminRequiredMixin, EndUserRequiredMixin
from payments.models import Transaction

User = get_user_model()


def _apply_filters(qs, request):
    kind = request.GET.get("kind")
    status_v = request.GET.get("status")
    if kind in {Transaction.KIND_CHARGE, Transaction.KIND_REFUND}:
        qs = qs.filter(kind=kind)
    if status_v in {Transaction.STATUS_SUCCEEDED, Transaction.STATUS_FAILED}:
        qs = qs.filter(status=status_v)
    return qs


class MyTransactionListView(EndUserRequiredMixin, ListView):
    template_name = "payments/transaction_list.html"
    context_object_name = "transactions"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            Transaction.objects.filter(user=self.request.user)
            .select_related("related_transaction", "user")
            .order_by("-created_at")
        )
        return _apply_filters(qs, self.request)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_kind"] = self.request.GET.get("kind", "")
        ctx["filter_status"] = self.request.GET.get("status", "")
        ctx["page_title"] = "自分の取引履歴"
        ctx["show_user_column"] = False
        return ctx


class AdminTransactionListView(AdminRequiredMixin, ListView):
    template_name = "payments/transaction_list.html"
    context_object_name = "transactions"
    paginate_by = 50

    def get_queryset(self):
        qs = (
            Transaction.objects.all()
            .select_related("related_transaction", "user")
            .order_by("-created_at")
        )
        qs = _apply_filters(qs, self.request)
        user_id = self.request.GET.get("user")
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_kind"] = self.request.GET.get("kind", "")
        ctx["filter_status"] = self.request.GET.get("status", "")
        ctx["filter_user"] = self.request.GET.get("user", "")
        ctx["page_title"] = "全取引履歴"
        ctx["show_user_column"] = True
        return ctx
