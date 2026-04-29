from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class K1Type(str, Enum):
    COMPLETELY_NEW = "A1"
    IMPROVEMENT = "A2"
    OLD = "A3"


class K2Type(str, Enum):
    EASY = "EASY"
    HARD = "HARD"
    NORMAL_EASY = "NORMAL_EASY"
    NORMAL_HARD = "NORMAL_HARD"
    DIGITAL_SELF_DEVELOPED = "DIGITAL_SELF_DEVELOPED"
    DIGITAL_CO_DEVELOPED = "DIGITAL_CO_DEVELOPED"
    DIGITAL_OUTSOURCE = "DIGITAL_OUTSOURCE"


class K3MeasureType(str, Enum):
    TIME_SAVED = "TIME_SAVED"
    COST_SAVED = "COST_SAVED"
    UNMEASURABLE = "UNMEASURABLE"


class IdeaScore(Base):
    __tablename__ = "idea_scores"

    id = Column(Integer, primary_key=True, index=True)
    idea_id = Column(Integer, ForeignKey("ideas.id"), nullable=False)
    scorer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    k1_type = Column(SQLEnum(K1Type), nullable=False)
    k1_score = Column(Integer, nullable=False)
    k1_note = Column(Text, nullable=True)

    k2_type = Column(String(50), nullable=False)
    k2_score = Column(Integer, nullable=False)
    k2_selected_codes = Column(Text, nullable=True)
    k2_time_frame = Column(String(50), nullable=True)
    k2_note = Column(Text, nullable=True)

    k3_measure_type = Column(SQLEnum(K3MeasureType), nullable=False)
    k3_option_code = Column(String(20), nullable=True)
    k3_selected_codes = Column(Text, nullable=True)
    k3_score = Column(Integer, nullable=False)
    k3_value = Column(Float, nullable=True)
    k3_note = Column(Text, nullable=True)

    total_score = Column(Integer, nullable=False)
    is_final = Column(Boolean, default=False)
    scored_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    idea = relationship("Idea", back_populates="scores")
    scorer = relationship("User", back_populates="scores")
