from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UnitCreate(BaseModel):
    name: str
    department: Optional[str] = None
    manager_user_id: Optional[int] = None

class UnitUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    manager_user_id: Optional[int] = None

class UnitResponse(BaseModel):
    id: int
    name: str
    department: Optional[str]
    manager_user_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UnitWithUsers(UnitResponse):
    user_count: int = 0
