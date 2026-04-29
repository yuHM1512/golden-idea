from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ActualBenefitEvaluation(Base):
    __tablename__ = "actual_benefit_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    idea_id = Column(Integer, ForeignKey("ideas.id"), nullable=False, unique=True, index=True)
    evaluator_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    before_seconds = Column(Float, nullable=False)
    after_seconds = Column(Float, nullable=False)
    improvement_percent = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    labor_second_price = Column(Float, nullable=False, default=6.14)
    benefit_value = Column(Float, nullable=False)
    note = Column(Text, nullable=True)

    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    idea = relationship("Idea", back_populates="actual_benefit")
    evaluator = relationship("User")
