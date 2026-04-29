from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal

class PaymentSlipCreate(BaseModel):
    """Generate payment slip for approved idea"""
    idea_id: int

class PaymentSlipUpdate(BaseModel):
    """Update payment slip status"""
    is_printed: Optional[bool] = None
    leadership_signed: Optional[bool] = None
    tech_chief_signed: Optional[bool] = None
    dept_head_signed: Optional[bool] = None
    employee_received: Optional[bool] = None

class PaymentSlipResponse(BaseModel):
    """Payment slip details"""
    id: int
    idea_id: int
    employee_code: str
    employee_name: str
    amount: Decimal
    printed_by_manager_id: Optional[int]
    print_date: Optional[datetime]
    is_printed: bool
    paid_by_user_id: Optional[int]
    paid_at: Optional[datetime]
    leadership_signed: bool
    tech_chief_signed: bool
    dept_head_signed: bool
    employee_received: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PaymentSlipListResponse(BaseModel):
    """List of payment slips for unit manager"""
    id: int
    idea_id: int
    employee_name: str
    amount: Decimal
    is_printed: bool
    print_date: Optional[datetime]
    paid_by_user_id: Optional[int] = None
    paid_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PaymentSlipPrintRequest(BaseModel):
    """Request to print payment slip"""
    slip_id: int

class PaymentSlipPrintResponse(BaseModel):
    """Response after printing"""
    message: str = "Giấy nhận tiền đã được in"
    pdf_url: Optional[str] = None
