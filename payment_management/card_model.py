from sqlalchemy import BigInteger, Column, String

from core.database import Base


class SavedCard(Base):
    __tablename__ = "cards_card"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    last_four_digits = Column(String(4), nullable=False)
