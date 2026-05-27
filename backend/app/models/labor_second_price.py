from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class LaborSecondPrice(Base):
    __tablename__ = "labor_second_prices"

    year = Column(Integer, primary_key=True, index=True)
    labor_second_price = Column(Float, nullable=False)
    updated_by = Column(String(50), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
