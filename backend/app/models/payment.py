from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class PaymentSlip(Base):
    __tablename__ = "payment_slips"

    id = Column(Integer, primary_key=True, index=True)
    idea_id = Column(Integer, ForeignKey("ideas.id"), nullable=False, unique=True)

    # Employee receiving payment
    employee_code = Column(String(50), nullable=False)
    employee_name = Column(String(255), nullable=False)

    # Payment details
    amount = Column(DECIMAL(10, 2), default=50000.00, nullable=False)  # 50k default

    # Printing info
    printed_by_manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    print_date = Column(DateTime(timezone=True), nullable=True)
    is_printed = Column(Boolean, default=False)

    # Reward payout info
    paid_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    # Signature tracking (for future use - form submission)
    leadership_signed = Column(Boolean, default=False)
    tech_chief_signed = Column(Boolean, default=False)
    dept_head_signed = Column(Boolean, default=False)
    employee_received = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    idea = relationship("Idea", back_populates="payment_slip")
    printed_by_manager = relationship("User", back_populates="payment_slips", foreign_keys=[printed_by_manager_id])
    paid_by_user = relationship("User", back_populates="paid_payment_slips", foreign_keys=[paid_by_user_id])
