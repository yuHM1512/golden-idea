from sqlalchemy import Column, Date, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class ScoreCriteriaSet(Base):
    __tablename__ = "score_criteria_sets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    effective_from = Column(Date, nullable=False, index=True)
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
