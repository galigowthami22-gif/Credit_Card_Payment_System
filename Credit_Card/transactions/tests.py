import csv
from decimal import Decimal
from io import StringIO

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth.models import User
from django.db import connection
from django.test import TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from transactions.models import Transaction
from users.tokens import create_access_token


class TransactionManagementTests(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.created_transaction_table = (
            Transaction._meta.db_table not in connection.introspection.table_names()
        )
        if cls.created_transaction_table:
            with connection.schema_editor() as schema_editor:
                schema_editor.create_model(Transaction)

    @classmethod
    def tearDownClass(cls):
        if cls.created_transaction_table:
            with connection.schema_editor() as schema_editor:
                schema_editor.delete_model(Transaction)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user(username="transaction-user", password="test-password")
        self.other_user = User.objects.create_user(username="another-user", password="test-password")
        self.admin = User.objects.create_superuser(
            username="admin-user",
            email="admin@example.com",
            password="test-password",
        )

    def create_transaction(self, *, user_id, status="SUCCESS", amount="25.00", **overrides):
        values = {
            "user_id": user_id,
            "card_id": 10,
            "amount": Decimal(amount),
            "currency": "INR",
            "status": status,
            "transaction_id": f"TXN-{Transaction.objects.count() + 1}",
            "card_last_four": "4242",
            "failure_reason": None,
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
        }
        values.update(overrides)
        return Transaction.objects.create(**values)

    def test_api_requires_bearer_token_even_with_session_auth(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("transaction-history"))

        self.assertEqual(response.status_code, 401)

    def test_api_rejects_invalid_bearer_token(self):
        response = self.client.get(
            reverse("transaction-history"),
            HTTP_AUTHORIZATION="Bearer invalid-token",
        )

        self.assertEqual(response.status_code, 401)

    def test_api_returns_only_the_authenticated_users_transactions(self):
        own = self.create_transaction(user_id=self.user.pk)
        self.create_transaction(user_id=self.other_user.pk)

        response = self.client.get(
            reverse("transaction-history"),
            HTTP_AUTHORIZATION=f"Bearer {create_access_token(self.user.pk)}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["transaction_id"] for item in response.json()["transactions"]],
            [own.pk],
        )

    def test_user_cannot_read_another_users_transaction_detail(self):
        transaction = self.create_transaction(user_id=self.other_user.pk)

        response = self.client.get(
            reverse("transaction-detail", args=[transaction.pk]),
            HTTP_AUTHORIZATION=f"Bearer {create_access_token(self.user.pk)}",
        )

        self.assertEqual(response.status_code, 404)

    def test_invalid_filters_return_a_client_error(self):
        response = self.client.get(
            reverse("transaction-history"),
            {"date": "not-a-date"},
            HTTP_AUTHORIZATION=f"Bearer {create_access_token(self.user.pk)}",
        )

        self.assertEqual(response.status_code, 400)

    def test_admin_changelist_shows_daily_payment_summary(self):
        self.create_transaction(user_id=self.user.pk, status="SUCCESS", amount="25.00")
        self.create_transaction(user_id=self.user.pk, status="FAILED", amount="12.50")
        self.create_transaction(user_id=self.user.pk, status="PENDING", amount="10.00")
        self.client.force_login(self.admin)

        response = self.client.get(reverse("admin:transactions_transaction_changelist"))

        self.assertEqual(response.status_code, 200)
        summary = response.context["daily_summary"]
        self.assertEqual(summary["total_transactions"], 3)
        self.assertEqual(summary["successful_payments"], 1)
        self.assertEqual(summary["failed_payments"], 1)
        self.assertEqual(summary["pending_payments"], 1)
        self.assertEqual(summary["total_payment_amount"], Decimal("47.50"))

    def test_non_admin_cannot_access_transaction_admin(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("admin:transactions_transaction_changelist"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("admin:login"), response.url)

    def test_admin_csv_export_is_audited_and_formula_safe(self):
        transaction = self.create_transaction(
            user_id=self.user.pk,
            status="FAILED",
            failure_reason="=HYPERLINK(\"https://example.invalid\")",
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:transactions_transaction_changelist"),
            {
                "action": "export_transactions_csv",
                "_selected_action": [str(transaction.pk)],
                "index": "0",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        rows = list(csv.reader(StringIO(response.content.decode("utf-8"))))
        self.assertEqual(rows[1][7], "'=HYPERLINK(\"https://example.invalid\")")
        self.assertTrue(
            LogEntry.objects.filter(
                user=self.admin,
                object_id=str(transaction.pk),
                action_flag=CHANGE,
            ).exists()
        )
        self.assertEqual(
            self.client.get(reverse("admin:admin_logentry_changelist")).status_code,
            200,
        )

    def test_direct_csv_export_downloads_all_records_for_admin(self):
        first = self.create_transaction(user_id=self.user.pk)
        second = self.create_transaction(user_id=self.other_user.pk, status="FAILED")
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("admin:transactions_transaction_export_csv")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="transactions.csv"')
        rows = list(csv.reader(StringIO(response.content.decode("utf-8"))))
        exported_ids = {row[0] for row in rows[1:]}
        self.assertIn(first.transaction_id, exported_ids)
        self.assertIn(second.transaction_id, exported_ids)
