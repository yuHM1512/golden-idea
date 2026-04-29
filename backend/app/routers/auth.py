from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import UserLogin, Token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login endpoint - authenticate user by employee_code only (no password yet)
    Returns JWT token on success

    TODO: Implement login logic
    1. Find user by employee_code in database
    2. Check if user is active
    3. Generate JWT token
    4. Return token + user info

    Future: Add password verification when password auth is enabled
    """
    pass

@router.post("/logout")
async def logout():
    """Logout endpoint"""
    # TODO: Implement logout (optional - could be client-side only)
    pass

@router.get("/me", response_model=dict)
async def get_current_user():
    """Get current authenticated user"""
    # TODO: Implement - extract from JWT token
    pass
