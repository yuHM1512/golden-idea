from sqlalchemy import Boolean, Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from app.database import Base

class ReviewLevel(str, Enum):
    """Review hierarchy levels"""
    TECHNICAL = "TECHNICAL"  # KTĐM / PGĐ XN xem xét sơ bộ
    DEPT_HEAD = "DEPT_HEAD"  # Trưởng bộ phận / GĐ XN phê duyệt
    COUNCIL = "COUNCIL"  # Ban cải tiến xem xét
    LEADERSHIP = "LEADERSHIP"  # Lãnh đạo công ty phê duyệt

class ReviewAction(str, Enum):
    """Actions reviewer can take"""
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_INFO = "REQUEST_INFO"
    FORWARD = "FORWARD"

class IdeaReview(Base):
    __tablename__ = "idea_reviews"

    id = Column(Integer, primary_key=True, index=True)
    idea_id = Column(Integer, ForeignKey("ideas.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    level = Column(SQLEnum(ReviewLevel), nullable=False)
    action = Column(SQLEnum(ReviewAction), nullable=False)
    comment = Column(Text, nullable=True)
    recommend_unit_reward = Column(Boolean, nullable=False, default=False)
    reviewed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    idea = relationship("Idea", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews")
