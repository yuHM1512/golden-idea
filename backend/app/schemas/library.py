from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

from app.schemas.idea import IdeaStatus


class IdeaLibraryRow(BaseModel):
    id: int
    title: str
    category: str
    status: IdeaStatus
    submitted_at: datetime
    unit_id: int
    unit_name: str
    full_name: str
    employee_code: Optional[str] = None
    product_code: Optional[str] = None
    description: str
    description_before: Optional[str] = None
    description_after: Optional[str] = None
    attachment_count: int = 0
    library_type: str = "standardization"

    class Config:
        from_attributes = True


class IdeaLibraryAttachment(BaseModel):
    id: int
    original_filename: str
    file_type: str
    file_size: int
    file_url: str
    attachment_type: str = "after"
    uploaded_at: Optional[datetime] = None


class IdeaLibraryDetail(BaseModel):
    id: int
    title: str
    category: str
    status: IdeaStatus
    submitted_at: datetime
    unit_id: int
    unit_name: str
    full_name: str
    employee_code: Optional[str] = None
    phone_number: Optional[str] = None
    position: Optional[str] = None
    product_code: Optional[str] = None
    description: str
    description_before: Optional[str] = None
    description_after: Optional[str] = None
    attachment_count: int = 0
    library_type: str = "standardization"
    attachments: List[IdeaLibraryAttachment] = []


class StandardizedIdeaReplicationCreate(BaseModel):
    employee_code: str
    idea_id: int
    apply_date: date
    description: str


class StandardizedIdeaReplicationResponse(BaseModel):
    id: int
    idea_id: int
    unit_id: int
    unit_name: str
    requester_user_id: Optional[int] = None
    requester_employee_code: str
    requester_name: str
    idea_title: str
    apply_date: date
    description: str
    approve: bool
    created_at: datetime
