from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.generic import RedirectView


urlpatterns = [
    path("", login_required(RedirectView.as_view(url="/dashboard/", permanent=False))),
    path("django-admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("payments.urls")),
    path("api/v1/", include("payments.api.urls")),
]
