"""Views for authentication, dashboard, and the admin portal."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.forms import (
    AdminUserCreateForm,
    AdminUserUpdateForm,
    BootstrapAuthenticationForm,
    EndUserSignupForm,
)
from accounts.mixins import AdminRequiredMixin, EndUserRequiredMixin
from payments.models import Transaction

User = get_user_model()


class AppLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = BootstrapAuthenticationForm
    redirect_authenticated_user = True


class AppLogoutView(LogoutView):
    next_page = "/login/"


class EndUserSignupView(FormView):
    """Public sign-up view. Only creates end-user-role accounts."""

    template_name = "accounts/signup.html"
    form_class = EndUserSignupForm
    success_url = reverse_lazy("dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(
            self.request,
            "ユーザー登録が完了しました。APIキーが発行されています。",
        )
        return super().form_valid(form)


class DashboardView(LoginRequiredMixin, TemplateView):
    """Role-aware landing page after login."""

    def get_template_names(self):
        if self.request.user.is_admin_role:
            return ["accounts/dashboard_admin.html"]
        return ["accounts/dashboard_end_user.html"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_admin_role:
            tx_qs = Transaction.objects.all()
            ctx.update(
                {
                    "user_count": User.objects.count(),
                    "admin_count": User.objects.filter(role=User.ROLE_ADMIN).count(),
                    "end_user_count": User.objects.filter(
                        role=User.ROLE_END_USER
                    ).count(),
                    "transaction_count": tx_qs.count(),
                    "succeeded_count": tx_qs.filter(
                        status=Transaction.STATUS_SUCCEEDED
                    ).count(),
                    "failed_count": tx_qs.filter(
                        status=Transaction.STATUS_FAILED
                    ).count(),
                }
            )
        else:
            recent = (
                Transaction.objects.filter(user=user)
                .select_related("related_transaction")
                .order_by("-created_at")[:10]
            )
            ctx["recent_transactions"] = recent
            ctx["transaction_count"] = Transaction.objects.filter(user=user).count()
        return ctx


class RegenerateApiKeyView(EndUserRequiredMixin, View):
    """POST-only view that issues a fresh API key for the current end user."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        user = request.user
        user.clear_api_key()
        user.issue_api_key()
        user.save(update_fields=["api_key", "api_key_issued_at"])
        messages.success(request, "新しいAPIキーを発行しました。古いキーは無効化されました。")
        return HttpResponseRedirect(reverse("dashboard"))


class AdminUserListView(AdminRequiredMixin, ListView):
    template_name = "accounts/admin_user_list.html"
    context_object_name = "users"
    paginate_by = 20

    def get_queryset(self):
        qs = User.objects.all().order_by("-date_joined")
        role = self.request.GET.get("role")
        if role in {User.ROLE_ADMIN, User.ROLE_END_USER}:
            qs = qs.filter(role=role)
        active = self.request.GET.get("active")
        if active == "1":
            qs = qs.filter(is_active=True)
        elif active == "0":
            qs = qs.filter(is_active=False)
        keyword = self.request.GET.get("q")
        if keyword:
            qs = qs.filter(
                Q(username__icontains=keyword) | Q(email__icontains=keyword)
            )
        return qs.annotate(transactions_count=Count("transactions"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_role"] = self.request.GET.get("role", "")
        ctx["filter_active"] = self.request.GET.get("active", "")
        ctx["filter_q"] = self.request.GET.get("q", "")
        ctx["role_choices"] = User.ROLE_CHOICES
        return ctx


class AdminUserDetailView(AdminRequiredMixin, DetailView):
    template_name = "accounts/admin_user_detail.html"
    context_object_name = "target_user"
    model = User

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["recent_transactions"] = (
            Transaction.objects.filter(user=self.object)
            .select_related("related_transaction")
            .order_by("-created_at")[:20]
        )
        return ctx


class AdminCreateView(AdminRequiredMixin, CreateView):
    template_name = "accounts/admin_form.html"
    form_class = AdminUserCreateForm
    success_url = reverse_lazy("admin_portal:user_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "管理者ユーザーを作成"
        ctx["submit_label"] = "作成する"
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "管理者ユーザーを作成しました。")
        return response


class AdminUpdateView(AdminRequiredMixin, UpdateView):
    template_name = "accounts/admin_form.html"
    form_class = AdminUserUpdateForm
    success_url = reverse_lazy("admin_portal:user_list")

    def get_queryset(self):
        return User.objects.filter(role=User.ROLE_ADMIN)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = f"管理者ユーザーを更新: {self.object.username}"
        ctx["submit_label"] = "更新する"
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "管理者ユーザーを更新しました。")
        return response


class AdminDeleteView(AdminRequiredMixin, DeleteView):
    template_name = "accounts/admin_confirm_delete.html"
    success_url = reverse_lazy("admin_portal:user_list")

    def get_queryset(self):
        return User.objects.filter(role=User.ROLE_ADMIN)

    def form_valid(self, form):
        target = self.get_object()
        if target.pk == self.request.user.pk:
            messages.error(self.request, "自分自身は削除できません。")
            return redirect("admin_portal:user_list")
        response = super().form_valid(form)
        messages.success(self.request, "管理者ユーザーを削除しました。")
        return response
