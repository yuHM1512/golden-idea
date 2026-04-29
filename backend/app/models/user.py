from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from app.database import Base

class UserRole(str, Enum):
    EMPLOYEE = "employee"
    ADMIN = "admin"
    TREASURER = "treasurer"
    DEPT_MANAGER = "dept_manager"
    SUB_DEPT_MANAGER = "sub_dept_manager"
    IE_MANAGER = "ie_manager"
    BOD_MANAGER = "bod_manager"
    UNIT_REPRESENT = "unit_represent"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    employee_code = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True)
    phone_number = Column(String(20))
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    role = Column(String(50), default=UserRole.EMPLOYEE.value, nullable=False)
    position = Column(String(255))  # Chức vụ
    # TODO: Uncomment when implementing password-based auth
    # hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    unit = relationship("Unit", back_populates="users", foreign_keys="[User.unit_id]")
    ideas_submitted = relationship("Idea", back_populates="submitter", foreign_keys="[Idea.submitter_id]")
    reviews = relationship("IdeaReview", back_populates="reviewer")
    scores = relationship("IdeaScore", back_populates="scorer")
    payment_slips = relationship("PaymentSlip", back_populates="printed_by_manager", foreign_keys="[PaymentSlip.printed_by_manager_id]")
    paid_payment_slips = relationship("PaymentSlip", back_populates="paid_by_user", foreign_keys="[PaymentSlip.paid_by_user_id]")
    managed_unit = relationship("Unit", back_populates="manager", foreign_keys="[Unit.manager_user_id]")
