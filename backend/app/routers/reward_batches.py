from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import extract
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.idea import Idea, IdeaStatus
from app.models.reward_batch import RewardBatch
from app.models.score import IdeaScore
from app.models.user import User

router = APIRouter(prefix="/reward-batches", tags=["reward-batches"])

QUARTER_MONTHS: dict[int, tuple[int, int]] = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}


class RewardBatchCreate(BaseModel):
    quarter: int = Field(..., ge=1, le=4)
    year: int = Field(..., ge=2020, le=2100)
    coefficient: float = Field(..., gt=0, description="VND / điểm")
    employee_code: str


def _require_user(db: Session, employee_code: str) -> User:
    code = (employee_code or "").strip().upper()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu employee_code")
    user = db.query(User).filter(User.employee_code.ilike(code)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User không tồn tại")
    return user


def _ie_score_for_idea(scores: list[IdeaScore]) -> IdeaScore | None:
    ie_scores = [score for score in (scores or []) if score.scorer and score.scorer.role == "ie_manager"]
    if not ie_scores:
        return None
    ie_scores.sort(key=lambda score: score.scored_at or datetime.min, reverse=True)
    return ie_scores[0]


def _parse_participants(raw_value, fallback_name: str, fallback_code: str) -> list[dict[str, str]]:
    participants: list[dict[str, str]] = []
    if raw_value:
        try:
            parsed = json.loads(raw_value)
        except (TypeError, json.JSONDecodeError):
            parsed = []

        if isinstance(parsed, list):
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                full_name = str(item.get("full_name") or "").strip()
                if not full_name:
                    continue
                employee_code = str(item.get("employee_code") or "").strip().upper()
                participants.append({"full_name": full_name, "employee_code": employee_code})

    if not participants and (fallback_name or "").strip():
        participants = [{"full_name": fallback_name.strip(), "employee_code": (fallback_code or "").strip().upper()}]

    return participants


@router.post("/")
def create_reward_batch(payload: RewardBatchCreate, db: Session = Depends(get_db)):
    user = _require_user(db, payload.employee_code)
    if user.role not in {"admin", "treasurer"}:
        raise HTTPException(status_code=403, detail="Không có quyền tạo đợt khen thưởng")

    batch = RewardBatch(
        quarter=payload.quarter,
        year=payload.year,
        coefficient=payload.coefficient,
        created_by=payload.employee_code.strip().upper(),
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return {
        "id": batch.id,
        "quarter": batch.quarter,
        "year": batch.year,
        "coefficient": batch.coefficient,
        "created_at": batch.created_at,
        "created_by": batch.created_by,
    }


@router.get("/")
def list_reward_batches(db: Session = Depends(get_db)):
    batches = db.query(RewardBatch).order_by(RewardBatch.year.desc(), RewardBatch.quarter.desc()).all()
    return [
        {
            "id": batch.id,
            "quarter": batch.quarter,
            "year": batch.year,
            "coefficient": batch.coefficient,
            "created_at": batch.created_at,
            "created_by": batch.created_by,
        }
        for batch in batches
    ]


@router.get("/{batch_id}/report")
def get_batch_report(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(RewardBatch).filter(RewardBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Đợt khen thưởng không tồn tại")

    month_start, month_end = QUARTER_MONTHS[int(batch.quarter)]

    ideas = (
        db.query(Idea)
        .options(
            joinedload(Idea.unit),
            joinedload(Idea.scores).joinedload(IdeaScore.scorer),
        )
        .filter(
            Idea.status.in_([IdeaStatus.APPROVED, IdeaStatus.REWARDED]),
            Idea.approved_at.isnot(None),
            extract("year", Idea.approved_at) == int(batch.year),
            extract("month", Idea.approved_at) >= int(month_start),
            extract("month", Idea.approved_at) <= int(month_end),
        )
        .order_by(Idea.approved_at)
        .all()
    )

    items: list[dict] = []
    for idea in ideas:
        ie_score = _ie_score_for_idea(idea.scores or [])
        score_value = int(ie_score.total_score) if ie_score else 0
        participants = _parse_participants(idea.participants_json, idea.full_name or "", idea.employee_code or "")
        for participant in participants:
            amount = round(score_value * float(batch.coefficient))
            items.append(
                {
                    "idea_id": idea.id,
                    "full_name": participant.get("full_name") or "—",
                    "unit_name": idea.unit.name if idea.unit else "—",
                    "employee_code": participant.get("employee_code") or "—",
                    "description": idea.description or "",
                    "ie_score": score_value,
                    "amount": amount,
                    "approved_at": idea.approved_at.isoformat() if idea.approved_at else None,
                }
            )

    return {
        "batch": {
            "id": batch.id,
            "quarter": batch.quarter,
            "year": batch.year,
            "coefficient": batch.coefficient,
            "created_at": batch.created_at,
        },
        "items": items,
        "total_amount": sum(item["amount"] for item in items),
    }

