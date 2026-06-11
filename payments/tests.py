"""Tests for the payments app (rules, services, and API endpoints)."""
from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from payments.exceptions import (
    AlreadyRefunded,
    RefundAmountExceeded,
    RefundNotAllowed,
    TransactionNotFound,
)
from payments.models import Transaction
from payments.rules import evaluate_charge, extract_last4
from payments.services import create_charge, create_refund, get_user_transaction

User = get_user_model()


class RuleTests(TestCase):
    def test_extract_last4(self):
        self.assertEqual(extract_last4("4242 4242 4242 4242"), "4242")
        self.assertEqual(extract_last4("4000-0000-0000-0000"), "0000")
        self.assertEqual(extract_last4("12"), "")

    def test_normal_card_succeeds(self):
        out = evaluate_charge(Decimal("1500"), "4242424242424242")
        self.assertTrue(out.succeeded)

    def test_declined_card(self):
        out = evaluate_charge(Decimal("1500"), "4000000000000000")
        self.assertFalse(out.succeeded)
        self.assertEqual(out.error_code, "card_declined")

    def test_insufficient_funds(self):
        out = evaluate_charge(Decimal("1500"), "4000000000000001")
        self.assertEqual(out.error_code, "insufficient_funds")

    def test_amount_too_large(self):
        out = evaluate_charge(Decimal("1000000"), "4242424242424242")
        self.assertFalse(out.succeeded)
        self.assertEqual(out.error_code, "amount_too_large")


class ServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "alice", "a@example.com", "Comp1ex-Passw0rd!"
        )

    def test_create_charge_succeeded(self):
        tx = create_charge(
            self.user,
            amount=Decimal("1500"),
            currency="JPY",
            card_number="4242424242424242",
        )
        self.assertTrue(tx.is_succeeded)
        self.assertEqual(tx.card_last4, "4242")

    def test_create_charge_failed_card(self):
        tx = create_charge(
            self.user,
            amount=Decimal("1500"),
            currency="JPY",
            card_number="4000000000000000",
        )
        self.assertTrue(tx.is_failed)
        self.assertEqual(tx.error_code, "card_declined")

    def test_refund_happy_path(self):
        charge = create_charge(
            self.user,
            amount=Decimal("2000"),
            currency="JPY",
            card_number="4242424242424242",
        )
        refund = create_refund(
            self.user, transaction_id=charge.transaction_id, reason="customer_request"
        )
        self.assertTrue(refund.is_succeeded)
        self.assertEqual(refund.kind, Transaction.KIND_REFUND)
        self.assertEqual(refund.related_transaction_id, charge.id)

    def test_refund_not_found_for_other_user(self):
        other = User.objects.create_user("bob", "b@example.com", "Comp1ex-Passw0rd!")
        charge = create_charge(
            other,
            amount=Decimal("2000"),
            currency="JPY",
            card_number="4242424242424242",
        )
        with self.assertRaises(TransactionNotFound):
            create_refund(self.user, transaction_id=charge.transaction_id)

    def test_refund_of_failed_charge_not_allowed(self):
        charge = create_charge(
            self.user,
            amount=Decimal("2000"),
            currency="JPY",
            card_number="4000000000000000",
        )
        with self.assertRaises(RefundNotAllowed):
            create_refund(self.user, transaction_id=charge.transaction_id)

    def test_double_refund(self):
        charge = create_charge(
            self.user,
            amount=Decimal("2000"),
            currency="JPY",
            card_number="4242424242424242",
        )
        create_refund(self.user, transaction_id=charge.transaction_id)
        with self.assertRaises(AlreadyRefunded):
            create_refund(self.user, transaction_id=charge.transaction_id)

    def test_refund_amount_exceeded(self):
        charge = create_charge(
            self.user,
            amount=Decimal("1000"),
            currency="JPY",
            card_number="4242424242424242",
        )
        with self.assertRaises(RefundAmountExceeded):
            create_refund(
                self.user, transaction_id=charge.transaction_id, amount=Decimal("2000")
            )

    def test_get_user_transaction_not_found(self):
        with self.assertRaises(TransactionNotFound):
            get_user_transaction(self.user, "missing-id")


class ApiAuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "alice", "a@example.com", "Comp1ex-Passw0rd!"
        )
        self.client = APIClient()

    def test_missing_api_key_returns_401(self):
        res = self.client.post(
            "/api/v1/payments/charge",
            data={"amount": "1500", "currency": "JPY", "card_number": "4242424242424242"},
            format="json",
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["error"]["code"], "unauthorized")

    def test_admin_cannot_use_api(self):
        admin = User.objects.create_superuser("adm", "adm@e.com", "Comp1ex-Passw0rd!")
        self.assertIsNone(admin.api_key)
        self.client.credentials(HTTP_X_API_KEY="pk_live_invalid")
        res = self.client.get("/api/v1/transactions")
        self.assertEqual(res.status_code, 401)


class ChargeApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "alice", "a@example.com", "Comp1ex-Passw0rd!"
        )
        self.client = APIClient()
        self.client.credentials(HTTP_X_API_KEY=self.user.api_key)

    def test_successful_charge(self):
        res = self.client.post(
            "/api/v1/payments/charge",
            data={
                "amount": "1500",
                "currency": "JPY",
                "card_number": "4242424242424242",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertEqual(body["status"], "succeeded")
        self.assertEqual(body["card_last4"], "4242")
        self.assertEqual(body["currency"], "JPY")

    def test_declined_charge_returns_201_with_failed(self):
        res = self.client.post(
            "/api/v1/payments/charge",
            data={
                "amount": "1500",
                "currency": "JPY",
                "card_number": "4000000000000000",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertEqual(body["status"], "failed")
        self.assertEqual(body["error"]["code"], "card_declined")

    def test_validation_error_for_jpy_fractional(self):
        res = self.client.post(
            "/api/v1/payments/charge",
            data={
                "amount": "1500.50",
                "currency": "JPY",
                "card_number": "4242424242424242",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error"]["code"], "validation_error")


class RefundApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "alice", "a@example.com", "Comp1ex-Passw0rd!"
        )
        self.client = APIClient()
        self.client.credentials(HTTP_X_API_KEY=self.user.api_key)

    def _make_charge(self) -> str:
        res = self.client.post(
            "/api/v1/payments/charge",
            data={
                "amount": "1500",
                "currency": "JPY",
                "card_number": "4242424242424242",
            },
            format="json",
        )
        return res.json()["transaction_id"]

    def test_refund_happy_path(self):
        tx_id = self._make_charge()
        res = self.client.post(
            "/api/v1/payments/refund",
            data={"transaction_id": tx_id, "reason": "test"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertEqual(body["kind"], "refund")
        self.assertEqual(body["related_transaction_id"], tx_id)

    def test_double_refund(self):
        tx_id = self._make_charge()
        self.client.post(
            "/api/v1/payments/refund",
            data={"transaction_id": tx_id},
            format="json",
        )
        res = self.client.post(
            "/api/v1/payments/refund",
            data={"transaction_id": tx_id},
            format="json",
        )
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["error"]["code"], "already_refunded")


class TransactionListApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "alice", "a@example.com", "Comp1ex-Passw0rd!"
        )
        self.client = APIClient()
        self.client.credentials(HTTP_X_API_KEY=self.user.api_key)

    def test_only_self_transactions_listed(self):
        other = User.objects.create_user("bob", "b@example.com", "Comp1ex-Passw0rd!")
        Transaction.objects.create(
            user=other,
            kind=Transaction.KIND_CHARGE,
            amount=Decimal("100"),
            currency="JPY",
            card_last4="4242",
            status=Transaction.STATUS_SUCCEEDED,
        )
        res = self.client.get("/api/v1/transactions")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["count"], 0)
