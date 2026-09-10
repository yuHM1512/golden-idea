from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class UnitIdeaTarget(Base):
    __tablename__ = "unit_idea_targets"
    __table_args__ = (
        CheckConstraint("year >= 2000 AND year <= 2100", name="ck_unit_idea_target_year"),
        CheckConstraint("target_count >= 0", name="ck_unit_idea_target_count"),
    )

    year = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey("units.id", ondelete="CASCADE"), primary_key=True)
    target_count = Column(Integer, nullable=False)
    updated_by = Column(String(50), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
