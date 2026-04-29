from sqlalchemy import Column, Float, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class RewardBatch(Base):
    __tablename__ = "reward_batches"

    id = Column(Integer, primary_key=True, index=True)
    quarter = Column(Integer, nullable=False)   # 1-4
    year = Column(Integer, nullable=False)
    coefficient = Column(Float, nullable=False)  # VND per point
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
