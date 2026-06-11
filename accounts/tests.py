"""Tests for the accounts app."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class UserModelTests(TestCase):
    def test_end_user_gets_api_key_on_save(self):
        u = User(username="alice", email="alice@example.com", role=User.ROLE_END_USER)
        u.set_password("strong-pass-123!")
        u.save()
        self.assertTrue(u.api_key)
        self.assertTrue(u.api_key.startswith("pk_live_"))
        self.assertIsNotNone(u.api_key_issued_at)

    def test_admin_user_has_no_api_key(self):
        u = User(username="root", email="root@example.com", role=User.ROLE_ADMIN)
        u.set_password("strong-pass-123!")
        u.save()
        self.assertIsNone(u.api_key)
        self.assertIsNone(u.api_key_issued_at)

    def test_role_properties(self):
        end = User.objects.create_user(
            username="end", email="e@example.com", password="pw-12345!"
        )
        adm = User.objects.create_superuser(
            username="adm", email="a@example.com", password="pw-12345!"
        )
        self.assertTrue(end.is_end_user_role)
        self.assertFalse(end.is_admin_role)
        self.assertTrue(adm.is_admin_role)
        self.assertFalse(adm.is_end_user_role)


class SignupViewTests(TestCase):
    def test_signup_creates_end_user_with_api_key(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "bob",
                "email": "bob@example.com",
                "password1": "Comp1ex-Passw0rd!",
                "password2": "Comp1ex-Passw0rd!",
            },
        )
        self.assertEqual(response.status_code, 302)
        u = User.objects.get(username="bob")
        self.assertEqual(u.role, User.ROLE_END_USER)
        self.assertTrue(u.api_key)


class AdminPortalAccessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            "adm", "adm@example.com", "Comp1ex-Passw0rd!"
        )
        self.end_user = User.objects.create_user(
            "end", "end@example.com", "Comp1ex-Passw0rd!"
        )

    def test_end_user_cannot_access_admin_user_list(self):
        self.client.login(username="end", password="Comp1ex-Passw0rd!")
        res = self.client.get(reverse("admin_portal:user_list"))
        self.assertEqual(res.status_code, 403)

    def test_admin_can_access_admin_user_list(self):
        self.client.login(username="adm", password="Comp1ex-Passw0rd!")
        res = self.client.get(reverse("admin_portal:user_list"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "ユーザー一覧")

    def test_admin_cannot_delete_self(self):
        self.client.login(username="adm", password="Comp1ex-Passw0rd!")
        url = reverse("admin_portal:admin_delete", args=[self.admin.pk])
        res = self.client.post(url)
        self.assertEqual(res.status_code, 302)
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_regenerate_api_key(self):
        self.client.login(username="end", password="Comp1ex-Passw0rd!")
        original = self.end_user.api_key
        res = self.client.post(reverse("regenerate_api_key"))
        self.assertEqual(res.status_code, 302)
        self.end_user.refresh_from_db()
        self.assertNotEqual(self.end_user.api_key, original)
