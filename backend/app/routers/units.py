from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.unit import Unit
from app.schemas import UnitResponse

router = APIRouter(prefix="/units", tags=["units"])


@router.get("/", response_model=List[UnitResponse])
async def list_units(db: Session = Depends(get_db)):
    return db.query(Unit).order_by(Unit.department.asc().nullslast(), Unit.name.asc()).all()

