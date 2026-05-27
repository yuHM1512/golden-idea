from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


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
    attachment_type: str = "after"
    uploaded_at: datetime

    class Config:
        from_attributes = True


class DirectUploadSessionRequest(BaseModel):
    original_filename: str
    file_size: int = Field(..., ge=1)
    content_type: Optional[str] = None
    attachment_type: Optional[str] = "after"


class DirectUploadSessionResponse(BaseModel):
    session_url: str
    folder_id: str


class DirectUploadCompleteRequest(BaseModel):
    drive_file_id: Optional[str] = None
    original_filename: str
    file_size: Optional[int] = Field(default=None, ge=1)
    content_type: Optional[str] = None
    attachment_type: Optional[str] = "after"


class IdeaParticipant(BaseModel):
    full_name: str = Field(..., description="Họ và tên người tham gia")
    employee_code: Optional[str] = Field(None, description="Mã nhân viên người tham gia")


class IdeaCreate(BaseModel):
    full_name: str = Field(..., description="Họ và tên")
    employee_code: Optional[str] = Field(None, description="Mã nhân viên")
    participants: List[IdeaParticipant] = Field(default_factory=list, description="Danh sách người cùng đăng ký")
    phone_number: Optional[str] = Field(None, description="Số điện thoại")
    bo_phan: Optional[str] = Field(None, description="Bộ phận")
    position: Optional[str] = Field(None, description="Chức vụ")
    title: str = Field(..., description="Tên ý tưởng")
    product_code: Optional[str] = Field(None, description="Mã hàng")
    category: str = Field(..., description="Nội dung ý tưởng liên quan")
    description: Optional[str] = Field(None, description="Mô tả ý tưởng gộp")
    description_before: Optional[str] = Field(None, description="Mô tả trước cải tiến")
    description_after: Optional[str] = Field(None, description="Mô tả sau cải tiến")
    is_anonymous: bool = Field(default=True, description="Ẩn danh")
    unit_id: int = Field(..., description="Unit ID")


class IdeaUpdate(BaseModel):
    full_name: Optional[str] = None
    employee_code: Optional[str] = None
    participants: Optional[List[IdeaParticipant]] = None
    phone_number: Optional[str] = None
    bo_phan: Optional[str] = None
    position: Optional[str] = None
    title: Optional[str] = None
    product_code: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    description_before: Optional[str] = None
    description_after: Optional[str] = None
    is_anonymous: Optional[bool] = None


class IdeaDetailResponse(BaseModel):
    id: int
    full_name: str
    employee_code: Optional[str]
    participants: List[IdeaParticipant] = Field(default_factory=list)
    phone_number: Optional[str]
    bo_phan: Optional[str]
    position: Optional[str]
    title: str
    product_code: Optional[str]
    category: str
    description: str
    description_before: Optional[str] = None
    description_after: Optional[str] = None
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
    id: int
    title: str
    full_name: str
    category: str
    status: IdeaStatus
    submitted_at: datetime
    description: str = Field(..., description="First 100 chars of description")
    description_before: Optional[str] = None
    description_after: Optional[str] = None

    class Config:
        from_attributes = True


class IdeaSubmitResponse(BaseModel):
    id: int
    status: IdeaStatus
    submitted_at: datetime
    message: str = "Ý tưởng của bạn đã được đăng ký thành công"
