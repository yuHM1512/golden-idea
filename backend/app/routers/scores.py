import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.score import IdeaScore
from app.models.score_criteria import ScoreCriteria
from app.models.score_criteria_set import ScoreCriteriaSet
from app.models.user import User
from app.schemas import (
    IdeaScoreResponse,
    K1ScoreBreakdown,
    K2ScoreBreakdown,
    K3ScoreGuide,
    ScoreCriteriaItemResponse,
    ScoreCriteriaSetCreate,
    ScoreCriteriaSetResponse,
    ScoreCriteriaSetUpdate,
)

router = APIRouter(prefix="/scores", tags=["scores"])


def _parse_codes(value):
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _to_score_response(score: IdeaScore) -> IdeaScoreResponse:
    return IdeaScoreResponse(
        id=score.id,
        idea_id=score.idea_id,
        scorer_id=score.scorer_id,
        k1_type=str(score.k1_type).split(".")[-1],
        k1_score=score.k1_score,
        k1_note=score.k1_note,
        k2_type=score.k2_type,
        k2_score=score.k2_score,
        k2_selected_codes=_parse_codes(score.k2_selected_codes),
        k2_time_frame=score.k2_time_frame,
        k2_note=score.k2_note,
        k3_measure_type=str(score.k3_measure_type).split(".")[-1],
        k3_option_code=score.k3_option_code,
        k3_selected_codes=_parse_codes(score.k3_selected_codes),
        k3_score=score.k3_score,
        k3_value=score.k3_value,
        k3_note=score.k3_note,
        total_score=score.total_score,
        is_final=score.is_final,
        scored_at=score.scored_at,
    )


def _require_criteria_manager(db: Session, employee_code: str) -> User:
    code = (employee_code or "").strip().upper()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu employee_code")
    user = db.query(User).filter(User.employee_code.ilike(code)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User không tồn tại")
    if user.role not in {"admin", "ie_manager"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền quản lý tiêu chí")
    return user


def _resolve_active_criteria_set(db: Session, apply_date: date | None = None) -> ScoreCriteriaSet | None:
    target_date = apply_date or date.today()
    active_set = (
        db.query(ScoreCriteriaSet)
        .filter(ScoreCriteriaSet.effective_from <= target_date)
        .order_by(ScoreCriteriaSet.effective_from.desc(), ScoreCriteriaSet.id.desc())
        .first()
    )
    if active_set is not None:
        return active_set
    return db.query(ScoreCriteriaSet).order_by(ScoreCriteriaSet.effective_from.asc(), ScoreCriteriaSet.id.asc()).first()


def _serialize_criteria_item(row: ScoreCriteria) -> ScoreCriteriaItemResponse:
    return ScoreCriteriaItemResponse(
        id=row.id,
        criteria_set_id=row.criteria_set_id,
        criterion_key=row.criterion_key,
        code=row.code,
        label=row.label,
        tooltip=row.tooltip,
        note=row.note,
        score=row.score,
        input_type=row.input_type,
        sort_order=row.sort_order,
        is_active=row.is_active,
    )


def _serialize_criteria_set(row: ScoreCriteriaSet, items: list[ScoreCriteria]) -> ScoreCriteriaSetResponse:
    return ScoreCriteriaSetResponse(
        id=row.id,
        name=row.name,
        effective_from=row.effective_from,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
        items=[_serialize_criteria_item(item) for item in items],
    )


def _criteria_payload(db: Session, apply_date: date | None = None):
    active_set = _resolve_active_criteria_set(db, apply_date)
    rows = []
    if active_set is not None:
        rows = (
            db.query(ScoreCriteria)
            .filter(
                ScoreCriteria.criteria_set_id == active_set.id,
                ScoreCriteria.is_active.is_(True),
            )
            .order_by(ScoreCriteria.criterion_key.asc(), ScoreCriteria.sort_order.asc(), ScoreCriteria.id.asc())
            .all()
        )

    grouped = {}
    for row in rows:
        grouped.setdefault(row.criterion_key, []).append(
            {
                "id": row.id,
                "criteria_set_id": row.criteria_set_id,
                "code": row.code,
                "label": row.label,
                "tooltip": row.tooltip,
                "note": row.note,
                "score": row.score,
                "input_type": row.input_type,
                "sort_order": row.sort_order,
            }
        )
    return {
        "criteria_set": None
        if active_set is None
        else {
            "id": active_set.id,
            "name": active_set.name,
            "effective_from": active_set.effective_from.isoformat(),
            "created_by": active_set.created_by,
            "created_at": active_set.created_at.isoformat() if active_set.created_at else None,
            "updated_at": active_set.updated_at.isoformat() if active_set.updated_at else None,
        },
        "k1": grouped.get("K1", []),
        "k2": {
            "EASY": grouped.get("K2_EASY", []),
            "HARD": grouped.get("K2_HARD", []),
        },
        "k3": {
            "TIME_SAVED": grouped.get("K3_TIME_SAVED", []),
            "COST_SAVED": grouped.get("K3_COST_SAVED", []),
            "UNMEASURABLE": grouped.get("K3_UNMEASURABLE", []),
        },
    }


def _normalize_set_name(raw_name: str | None, effective_from: date) -> str:
    candidate = (raw_name or "").strip()
    if candidate:
        return candidate
    return f"Bo tieu chi ap dung tu {effective_from.isoformat()}"


def _replace_set_items(db: Session, criteria_set_id: int, items: list):
    db.query(ScoreCriteria).filter(ScoreCriteria.criteria_set_id == criteria_set_id).delete()
    for item in items:
        db.add(
            ScoreCriteria(
                criteria_set_id=criteria_set_id,
                criterion_key=item.criterion_key.strip(),
                code=item.code.strip(),
                label=item.label.strip(),
                tooltip=(item.tooltip or "").strip() or None,
                note=(item.note or "").strip() or None,
                score=item.score,
                input_type=(item.input_type or "radio").strip(),
                sort_order=item.sort_order,
                is_active=item.is_active,
            )
        )


@router.get("/{idea_id}/latest", response_model=IdeaScoreResponse)
async def get_latest_score(idea_id: int, role: str | None = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(IdeaScore).filter(IdeaScore.idea_id == idea_id)
    if role:
        query = query.join(IdeaScore.scorer).filter(User.role == role)
    score = query.order_by(IdeaScore.scored_at.desc(), IdeaScore.id.desc()).first()
    if score is None:
        raise HTTPException(status_code=404, detail="Chua co diem")
    return _to_score_response(score)


@router.get("/{idea_id}/history", response_model=list[IdeaScoreResponse])
async def get_score_history(idea_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(IdeaScore)
        .options(joinedload(IdeaScore.scorer))
        .filter(IdeaScore.idea_id == idea_id)
        .order_by(IdeaScore.scored_at.desc(), IdeaScore.id.desc())
        .all()
    )
    return [_to_score_response(row) for row in rows]


@router.get("/guide/k1", response_model=K1ScoreBreakdown, tags=["reference"])
async def get_k1_guide():
    return K1ScoreBreakdown()


@router.get("/guide/k2", response_model=K2ScoreBreakdown, tags=["reference"])
async def get_k2_guide():
    return K2ScoreBreakdown()


@router.get("/guide/k3", response_model=K3ScoreGuide, tags=["reference"])
async def get_k3_guide():
    return K3ScoreGuide()


@router.get("/guide/criteria")
async def get_scoring_criteria(apply_date: date | None = Query(default=None), db: Session = Depends(get_db)):
    return _criteria_payload(db, apply_date)


@router.get("/criteria-sets", response_model=list[ScoreCriteriaSetResponse])
async def list_criteria_sets(employee_code: str = Query(...), db: Session = Depends(get_db)):
    _require_criteria_manager(db, employee_code)
    rows = db.query(ScoreCriteriaSet).order_by(ScoreCriteriaSet.effective_from.desc(), ScoreCriteriaSet.id.desc()).all()
    items = db.query(ScoreCriteria).order_by(ScoreCriteria.sort_order.asc(), ScoreCriteria.id.asc()).all()
    by_set = {}
    for item in items:
        by_set.setdefault(item.criteria_set_id, []).append(item)
    return [_serialize_criteria_set(row, by_set.get(row.id, [])) for row in rows]


@router.get("/criteria-sets/{criteria_set_id}", response_model=ScoreCriteriaSetResponse)
async def get_criteria_set(criteria_set_id: int, employee_code: str = Query(...), db: Session = Depends(get_db)):
    _require_criteria_manager(db, employee_code)
    criteria_set = db.query(ScoreCriteriaSet).filter(ScoreCriteriaSet.id == criteria_set_id).first()
    if criteria_set is None:
        raise HTTPException(status_code=404, detail="Bo tieu chi khong ton tai")
    items = (
        db.query(ScoreCriteria)
        .filter(ScoreCriteria.criteria_set_id == criteria_set_id)
        .order_by(ScoreCriteria.sort_order.asc(), ScoreCriteria.id.asc())
        .all()
    )
    return _serialize_criteria_set(criteria_set, items)


@router.post("/criteria-sets", response_model=ScoreCriteriaSetResponse)
async def create_criteria_set(payload: ScoreCriteriaSetCreate, db: Session = Depends(get_db)):
    user = _require_criteria_manager(db, payload.employee_code)
    if not payload.items:
        raise HTTPException(status_code=400, detail="Bo tieu chi phai co it nhat 1 dong")

    criteria_set = ScoreCriteriaSet(
        name=_normalize_set_name(payload.name, payload.effective_from),
        effective_from=payload.effective_from,
        created_by=user.employee_code,
    )
    db.add(criteria_set)
    db.flush()
    _replace_set_items(db, criteria_set.id, payload.items)
    db.commit()
    db.refresh(criteria_set)
    items = (
        db.query(ScoreCriteria)
        .filter(ScoreCriteria.criteria_set_id == criteria_set.id)
        .order_by(ScoreCriteria.sort_order.asc(), ScoreCriteria.id.asc())
        .all()
    )
    return _serialize_criteria_set(criteria_set, items)


@router.put("/criteria-sets/{criteria_set_id}", response_model=ScoreCriteriaSetResponse)
async def update_criteria_set(criteria_set_id: int, payload: ScoreCriteriaSetUpdate, db: Session = Depends(get_db)):
    _require_criteria_manager(db, payload.employee_code)
    criteria_set = db.query(ScoreCriteriaSet).filter(ScoreCriteriaSet.id == criteria_set_id).first()
    if criteria_set is None:
        raise HTTPException(status_code=404, detail="Bo tieu chi khong ton tai")
    if not payload.items:
        raise HTTPException(status_code=400, detail="Bo tieu chi phai co it nhat 1 dong")

    criteria_set.name = _normalize_set_name(payload.name, payload.effective_from)
    criteria_set.effective_from = payload.effective_from
    db.add(criteria_set)
    _replace_set_items(db, criteria_set.id, payload.items)
    db.commit()
    db.refresh(criteria_set)
    items = (
        db.query(ScoreCriteria)
        .filter(ScoreCriteria.criteria_set_id == criteria_set.id)
        .order_by(ScoreCriteria.sort_order.asc(), ScoreCriteria.id.asc())
        .all()
    )
    return _serialize_criteria_set(criteria_set, items)
