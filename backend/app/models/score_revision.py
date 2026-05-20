from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class IdeaScoreRevision(Base):
    __tablename__ = "idea_score_revisions"

    id = Column(Integer, primary_key=True, index=True)
    score_id = Column(Integer, ForeignKey("idea_scores.id"), nullable=False, index=True)
    idea_id = Column(Integer, ForeignKey("ideas.id"), nullable=False, index=True)
    edited_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    original_scorer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    original_scored_at = Column(DateTime(timezone=True), nullable=True)
    original_updated_at = Column(DateTime(timezone=True), nullable=True)

    k1_type = Column(String(50), nullable=False)
    k1_score = Column(Integer, nullable=False)
    k1_note = Column(Text, nullable=True)

    k2_type = Column(String(50), nullable=False)
    k2_score = Column(Integer, nullable=False)
    k2_selected_codes = Column(Text, nullable=True)
    k2_time_frame = Column(String(50), nullable=True)
    k2_note = Column(Text, nullable=True)

    k3_measure_type = Column(String(50), nullable=False)
    k3_option_code = Column(String(20), nullable=True)
    k3_selected_codes = Column(Text, nullable=True)
    k3_score = Column(Integer, nullable=False)
    k3_value = Column(Float, nullable=True)
    k3_note = Column(Text, nullable=True)

    total_score = Column(Integer, nullable=False)
    is_final = Column(Boolean, default=False, nullable=False)
    revision_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    score = relationship("IdeaScore")
    idea = relationship("Idea")
    edited_by = relationship("User", foreign_keys=[edited_by_id])
    original_scorer = relationship("User", foreign_keys=[original_scorer_id])
