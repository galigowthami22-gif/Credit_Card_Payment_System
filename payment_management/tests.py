import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from payment_management.payment_service import PaymentService
from payment_management.payment_repository import PaymentRepository
from payment_management.payment_schema import PaymentCreate


class _QueryResult:
    def __init__(self, card):
        self.card = card

    def scalar_one_or_none(self):
        return self.card


class _Session:
    def __init__(self, card):
        self.card = card

    async def execute(self, _query):
        return _QueryResult(self.card)


class PaymentServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_payment_uses_card_last_four_from_owners_saved_card(self):
        card = SimpleNamespace(last_four_digits="1234")
        session = _Session(card)
        statuses = []

        async def store(_session, payment):
            statuses.append(payment.status)
            return payment

        with (
            patch.object(PaymentRepository, "create", new=AsyncMock(side_effect=store)),
            patch.object(PaymentRepository, "update", new=AsyncMock(side_effect=store)),
            patch("payment_management.payment_service.random.choice", return_value=True),
        ):
            payment = await PaymentService.make_payment(
                session,
                user_id=7,
                payment_data=PaymentCreate(card_id=2, amount=Decimal("25.50")),
            )

        self.assertEqual(statuses, ["PENDING", "SUCCESS"])
        self.assertEqual(payment.card_last_four, "1234")
        self.assertEqual(payment.status, "SUCCESS")

    async def test_payment_rejects_card_not_owned_by_user(self):
        session = _Session(None)

        with patch.object(PaymentRepository, "create", new=AsyncMock()) as create:
            with self.assertRaisesRegex(ValueError, "Saved card not found"):
                await PaymentService.make_payment(
                    session,
                    user_id=7,
                    payment_data=PaymentCreate(card_id=2, amount=Decimal("25.50")),
                )

        create.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
