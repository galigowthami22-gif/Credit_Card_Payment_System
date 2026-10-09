import sqlite3
import os
import tempfile
import unittest
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import jwt
from fastapi.testclient import TestClient
from uuid import UUID

from payments.main import create_app

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", "default-key"))
PAYMENT_REFERENCE = UUID("7438ad78-21f8-42db-88fd-64dcd7823154")


class PaymentApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "payments.sqlite3"
        self.app = create_app(self.database_path)
        self.client_context = TestClient(self.app)
        self.client = self.client_context.__enter__()
        self.authorization = self._authorization()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.temp_directory.cleanup()

    def _authorization(self, last_four: str = "4242", reference=PAYMENT_REFERENCE):
        now = datetime.now(UTC)
        return {
            "Authorization": "Bearer "
            + jwt.encode(
                {
                    "user_id": 1,
                    "iat": now,
                    "exp": now + timedelta(minutes=2),
                    "scope": "payment",
                    "payment_reference": str(reference),
                    "card_last_four": last_four,
                },
                JWT_SECRET_KEY,
                algorithm="HS256",
            )
        }

    def _payment_payload(self, **updates) -> dict[str, str]:
        payload = {
            "amount": "25.50",
            "payment_reference": str(PAYMENT_REFERENCE),
        }
        payload.update(updates)
        return payload

    def test_payment_is_created_pending_before_processing_and_finalized(self) -> None:
        def inspect_pending_then_succeed(card_last_four: str) -> tuple[str, None]:
            with closing(sqlite3.connect(self.database_path)) as connection:
                row = connection.execute(
                    "SELECT status, card_last_four FROM payments"
                ).fetchone()
            self.assertEqual(row, ("PENDING", "4242"))
            self.assertEqual(card_last_four, "4242")
            return "SUCCESS", None

        with patch(
            "payments.main.simulate_payment",
            side_effect=inspect_pending_then_succeed,
        ):
            response = self.client.post(
                "/payments",
                json=self._payment_payload(),
                headers=self.authorization,
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "SUCCESS")
        self.assertEqual(response.json()["card_last_four"], "4242")
        self.assertEqual(response.json()["transaction_id"], "TXN-1")
        self.assertNotIn("card_number", response.json())
        self.assertNotIn("cvv", response.json())

        with closing(sqlite3.connect(self.database_path)) as connection:
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(payments)")
            }
        self.assertNotIn("card_number", columns)
        self.assertNotIn("cvv", columns)

    def test_simulator_can_return_failed_status(self) -> None:
        response = self.client.post(
            "/payments",
            json=self._payment_payload(),
            headers=self._authorization(last_four="0002"),
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "FAILED")
        self.assertEqual(
            response.json()["failure_reason"],
            "Payment declined by the simulator.",
        )

    def test_invalid_amount_is_rejected(self) -> None:
        invalid_payload = self._payment_payload(amount="0")

        response = self.client.post(
            "/payments",
            json=invalid_payload,
            headers=self.authorization,
        )

        self.assertEqual(response.status_code, 422)

        with closing(sqlite3.connect(self.database_path)) as connection:
            count = connection.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
        self.assertEqual(count, 0)

    def test_payment_requires_a_valid_jwt(self) -> None:
        response = self.client.post("/payments", json=self._payment_payload())

        self.assertEqual(response.status_code, 401)

    def test_payment_authorization_is_bound_to_card_reference(self) -> None:
        response = self.client.post(
            "/payments",
            json=self._payment_payload(payment_reference="5254bda4-5963-4fc3-a297-e4c1db4f2347"),
            headers=self.authorization,
        )

        self.assertEqual(response.status_code, 401)

    def test_user_access_token_is_not_a_card_payment_grant(self) -> None:
        now = datetime.now(UTC)
        access_token = jwt.encode(
            {"user_id": 1, "iat": now, "exp": now + timedelta(hours=1)},
            JWT_SECRET_KEY,
            algorithm="HS256",
        )

        response = self.client.post(
            "/payments",
            json=self._payment_payload(),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
