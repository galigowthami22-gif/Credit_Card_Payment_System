from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from payment_management.payment_model import Payment

class PaymentRepository:

    @staticmethod
    async def create(db: AsyncSession, payment: Payment) -> Payment:
        db.add(payment)
        await db.commit()
        await db.refresh(payment)
        return payment

    @staticmethod
    async def get_by_id(db: AsyncSession, payment_id: int):
        result = await db.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update(db: AsyncSession, payment: Payment):
        db.add(payment)
        await db.commit()
        await db.refresh(payment)
        return payment