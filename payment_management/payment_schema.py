from decimal import Decimal
from pydantic import BaseModel, Field

class PaymentCreate(BaseModel):

    card_id: int = Field(..., gt=0, description="Saved card ID")
    amount: Decimal = Field(..., gt=0, description="Payment amount")

class PaymentResponse(BaseModel):

    id: int
    transaction_id: str
    card_id: int
    card_last_four: str
    amount: Decimal
    currency: str
    status: str
    failure_reason: str | None = None

    class Config:
        from_attributes = True