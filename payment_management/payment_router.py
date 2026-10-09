from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from payment_management.payment_schema import PaymentCreate, PaymentResponse
from payment_management.payment_service import PaymentService
from auth_dependency import get_current_user

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def make_payment(
    payment_data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PaymentResponse:
    try:
        payment = await PaymentService.make_payment(
            db=db,
            user_id=current_user["user_id"],
            payment_data=payment_data,
        )
        return payment
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))