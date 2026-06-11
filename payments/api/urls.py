from django.urls import path

from payments.api import views


urlpatterns = [
    path("payments/charge", views.ChargeView.as_view(), name="api_payments_charge"),
    path("payments/refund", views.RefundView.as_view(), name="api_payments_refund"),
    path(
        "payments/<str:transaction_id>",
        views.TransactionDetailView.as_view(),
        name="api_payments_detail",
    ),
    path("transactions", views.TransactionListView.as_view(), name="api_transactions"),
]
