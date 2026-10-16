import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.idea import Idea, IdeaStatus
from app.models.idea_target_group import IdeaTargetGroup, IdeaTargetGroupMember
from app.models.reward_batch import RewardBatch
from app.models.review import ReviewLevel
from app.models.score import IdeaScore
from app.models.score_criteria import ScoreCriteria
from app.models.score_criteria_set import ScoreCriteriaSet
from app.models.user import User
from app.routers.reviews import _is_visible_to_requested_role
from app.services.report_period import default_report_period, effective_report_period, report_period_predicate
from app.services.roles import has_role
from app.time_utils import now_utc

router = APIRouter(prefix="/quarterly-reports", tags=["quarterly-reports"])

REPORT_ROLES = frozenset({"admin", "ie_manager", "digital_manager", "bod_manager"})
COUNCIL_PERIOD_ROLES = frozenset({"admin", "ie_manager", "digital_manager", "bod_manager"})
COMPANY_RESULTS = {"APPROVED_NO_STANDARDIZATION", "APPROVED_STANDARDIZATION"}
UNIT_RESULT = "UNIT_REVIEW"


class PeriodVerification(BaseModel):
    employee_code: str
    year: int = Field(..., ge=2020, le=2100)
    quarter: int = Field(..., ge=1, le=4)
    note: str = Field(default="", max_length=1000)


def _actor(db: Session, employee_code: str, allowed_roles: frozenset[str] = REPORT_ROLES) -> User:
    user = db.query(User).filter(User.employee_code.ilike(employee_code.strip())).first()
    if not user:
        raise HTTPException(404, "Không tìm thấy người dùng")
    if not any(has_role(user, role) for role in allowed_roles):
        raise HTTPException(403, "Không có quyền xem hoặc xác nhận kỳ báo cáo")
    return user


def _latest_ie_score(idea: Idea) -> IdeaScore | None:
    scores = [s for s in idea.scores if s.scorer and (has_role(s.scorer, "ie_manager") or has_role(s.scorer, "digital_manager"))]
    return max(scores, key=lambda s: s.scored_at or datetime.min, default=None)


def _council_result(idea: Idea) -> str | None:
    reviews = [r for r in idea.reviews if r.level == ReviewLevel.COUNCIL and r.council_result_type]
    latest = max(reviews, key=lambda r: r.reviewed_at or datetime.min, default=None)
    return latest.council_result_type if latest else None


def _classification(idea: Idea) -> str:
    if idea.status in {IdeaStatus.REJECTED, IdeaStatus.CANCELLED}:
        return "not_considered"
    result = _council_result(idea)
    if result == "BCT_REJECTED":
        return "not_considered"
    if result == UNIT_RESULT:
        return "unit"
    if result in COMPANY_RESULTS or idea.status in {IdeaStatus.APPROVED, IdeaStatus.REWARDED}:
        return "company"
    return "pending"


def _criteria_catalog(db: Session) -> list[tuple[object, dict[str, int]]]:
    sets = db.query(ScoreCriteriaSet).order_by(ScoreCriteriaSet.effective_from, ScoreCriteriaSet.id).all()
    # Keep inactive rows in the historical lookup: a score may reference a code
    # that was active when it was submitted and disabled later.
    rows = db.query(ScoreCriteria).all()
    by_set: dict[int, dict[str, int]] = {}
    for row in rows:
        if row.criteria_set_id is not None:
            by_set.setdefault(int(row.criteria_set_id), {})[str(row.code)] = int(row.score)
    return [(criteria_set.effective_from, by_set.get(int(criteria_set.id), {})) for criteria_set in sets]


def _criteria_lookup_for_score(score: IdeaScore | None, catalog: list[tuple[object, dict[str, int]]]) -> dict[str, int]:
    if not catalog:
        return {}
    score_date = score.scored_at.date() if score and score.scored_at else catalog[-1][0]
    eligible = [lookup for effective_from, lookup in catalog if effective_from <= score_date]
    return eligible[-1] if eligible else catalog[0][1]


def _subcriteria_scores(score: IdeaScore | None, catalog: list[tuple[object, dict[str, int]]]) -> dict[str, int]:
    if score is None:
        return {}
    lookup = _criteria_lookup_for_score(score, catalog)
    result: dict[str, int] = {}
    k1_code = score.k1_type.value if getattr(score.k1_type, "value", None) else str(score.k1_type or "")
    if k1_code:
        result[k1_code] = int(score.k1_score)
    for code in _codes(score.k2_selected_codes):
        if code in lookup:
            result[code] = int(lookup[code])
    if score.k3_option_code:
        result[str(score.k3_option_code)] = int(score.k3_score)
    else:
        for code in _codes(score.k3_selected_codes):
            if code in lookup:
                result[code] = int(lookup[code])
    return result


def _detail(idea: Idea, classification: str, criteria_catalog: list[tuple[object, dict[str, int]]]) -> dict:
    score = _latest_ie_score(idea)
    benefit = idea.actual_benefit or idea.dept_actual_benefit
    default = default_report_period(idea)
    effective = effective_report_period(idea)
    return {
        "idea_id": idea.id,
        "submitted_at": idea.submitted_at,
        "title": idea.title,
        "full_name": idea.full_name,
        "employee_code": idea.employee_code,
        "unit_id": idea.unit_id,
        "unit_name": idea.unit.name if idea.unit else "—",
        "department": idea.bo_phan,
        "product_code": idea.product_code,
        "classification": classification,
        "k1_code": score.k1_type.value if score and score.k1_type else None,
        "k1_score": score.k1_score if score else None,
        "k2_codes": _codes(score.k2_selected_codes) if score else [],
        "k2_score": score.k2_score if score else None,
        "k3_codes": _codes(score.k3_selected_codes) if score else [],
        "k3_option_code": score.k3_option_code if score else None,
        "k3_score": score.k3_score if score else None,
        "criteria_scores": _subcriteria_scores(score, criteria_catalog),
        "ie_score": score.total_score if score else None,
        "council_score": idea.council_final_score,
        "benefit_value": benefit.benefit_value if benefit else None,
        "default_year": default[0] if default else None,
        "default_quarter": default[1] if default else None,
        "report_year": effective[0] if effective else None,
        "report_quarter": effective[1] if effective else None,
        "period_verified_at": idea.report_period_verified_at,
        "period_note": idea.report_period_note,
    }


def _codes(raw: str | None) -> list[str]:
    try:
        parsed = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    return [str(code) for code in parsed] if isinstance(parsed, list) else []


@router.get("/")
def quarterly_report(
    employee_code: str = Query(...),
    year: int = Query(..., ge=2020, le=2100),
    quarter: int = Query(..., ge=1, le=4),
    db: Session = Depends(get_db),
):
    _actor(db, employee_code)
    ideas = db.query(Idea).options(
        selectinload(Idea.unit),
        selectinload(Idea.scores).selectinload(IdeaScore.scorer),
        selectinload(Idea.reviews),
        selectinload(Idea.actual_benefit),
        selectinload(Idea.dept_actual_benefit),
    ).filter(
        Idea.submitted_at.isnot(None),
        Idea.status != IdeaStatus.DRAFT,
        report_period_predicate(Idea, year, quarter, db.bind.dialect.name),
    ).all()
    criteria_catalog = _criteria_catalog(db)
    items = []
    for idea in ideas:
        classification = _classification(idea)
        items.append(_detail(idea, classification, criteria_catalog))
    items.sort(key=lambda row: (str(row["submitted_at"]), row["idea_id"]))

    groups = db.query(IdeaTargetGroup).filter_by(year=year).order_by(IdeaTargetGroup.name).all()
    members = db.query(IdeaTargetGroupMember).filter_by(year=year).all()
    member_ids: dict[int, set[int]] = {group.id: set() for group in groups}
    for member in members:
        if member.group_id in member_ids:
            member_ids[member.group_id].add(member.unit_id)
    covered = set().union(*member_ids.values()) if member_ids else set()
    units = {item["unit_id"]: item["unit_name"] for item in items}
    buckets = [(group.name, member_ids[group.id], group.headcount, group.target_count) for group in groups]
    buckets.extend((units[unit_id], {unit_id}, None, None) for unit_id in sorted(units) if unit_id not in covered)
    summary = []
    for name, unit_ids, headcount, target in buckets:
        rows = [item for item in items if item["unit_id"] in unit_ids and item["classification"] in {"unit", "company"}]
        summary.append({
            "unit_name": name,
            "annual_headcount": headcount,
            "annual_target": target,
            "idea_count": len(rows),
            "unit_review_count": sum(item["classification"] == "unit" for item in rows),
            "company_review_count": sum(item["classification"] == "company" for item in rows),
            "company_score": sum(item["council_score"] for item in rows if item["classification"] == "company" and item["council_score"] is not None),
            "company_scored_count": sum(item["classification"] == "company" and item["council_score"] is not None for item in rows),
            "benefit_value": sum(item["benefit_value"] or 0 for item in rows if item["benefit_value"] is not None),
            "benefit_count": sum(item["benefit_value"] is not None for item in rows),
        })
    return {"year": year, "quarter": quarter, "summary": summary, "items": items}


@router.put("/ideas/{idea_id}/period")
def verify_report_period(idea_id: int, payload: PeriodVerification, db: Session = Depends(get_db)):
    actor = _actor(db, payload.employee_code, COUNCIL_PERIOD_ROLES)
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(404, "Không tìm thấy ý tưởng")
    if not _is_visible_to_requested_role(actor, idea, "council_review"):
        raise HTTPException(403, "Ý tưởng không thuộc phạm vi xét duyệt Hội đồng của bạn")
    default = default_report_period(idea)
    if default is None:
        raise HTTPException(422, "Ý tưởng chưa có ngày để xác định kỳ mặc định")
    note = payload.note.strip()
    if (payload.year, payload.quarter) != default and not note:
        raise HTTPException(422, "Cần ghi lý do khi chuyển ý tưởng sang quý/năm khác")
    current = effective_report_period(idea)
    requested = (payload.year, payload.quarter)
    if current != requested:
        for period_year, period_quarter in {current, requested}:
            if db.query(RewardBatch.id).filter_by(year=period_year, quarter=period_quarter).first():
                raise HTTPException(409, "Đợt khen thưởng của quý nguồn hoặc quý đích đã được tạo; không thể chuyển kỳ")
    if requested == default:
        idea.report_year = None
        idea.report_quarter = None
        idea.report_period_note = None
        idea.report_period_verified_at = None
        idea.report_period_verified_by_id = None
    else:
        idea.report_year = payload.year
        idea.report_quarter = payload.quarter
        idea.report_period_note = note
        idea.report_period_verified_at = now_utc()
        idea.report_period_verified_by_id = actor.id
    db.commit()
    return {"idea_id": idea.id, "year": requested[0], "quarter": requested[1], "verified_at": idea.report_period_verified_at}
