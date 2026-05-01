from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
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


class RewardBatchSpecialRewardInput(BaseModel):
    idea_id: int = Field(..., gt=0)
    reward_multiplier: float = Field(..., gt=0, description="Hệ số khen thưởng riêng cho ý tưởng")


class RewardBatchCreate(BaseModel):
    quarter: int = Field(..., ge=1, le=4)
    year: int = Field(..., ge=2020, le=2100)
    coefficient: float = Field(..., gt=0, description="VND / điểm")
    special_rewards: list[RewardBatchSpecialRewardInput] = Field(default_factory=list)
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


def _build_title(idea: Idea) -> str:
    desc = (idea.description or "").strip()
    if not desc:
        return f"Ý tưởng #{idea.id}"
    return desc[:80] + ("..." if len(desc) > 80 else "")


def _normalize_special_rewards(values: list[RewardBatchSpecialRewardInput] | None) -> list[dict[str, float]]:
    normalized: dict[int, float] = {}
    for item in values or []:
        idea_id = int(item.idea_id)
        reward_multiplier = float(item.reward_multiplier)
        if reward_multiplier <= 0:
            continue
        normalized[idea_id] = reward_multiplier
    return [
        {"idea_id": idea_id, "reward_multiplier": reward_multiplier}
        for idea_id, reward_multiplier in sorted(normalized.items(), key=lambda pair: pair[0])
    ]


def _load_special_rewards(raw_value: str | None) -> list[dict[str, float]]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []

    normalized: list[dict[str, float]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        try:
            idea_id = int(item.get("idea_id"))
            reward_multiplier = float(item.get("reward_multiplier"))
        except (TypeError, ValueError):
            continue
        if idea_id <= 0 or reward_multiplier <= 0:
            continue
        normalized.append({"idea_id": idea_id, "reward_multiplier": reward_multiplier})
    return normalized


def _special_reward_map(raw_value: str | None) -> dict[int, float]:
    return {int(item["idea_id"]): float(item["reward_multiplier"]) for item in _load_special_rewards(raw_value)}


def _load_eligible_ideas(db: Session, year: int, quarter: int) -> list[Idea]:
    month_start, month_end = QUARTER_MONTHS[int(quarter)]
    return (
        db.query(Idea)
        .options(
            joinedload(Idea.unit),
            joinedload(Idea.scores).joinedload(IdeaScore.scorer),
        )
        .filter(
            Idea.status.in_([IdeaStatus.APPROVED, IdeaStatus.REWARDED]),
            Idea.approved_at.isnot(None),
            extract("year", Idea.approved_at) == int(year),
            extract("month", Idea.approved_at) >= int(month_start),
            extract("month", Idea.approved_at) <= int(month_end),
        )
        .order_by(Idea.approved_at, Idea.id)
        .all()
    )


def _serialize_batch(batch: RewardBatch) -> dict:
    special_rewards = _load_special_rewards(batch.special_coefficients)
    return {
        "id": batch.id,
        "quarter": batch.quarter,
        "year": batch.year,
        "coefficient": batch.coefficient,
        "special_rewards": special_rewards,
        "special_reward_count": len(special_rewards),
        "created_at": batch.created_at,
        "created_by": batch.created_by,
    }


@router.post("/")
def create_reward_batch(payload: RewardBatchCreate, db: Session = Depends(get_db)):
    user = _require_user(db, payload.employee_code)
    if user.role not in {"admin", "treasurer"}:
        raise HTTPException(status_code=403, detail="Không có quyền tạo đợt khen thưởng")

    eligible_idea_ids = {idea.id for idea in _load_eligible_ideas(db, payload.year, payload.quarter)}
    special_rewards = _normalize_special_rewards(payload.special_rewards)
    invalid_idea_ids = [item["idea_id"] for item in special_rewards if item["idea_id"] not in eligible_idea_ids]
    if invalid_idea_ids:
        joined_ids = ", ".join(str(item) for item in invalid_idea_ids)
        raise HTTPException(status_code=400, detail=f"Ý tưởng nổi trội không thuộc quý/năm đã chọn: {joined_ids}")

    batch = RewardBatch(
        quarter=payload.quarter,
        year=payload.year,
        coefficient=payload.coefficient,
        special_coefficients=json.dumps(special_rewards, ensure_ascii=False) if special_rewards else None,
        created_by=payload.employee_code.strip().upper(),
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return _serialize_batch(batch)


@router.get("/")
def list_reward_batches(db: Session = Depends(get_db)):
    batches = db.query(RewardBatch).order_by(RewardBatch.year.desc(), RewardBatch.quarter.desc()).all()
    return [_serialize_batch(batch) for batch in batches]


@router.get("/candidates")
def get_reward_batch_candidates(
    quarter: int = Query(..., ge=1, le=4),
    year: int = Query(..., ge=2020, le=2100),
    db: Session = Depends(get_db),
):
    ideas = _load_eligible_ideas(db, year, quarter)
    items: list[dict] = []
    for idea in ideas:
        ie_score = _ie_score_for_idea(idea.scores or [])
        score_value = int(ie_score.total_score) if ie_score else 0
        participants = _parse_participants(idea.participants_json, idea.full_name or "", idea.employee_code or "")
        items.append(
            {
                "idea_id": idea.id,
                "title": _build_title(idea),
                "description": idea.description or "",
                "unit_name": idea.unit.name if idea.unit else "—",
                "ie_score": score_value,
                "participant_count": len(participants),
                "employee_codes": [item.get("employee_code") or "" for item in participants if item.get("employee_code")],
                "approved_at": idea.approved_at.isoformat() if idea.approved_at else None,
            }
        )
    return {"items": items}


@router.get("/{batch_id}/report")
def get_batch_report(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(RewardBatch).filter(RewardBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Đợt khen thưởng không tồn tại")

    ideas = _load_eligible_ideas(db, int(batch.year), int(batch.quarter))
    special_rewards = _special_reward_map(batch.special_coefficients)

    items: list[dict] = []
    for idea in ideas:
        ie_score = _ie_score_for_idea(idea.scores or [])
        score_value = int(ie_score.total_score) if ie_score else 0
        reward_multiplier = float(special_rewards.get(idea.id, 1))
        participants = _parse_participants(idea.participants_json, idea.full_name or "", idea.employee_code or "")
        for participant in participants:
            amount = round(score_value * float(batch.coefficient) * reward_multiplier)
            items.append(
                {
                    "idea_id": idea.id,
                    "title": _build_title(idea),
                    "full_name": participant.get("full_name") or "—",
                    "unit_name": idea.unit.name if idea.unit else "—",
                    "employee_code": participant.get("employee_code") or "—",
                    "description": idea.description or "",
                    "ie_score": score_value,
                    "reward_multiplier": reward_multiplier,
                    "amount": amount,
                    "approved_at": idea.approved_at.isoformat() if idea.approved_at else None,
                }
            )

    return {
        "batch": _serialize_batch(batch),
        "items": items,
        "total_amount": sum(item["amount"] for item in items),
    }
