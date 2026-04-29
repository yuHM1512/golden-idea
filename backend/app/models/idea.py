from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from app.database import Base

class IdeaStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"  # KTĐM / PGĐ XN reviewing
    DEPT_APPROVED = "DEPT_APPROVED"  # Trưởng bộ phận approved
    COUNCIL_REVIEW = "COUNCIL_REVIEW"  # Ban cải tiến reviewing
    LEADERSHIP_REVIEW = "LEADERSHIP_REVIEW"  # Lãnh đạo reviewing
    APPROVED = "APPROVED"  # Fully approved
    REWARDED = "REWARDED"  # Payment slip printed
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class IdeaCategory(str, Enum):
    """Nội dung ý tưởng liên quan (category)"""
    TOOLS = "TOOLS"  # Công cụ / cữ gá / form / phụ trợ
    PROCESS = "PROCESS"  # Phương pháp quy trình
    DIGITIZATION = "DIGITIZATION"  # Số hóa
    OTHER = "OTHER"

class Idea(Base):
    __tablename__ = "ideas"

    id = Column(Integer, primary_key=True, index=True)

    # From Phiếu đăng ký ý tưởng
    full_name = Column(String(255), nullable=False)
    employee_code = Column(String(50), nullable=True)
    participants_json = Column(Text, nullable=True)
    phone_number = Column(String(20), nullable=True)
    bo_phan = Column(String(255), nullable=True)  # Bộ phận
    position = Column(String(255), nullable=True)  # Chức vụ
    product_code = Column(String(100), nullable=True)  # Mã hàng
    category = Column(String(50), nullable=False)  # Nội dung ý tưởng liên quan
    description = Column(Text, nullable=False)  # Mô tả ý tưởng

    # System fields
    submitter_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Linked user if registered
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    status = Column(SQLEnum(IdeaStatus), default=IdeaStatus.SUBMITTED, nullable=False)
    is_anonymous = Column(Boolean, default=True)  # Ẩn danh flag

    # Workflow tracking
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    submitter = relationship("User", back_populates="ideas_submitted", foreign_keys=[submitter_id])
    unit = relationship("Unit", back_populates="ideas")
    attachments = relationship("FileAttachment", back_populates="idea", cascade="all, delete-orphan")
    scores = relationship("IdeaScore", back_populates="idea", cascade="all, delete-orphan")
    reviews = relationship("IdeaReview", back_populates="idea", cascade="all, delete-orphan")
    payment_slip = relationship("PaymentSlip", back_populates="idea", uselist=False)
    actual_benefit = relationship("ActualBenefitEvaluation", back_populates="idea", uselist=False, cascade="all, delete-orphan")
