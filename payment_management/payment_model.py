from datetime import datetime
from decimal import Decimal
from sqlalchemy import BigInteger, Column, String, Numeric, DateTime
from core.database import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    card_id = Column(BigInteger, nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(String(20), nullable=False, default="PENDING")
    transaction_id = Column(String(100), unique=True, nullable=False, index=True)
    card_last_four = Column(String(4), nullable=False)
    failure_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)