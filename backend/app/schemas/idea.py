from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class IdeaCategory(str, Enum):
    TOOLS = "TOOLS"  # Công cụ (cữ gá, ráp form, phụ trợ)
    PROCESS = "PROCESS"  # Quy trình
    DIGITIZATION = "DIGITIZATION"  # Số hóa
    OTHER = "OTHER"

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

class FileAttachmentResponse(BaseModel):
    id: int
    original_filename: str
    file_type: str
    file_size: int
    uploaded_at: datetime

    class Config:
        from_attributes = True

class IdeaParticipant(BaseModel):
    full_name: str = Field(..., description="Họ và tên người tham gia")
    employee_code: Optional[str] = Field(None, description="Mã nhân viên người tham gia")

class IdeaCreate(BaseModel):
    """Phiếu đăng ký ý tưởng - Form submission"""
    full_name: str = Field(..., description="Họ và tên")
    employee_code: Optional[str] = Field(None, description="Mã Nhân Viên (optional)")
    participants: List[IdeaParticipant] = Field(default_factory=list, description="Danh sách người cùng đăng ký")
    phone_number: Optional[str] = Field(None, description="Số điện thoại")
    bo_phan: Optional[str] = Field(None, description="Bộ phận")
    position: Optional[str] = Field(None, description="Chức vụ")
    product_code: Optional[str] = Field(None, description="Mã hàng")
    category: IdeaCategory = Field(..., description="Nội dung ý tưởng liên quan")
    description: str = Field(..., description="Mô tả ý tưởng")
    is_anonymous: bool = Field(default=True, description="Ẩn danh")
    unit_id: int = Field(..., description="Unit ID (from session or dropdown)")

class IdeaUpdate(BaseModel):
    """Update idea (before submission)"""
    full_name: Optional[str] = None
    employee_code: Optional[str] = None
    participants: Optional[List[IdeaParticipant]] = None
    phone_number: Optional[str] = None
    bo_phan: Optional[str] = None
    position: Optional[str] = None
    product_code: Optional[str] = None
    category: Optional[IdeaCategory] = None
    description: Optional[str] = None
    is_anonymous: Optional[bool] = None

class IdeaDetailResponse(BaseModel):
    """Full idea details with attachments"""
    id: int
    full_name: str
    employee_code: Optional[str]
    participants: List[IdeaParticipant] = Field(default_factory=list)
    phone_number: Optional[str]
    bo_phan: Optional[str]
    position: Optional[str]
    product_code: Optional[str]
    category: IdeaCategory
    description: str
    is_anonymous: bool
    status: IdeaStatus
    unit_id: int
    submitter_id: Optional[int]
    submitted_at: datetime
    reviewed_at: Optional[datetime]
    approved_at: Optional[datetime]
    rejection_reason: Optional[str]
    attachments: List[FileAttachmentResponse] = []

    class Config:
        from_attributes = True

class IdeaListResponse(BaseModel):
    """List of ideas (summary)"""
    id: int
    full_name: str
    category: IdeaCategory
    status: IdeaStatus
    submitted_at: datetime
    description: str = Field(..., description="First 100 chars of description")

    class Config:
        from_attributes = True

class IdeaSubmitResponse(BaseModel):
    """Response after submitting idea"""
    id: int
    status: IdeaStatus
    submitted_at: datetime
    message: str = "Ý tưởng của bạn đã được đăng ký thành công"
