from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text

from app.database import Base


class ScoreCriteria(Base):
    __tablename__ = "score_criteria"

    id = Column(Integer, primary_key=True, index=True)
    criteria_set_id = Column(Integer, ForeignKey("score_criteria_sets.id"), nullable=True, index=True)
    criterion_key = Column(String(50), nullable=False, index=True)
    code = Column(String(20), nullable=False, index=True)
    label = Column(String(500), nullable=False)
    tooltip = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    score = Column(Integer, nullable=False, default=0)
    input_type = Column(String(20), nullable=False, default="radio")
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
