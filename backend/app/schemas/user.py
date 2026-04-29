from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum
from datetime import datetime

class UserRole(str, Enum):
    EMPLOYEE = "employee"
    ADMIN = "admin"
    TREASURER = "treasurer"
    DEPT_MANAGER = "dept_manager"
    SUB_DEPT_MANAGER = "sub_dept_manager"
    IE_MANAGER = "ie_manager"
    BOD_MANAGER = "bod_manager"
    UNIT_REPRESENT = "unit_represent"

class UserCreate(BaseModel):
    employee_code: str
    full_name: str
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    unit_id: Optional[int] = None
    role: UserRole = UserRole.EMPLOYEE
    position: Optional[str] = None
    # TODO: Uncomment when implementing password-based auth
    # password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    position: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    employee_code: str
    full_name: str
    email: Optional[str]
    phone_number: Optional[str]
    position: Optional[str]
    unit_id: Optional[int]
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    """Simple login: only need employee_code (no password for now)"""
    employee_code: str
    # TODO: Uncomment when implementing password-based auth
    # password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
