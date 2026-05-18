from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class IdeaStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    DEPT_APPROVED = "DEPT_APPROVED"
    COUNCIL_REVIEW = "COUNCIL_REVIEW"
    LEADERSHIP_REVIEW = "LEADERSHIP_REVIEW"
    APPROVED = "APPROVED"
    REWARDED = "REWARDED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class IdeaCategory(str, Enum):
    TOOLS = "TOOLS"
    PROCESS = "PROCESS"
    DIGITIZATION = "DIGITIZATION"
    OTHER = "OTHER"


class Idea(Base):
    __tablename__ = "ideas"

    id = Column(Integer, primary_key=True, index=True)

    # Submission fields
    full_name = Column(String(255), nullable=False)
    employee_code = Column(String(50), nullable=True)
    participants_json = Column(Text, nullable=True)
    phone_number = Column(String(20), nullable=True)
    bo_phan = Column(String(255), nullable=True)
    position = Column(String(255), nullable=True)
    title = Column(String(255), nullable=False)
    product_code = Column(String(100), nullable=True)
    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)

    # System fields
    submitter_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    status = Column(SQLEnum(IdeaStatus), default=IdeaStatus.SUBMITTED, nullable=False)
    is_anonymous = Column(Boolean, default=True)
    eligible_register_reward = Column(Boolean, default=False, nullable=False)
    bod_register_approved = Column(Boolean, default=False, nullable=False)
    bod_register_approved_at = Column(DateTime(timezone=True), nullable=True)
    bod_register_approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    council_final_score = Column(Integer, nullable=True)
    council_final_scored_at = Column(DateTime(timezone=True), nullable=True)
    council_final_scored_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    council_final_note = Column(Text, nullable=True)
    council_is_featured = Column(Boolean, default=False, nullable=False)
    council_reward_multiplier = Column(Float, nullable=True)

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
    actual_benefit = relationship(
        "ActualBenefitEvaluation",
        back_populates="idea",
        uselist=False,
        cascade="all, delete-orphan",
    )
