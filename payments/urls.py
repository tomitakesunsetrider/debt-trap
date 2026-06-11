from django.urls import path

from payments import views


urlpatterns = [
    path("me/transactions/", views.MyTransactionListView.as_view(), name="my_transactions"),
    path(
        "admin-portal/transactions/",
        views.AdminTransactionListView.as_view(),
        name="admin_transactions",
    ),
]
