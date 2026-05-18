from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class StandardizedIdeaReplication(Base):
    __tablename__ = "standardized_idea_replications"

    id = Column(Integer, primary_key=True, index=True)
    idea_id = Column(Integer, ForeignKey("ideas.id"), nullable=False, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False, index=True)
    requester_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    requester_employee_code = Column(String(50), nullable=False)
    requester_name = Column(String(255), nullable=False)
    idea_title = Column(String(255), nullable=False)
    apply_date = Column(Date, nullable=False)
    description = Column(Text, nullable=False)
    approve = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    idea = relationship("Idea")
    unit = relationship("Unit")
    requester = relationship("User")
