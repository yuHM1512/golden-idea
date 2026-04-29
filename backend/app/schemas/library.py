from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.schemas.idea import IdeaCategory, IdeaStatus


class IdeaLibraryRow(BaseModel):
    id: int
    title: str
    category: IdeaCategory
    status: IdeaStatus
    submitted_at: datetime
    unit_id: int
    unit_name: str
    full_name: str
    employee_code: Optional[str] = None
    description: str
    attachment_count: int = 0

    class Config:
        from_attributes = True


class IdeaLibraryAttachment(BaseModel):
    id: int
    original_filename: str
    file_type: str
    file_size: int
    file_url: str
    uploaded_at: Optional[datetime] = None


class IdeaLibraryDetail(BaseModel):
    id: int
    title: str
    category: IdeaCategory
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
    attachment_count: int = 0
    attachments: List[IdeaLibraryAttachment] = []
