from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.database import get_db
from app.models.unit import Unit
from app.models.user import User, UserRole
from app.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


def _apply_user_fields(user: User, data: UserCreate) -> None:
    user.employee_code = data.employee_code.strip().upper()
    user.full_name = data.full_name.strip()
    user.email = data.email
    user.phone_number = data.phone_number
    user.position = data.position
    user.unit_id = data.unit_id
    user.role = data.role.value
    user.is_active = True


def _ensure_unit_exists(db: Session, unit_id: int | None) -> Unit | None:
    if unit_id is None:
        return None
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unit id={unit_id} không tồn tại",
        )
    return unit


def _validate_role_unit_requirement(db: Session, data: UserCreate) -> None:
    if data.role in {UserRole.BOD_MANAGER, UserRole.TREASURER, UserRole.ADMIN}:
        return
    if data.unit_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role này bắt buộc phải chọn đơn vị",
        )
    _ensure_unit_exists(db, data.unit_id)


def _assign_dept_manager_if_needed(db: Session, user: User) -> None:
    if user.role != UserRole.DEPT_MANAGER.value:
        return
    unit = db.query(Unit).filter(Unit.id == user.unit_id).first()
    if unit is None:
        return
    unit.manager_user_id = user.id


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def upsert_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Create or update a user by employee_code.
    If role=dept_manager, automatically sets units.manager_user_id for that unit.
    """
    _validate_role_unit_requirement(db, user_in)

    employee_code = user_in.employee_code.strip().upper()
    user = db.query(User).filter(User.employee_code == employee_code).first()
    created = False
    if user is None:
        user = User(employee_code=employee_code, full_name=user_in.full_name.strip(), unit_id=user_in.unit_id)
        created = True
        db.add(user)

    _apply_user_fields(user, user_in)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Trùng employee_code hoặc email") from e

    if created:
        db.refresh(user)

    _assign_dept_manager_if_needed(db, user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/", response_model=List[UserResponse])
async def list_users(skip: int = 0, limit: int = 500, db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id.asc()).offset(skip).limit(limit).all()


@router.get("/by-code/{employee_code}", response_model=UserResponse)
async def get_user_by_code(employee_code: str, db: Session = Depends(get_db)):
    code = employee_code.strip()
    user = db.query(User).filter(func.upper(User.employee_code) == code.upper()).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User không tồn tại")
    return user


@router.post("/bulk", response_model=List[UserResponse], status_code=status.HTTP_201_CREATED)
async def upsert_users_bulk(users_in: List[UserCreate], db: Session = Depends(get_db)):
    """
    Bulk create/update users.
    If any user has role=dept_manager, automatically sets units.manager_user_id.
    """
    if not users_in:
        return []

    for item in users_in:
        _validate_role_unit_requirement(db, item)

    unit_ids = {u.unit_id for u in users_in if u.unit_id is not None}
    existing_units = {u.id for u in db.query(Unit.id).filter(Unit.id.in_(unit_ids)).all()}
    missing = sorted(unit_ids - existing_units)
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unit id không tồn tại: {missing}")

    employee_codes = [u.employee_code.strip().upper() for u in users_in]
    existing_users = db.query(User).filter(User.employee_code.in_(employee_codes)).all()
    existing_by_code = {u.employee_code: u for u in existing_users}

    result: list[User] = []
    for item in users_in:
        code = item.employee_code.strip().upper()
        user = existing_by_code.get(code)
        if user is None:
            user = User(employee_code=code, full_name=item.full_name.strip(), unit_id=item.unit_id)
            db.add(user)
            existing_by_code[code] = user
        _apply_user_fields(user, item)
        result.append(user)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Trùng employee_code hoặc email") from e

    # Ensure ids exist, then assign dept managers
    for user in result:
        if user.id is None:
            db.refresh(user)
        _assign_dept_manager_if_needed(db, user)

    db.commit()
    for user in result:
        db.refresh(user)
    return result
