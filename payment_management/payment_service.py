import random
import uuid
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from payment_management.card_model import SavedCard
from payment_management.payment_model import Payment
from payment_management.payment_schema import PaymentCreate
from payment_management.payment_repository import PaymentRepository

class PaymentService:

    @staticmethod
    async def make_payment(db: AsyncSession, user_id: int, payment_data: PaymentCreate):
        if payment_data.amount <= Decimal("0"):
            raise ValueError("Payment amount must be greater than zero")
        if payment_data.amount > Decimal("1000000"):
            raise ValueError("Payment amount cannot exceed ₹10,00,000")

        result = await db.execute(
            select(SavedCard).where(
                SavedCard.id == payment_data.card_id,
                SavedCard.user_id == user_id,
            )
        )
        card = result.scalar_one_or_none()
        if card is None:
            raise ValueError("Saved card not found.")

        transaction_id = (f"TXN-{uuid.uuid4().hex[:12].upper()}")
        payment = Payment(user_id=user_id,
            card_id=payment_data.card_id,
            amount=payment_data.amount,
            currency="INR", status="PENDING", 
            transaction_id=transaction_id, 
            card_last_four=card.last_four_digits)
        payment = await PaymentRepository.create(db, payment)
        payment_success = random.choice([True, True, True, False])
        if payment_success:
            payment.status = "SUCCESS"
            payment.failure_reason = None
        else:
            payment.status = "FAILED"
            payment.failure_reason = ("Payment declined by simulated gateway")
        payment = await PaymentRepository.update(db, payment)
        return payment