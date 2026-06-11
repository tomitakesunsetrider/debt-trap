from django.urls import include, path

from accounts import views

admin_portal_patterns = (
    [
        path("users/", views.AdminUserListView.as_view(), name="user_list"),
        path("users/<int:pk>/", views.AdminUserDetailView.as_view(), name="user_detail"),
        path("admins/new/", views.AdminCreateView.as_view(), name="admin_create"),
        path("admins/<int:pk>/edit/", views.AdminUpdateView.as_view(), name="admin_update"),
        path(
            "admins/<int:pk>/delete/",
            views.AdminDeleteView.as_view(),
            name="admin_delete",
        ),
    ],
    "admin_portal",
)


urlpatterns = [
    path("login/", views.AppLoginView.as_view(), name="login"),
    path("logout/", views.AppLogoutView.as_view(), name="logout"),
    path("signup/", views.EndUserSignupView.as_view(), name="signup"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path(
        "me/api-key/regenerate/",
        views.RegenerateApiKeyView.as_view(),
        name="regenerate_api_key",
    ),
    path("admin-portal/", include(admin_portal_patterns)),
]
