from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)  # Đơn vị / Bộ phận
    department = Column(String(255))  # Optional: department classification
    manager_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="unit", foreign_keys="User.unit_id")
    manager = relationship("User", back_populates="managed_unit", foreign_keys=[manager_user_id])
    ideas = relationship("Idea", back_populates="unit")
