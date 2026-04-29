from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any

from app.database import get_db
from app.models.unit import Unit
from app.models.idea import Idea, IdeaStatus, IdeaCategory
from app.models.actual_benefit import ActualBenefitEvaluation

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

LIBRARY_DASHBOARD_STATUSES = (
    IdeaStatus.APPROVED,
    IdeaStatus.REWARDED,
)


@router.get("/ideas-by-unit", response_model=List[Dict[str, Any]])
async def ideas_by_unit(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2100),
    db: Session = Depends(get_db),
):
    """
    Simple dashboard: number of ideas per unit.
    Includes units with 0 ideas.
    """
    idea_join = (Idea.unit_id == Unit.id) & (Idea.status.in_(LIBRARY_DASHBOARD_STATUSES))
    if year is not None:
        idea_join = idea_join & (func.extract("year", Idea.submitted_at) == year)
    if month is not None:
        idea_join = idea_join & (func.extract("month", Idea.submitted_at) == month)

    rows = (
        db.query(
            Unit.id.label("unit_id"),
            Unit.name.label("unit_name"),
            Unit.department.label("department"),
            func.count(Idea.id).label("idea_count"),
        )
        .outerjoin(Idea, idea_join)
        .group_by(Unit.id, Unit.name, Unit.department)
        .order_by(Unit.department.asc().nullslast(), Unit.name.asc())
        .all()
    )

    return [
        {
            "unit_id": r.unit_id,
            "unit_name": r.unit_name,
            "department": r.department,
            "idea_count": int(r.idea_count or 0),
        }
        for r in rows
    ]


@router.get("/idea-metrics", response_model=Dict[str, Any])
async def idea_metrics(db: Session = Depends(get_db)):
    """
    KPI metrics for idea lifecycle milestones.
    """
    rows = db.query(Idea.status, func.count(Idea.id)).group_by(Idea.status).all()
    by_status = {getattr(status, "value", str(status)): int(count) for status, count in rows}

    total = int(sum(by_status.values()))
    dept_recognized = int(
        (by_status.get(IdeaStatus.DEPT_APPROVED.value, 0))
        + (by_status.get(IdeaStatus.COUNCIL_REVIEW.value, 0))
        + (by_status.get(IdeaStatus.LEADERSHIP_REVIEW.value, 0))
        + (by_status.get(IdeaStatus.APPROVED.value, 0))
        + (by_status.get(IdeaStatus.REWARDED.value, 0))
    )
    ie_recognized = int(
        (by_status.get(IdeaStatus.LEADERSHIP_REVIEW.value, 0))
        + (by_status.get(IdeaStatus.APPROVED.value, 0))
        + (by_status.get(IdeaStatus.REWARDED.value, 0))
    )
    council_recognized = int(
        (by_status.get(IdeaStatus.APPROVED.value, 0))
        + (by_status.get(IdeaStatus.REWARDED.value, 0))
    )

    total_benefit_value = (
        db.query(func.coalesce(func.sum(ActualBenefitEvaluation.benefit_value), 0.0))
        .join(Idea, Idea.id == ActualBenefitEvaluation.idea_id)
        .filter(Idea.status.in_(LIBRARY_DASHBOARD_STATUSES))
        .scalar()
    )

    return {
        "total": total,
        "by_status": by_status,
        "dept_recognized": dept_recognized,
        "ie_recognized": ie_recognized,
        "council_recognized": council_recognized,
        "total_benefit_value": float(total_benefit_value or 0.0),
    }


@router.get("/ideas-by-category", response_model=List[Dict[str, Any]])
async def ideas_by_category(db: Session = Depends(get_db)):
    """
    For charts: number of ideas per category.
    """
    rows = (
        db.query(Idea.category, func.count(Idea.id))
        .filter(Idea.status.in_(LIBRARY_DASHBOARD_STATUSES))
        .group_by(Idea.category)
        .order_by(func.count(Idea.id).desc())
        .all()
    )
    return [{"category": getattr(category, "value", str(category)), "count": int(count)} for category, count in rows]
