from decimal import Decimal
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, Field


class PaymentRequest(BaseModel):
    payment_reference: UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class PaymentResponse(BaseModel):
    id: int
    transaction_id: str
    amount: Decimal
    card_last_four: str
    status: Literal["PENDING", "SUCCESS", "FAILED"]
    failure_reason: str | None
    created_at: str
    updated_at: str
