from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Iterable, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.actual_benefit import ActualBenefitEvaluation
from app.models.payment import PaymentSlip
from app.models.idea import Idea, IdeaStatus
from app.models.review import IdeaReview, ReviewAction, ReviewLevel
from app.models.score import IdeaScore, K2Type, K3MeasureType
from app.models.score_criteria import ScoreCriteria
from app.models.user import User
from app.routers.ideas import build_attachment_file_url, sync_idea_attachments_from_drive
from app.schemas import (
    ActualBenefitInput,
    ActualBenefitView,
    ApprovalAttachmentView,
    ApprovalIdeaDetail,
    ApprovalIdeaItem,
    ApprovalMetrics,
    ApprovalQueueResponse,
    ApprovalReviewView,
    ApprovalScoreInput,
    ApprovalScoreView,
    ApprovalSubmitRequest,
    ReviewHistoryResponse,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])

DEPT_VISIBLE_STATUSES = {
    IdeaStatus.SUBMITTED.value,
    IdeaStatus.UNDER_REVIEW.value,
    IdeaStatus.DEPT_APPROVED.value,
    IdeaStatus.COUNCIL_REVIEW.value,
    IdeaStatus.LEADERSHIP_REVIEW.value,
    IdeaStatus.APPROVED.value,
    IdeaStatus.REWARDED.value,
    IdeaStatus.REJECTED.value,
}
IE_VISIBLE_STATUSES = {
    IdeaStatus.DEPT_APPROVED.value,
    IdeaStatus.COUNCIL_REVIEW.value,
    IdeaStatus.LEADERSHIP_REVIEW.value,
    IdeaStatus.APPROVED.value,
    IdeaStatus.REWARDED.value,
}
BOD_VISIBLE_STATUSES = {
    IdeaStatus.LEADERSHIP_REVIEW.value,
    IdeaStatus.APPROVED.value,
    IdeaStatus.REWARDED.value,
}


def _normalize_status(value: Any) -> str:
    if value is None:
        return ""
    return str(value).split(".")[-1]


def _parse_json_list(raw_value: Any) -> list[str]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _dump_json_list(values: Iterable[str]) -> str:
    return json.dumps([str(value) for value in values])


def _role_name(user: User | None) -> str:
    return (user.role or "").strip() if user else "anonymous"


def _require_user(db: Session, employee_code: str) -> User:
    code = (employee_code or "").strip().upper()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu employee_code")
    user = db.query(User).options(joinedload(User.unit)).filter(func.upper(User.employee_code) == code).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User không tồn tại")
    return user


def _scope_kind(user: User) -> str:
    role = _role_name(user)
    if role in {"dept_manager", "sub_dept_manager"}:
        return "dept"
    if role == "ie_manager":
        return "ie"
    if role == "bod_manager":
        return "bod"
    if role == "admin":
        return "admin"
    if role == "unit_represent":
        return "unit_represent"
    return "anonymous"


def _review_level(user: User, idea: Idea) -> Optional[ReviewLevel]:
    scope = _scope_kind(user)
    if scope == "dept":
        return ReviewLevel.DEPT_HEAD
    if scope == "ie":
        return ReviewLevel.COUNCIL
    if scope == "bod":
        return ReviewLevel.LEADERSHIP
    if scope == "admin":
        status_value = _normalize_status(idea.status)
        if status_value in {IdeaStatus.SUBMITTED.value, IdeaStatus.UNDER_REVIEW.value}:
            return ReviewLevel.DEPT_HEAD
        if status_value in {IdeaStatus.DEPT_APPROVED.value, IdeaStatus.COUNCIL_REVIEW.value}:
            return ReviewLevel.COUNCIL
        if status_value == IdeaStatus.LEADERSHIP_REVIEW.value:
            return ReviewLevel.LEADERSHIP
    return None


def _visible_statuses(user: User) -> Optional[set[str]]:
    scope = _scope_kind(user)
    if scope in {"dept", "unit_represent"}:
        return DEPT_VISIBLE_STATUSES
    if scope == "ie":
        return IE_VISIBLE_STATUSES
    if scope == "bod":
        return BOD_VISIBLE_STATUSES
    return None


def _can_review(user: User, idea: Idea) -> bool:
    scope = _scope_kind(user)
    status_value = _normalize_status(idea.status)
    if scope == "dept":
        return idea.unit_id == user.unit_id and status_value in {IdeaStatus.SUBMITTED.value, IdeaStatus.UNDER_REVIEW.value}
    if scope == "ie":
        return status_value in {IdeaStatus.DEPT_APPROVED.value, IdeaStatus.COUNCIL_REVIEW.value}
    if scope == "bod":
        return status_value == IdeaStatus.LEADERSHIP_REVIEW.value
    if scope == "admin":
        return status_value in {
            IdeaStatus.SUBMITTED.value,
            IdeaStatus.UNDER_REVIEW.value,
            IdeaStatus.DEPT_APPROVED.value,
            IdeaStatus.COUNCIL_REVIEW.value,
            IdeaStatus.LEADERSHIP_REVIEW.value,
        }
    return False


def _next_status(user: User, action: ReviewAction) -> IdeaStatus:
    if action == ReviewAction.REJECT:
        return IdeaStatus.REJECTED
    scope = _scope_kind(user)
    if scope == "dept":
        return IdeaStatus.DEPT_APPROVED
    if scope == "ie":
        return IdeaStatus.LEADERSHIP_REVIEW
    if scope == "bod":
        return IdeaStatus.APPROVED
    return IdeaStatus.UNDER_REVIEW


def _score_role_bucket(role: str) -> Optional[str]:
    if role in {"dept_manager", "sub_dept_manager"}:
        return "dept"
    if role == "ie_manager":
        return "ie"
    return None


def _criteria_lookup(db: Session) -> dict[str, dict[str, ScoreCriteria]]:
    rows = db.query(ScoreCriteria).filter(ScoreCriteria.is_active.is_(True)).all()
    lookup: dict[str, dict[str, ScoreCriteria]] = {}
    for row in rows:
        lookup.setdefault(row.criterion_key, {})[row.code] = row
    return lookup


def _sum_selected(criteria_group: dict[str, ScoreCriteria], codes: list[str], detail: str) -> int:
    total = 0
    for code in codes:
        row = criteria_group.get(code)
        if row is None:
            raise HTTPException(status_code=400, detail=f"{detail}: mã tiêu chí {code} không hợp lệ")
        total += row.score
    return total


def _normalize_k2_type(raw_value: str) -> str:
    normalized = (raw_value or "").strip().upper()
    if normalized in {K2Type.NORMAL_EASY.value, K2Type.EASY.value}:
        return K2Type.EASY.value
    if normalized in {K2Type.NORMAL_HARD.value, K2Type.HARD.value}:
        return K2Type.HARD.value
    return normalized


def _calculate_score(db: Session, payload: ApprovalScoreInput) -> dict[str, Any]:
    criteria = _criteria_lookup(db)

    k1 = criteria.get("K1", {}).get(payload.k1_type.value)
    if k1 is None:
        raise HTTPException(status_code=400, detail="K1 không hợp lệ")
    k1_score = k1.score

    k2_type = _normalize_k2_type(payload.k2_type)
    if k2_type not in {K2Type.EASY.value, K2Type.HARD.value}:
        raise HTTPException(status_code=400, detail="K2 phải chọn Dễ hoặc Khó")
    k2_group_key = "K2_EASY" if k2_type == K2Type.EASY.value else "K2_HARD"
    k2_selected_codes = [str(code) for code in payload.k2_selected_codes]
    k2_score = _sum_selected(criteria.get(k2_group_key, {}), k2_selected_codes, "K2")

    k3_selected_codes = [str(code) for code in payload.k3_selected_codes]
    k3_option_code = payload.k3_option_code
    k3_score = 0
    k3_value = payload.k3_value

    if payload.k3_measure_type == K3MeasureType.UNMEASURABLE:
        k3_score = _sum_selected(criteria.get("K3_UNMEASURABLE", {}), k3_selected_codes, "K3")
        k3_option_code = None
        k3_value = None
    else:
        if not k3_option_code:
            raise HTTPException(status_code=400, detail="K3 đo lường được phải chọn mức giá trị")
        group_key = "K3_TIME_SAVED" if payload.k3_measure_type == K3MeasureType.TIME_SAVED else "K3_COST_SAVED"
        option = criteria.get(group_key, {}).get(k3_option_code)
        if option is None:
            raise HTTPException(status_code=400, detail="K3: mức giá trị không hợp lệ")
        k3_score = option.score
        k3_selected_codes = []
        k3_value = None

    total_score = k1_score + k2_score + k3_score
    return {
        "k1_type": payload.k1_type.value,
        "k1_score": k1_score,
        "k1_note": payload.k1_note,
        "k2_type": k2_type,
        "k2_score": k2_score,
        "k2_selected_codes": _dump_json_list(k2_selected_codes),
        "k2_time_frame": None,
        "k2_note": payload.k2_note,
        "k3_measure_type": payload.k3_measure_type.value,
        "k3_option_code": k3_option_code,
        "k3_selected_codes": _dump_json_list(k3_selected_codes),
        "k3_score": k3_score,
        "k3_value": k3_value,
        "k3_note": payload.k3_note,
        "total_score": total_score,
    }


def _format_score(score: IdeaScore) -> ApprovalScoreView:
    scorer = score.scorer
    return ApprovalScoreView(
        id=score.id,
        scorer_id=score.scorer_id,
        scorer_name=scorer.full_name if scorer else f"User {score.scorer_id}",
        scorer_role=_role_name(scorer),
        k1_type=_normalize_status(score.k1_type),
        k1_score=score.k1_score,
        k1_note=score.k1_note,
        k2_type=_normalize_status(score.k2_type),
        k2_score=score.k2_score,
        k2_selected_codes=_parse_json_list(score.k2_selected_codes),
        k2_time_frame=score.k2_time_frame,
        k2_note=score.k2_note,
        k3_measure_type=_normalize_status(score.k3_measure_type),
        k3_option_code=score.k3_option_code,
        k3_selected_codes=_parse_json_list(score.k3_selected_codes),
        k3_score=score.k3_score,
        k3_value=score.k3_value,
        k3_note=score.k3_note,
        total_score=score.total_score,
        is_final=score.is_final,
        scored_at=score.scored_at,
    )


def _format_review(review: IdeaReview) -> ApprovalReviewView:
    reviewer = review.reviewer
    return ApprovalReviewView(
        id=review.id,
        reviewer_id=review.reviewer_id,
        reviewer_name=reviewer.full_name if reviewer else f"User {review.reviewer_id}",
        reviewer_role=_role_name(reviewer),
        level=_normalize_status(review.level),
        action=_normalize_status(review.action),
        comment=review.comment,
        recommend_unit_reward=bool(review.recommend_unit_reward),
        reviewed_at=review.reviewed_at,
    )


def _format_attachment(attachment) -> ApprovalAttachmentView:
    return ApprovalAttachmentView(
        id=attachment.id,
        original_filename=attachment.original_filename,
        file_type=attachment.file_type,
        file_size=attachment.file_size,
        file_url=build_attachment_file_url(attachment),
        external_url=attachment.external_url,
        uploaded_at=attachment.uploaded_at,
    )


def _format_actual_benefit(evaluation: ActualBenefitEvaluation | None) -> ActualBenefitView | None:
    if evaluation is None:
        return None
    evaluator = evaluation.evaluator
    return ActualBenefitView(
        id=evaluation.id,
        idea_id=evaluation.idea_id,
        evaluator_id=evaluation.evaluator_id,
        evaluator_name=evaluator.full_name if evaluator else f"User {evaluation.evaluator_id}",
        before_seconds=evaluation.before_seconds,
        after_seconds=evaluation.after_seconds,
        improvement_percent=evaluation.improvement_percent,
        quantity=evaluation.quantity,
        labor_second_price=evaluation.labor_second_price,
        benefit_value=evaluation.benefit_value,
        note=evaluation.note,
        evaluated_at=evaluation.evaluated_at,
    )


def _has_measurable_ie_score(idea: Idea) -> bool:
    for score in idea.scores:
        if _role_name(score.scorer) == "ie_manager" and _normalize_status(score.k3_measure_type) in {
            K3MeasureType.TIME_SAVED.value,
            K3MeasureType.COST_SAVED.value,
        }:
            return True
    return False


def _build_title(idea: Idea) -> str:
    desc = (idea.description or "").strip()
    if not desc:
        return f"Ý tưởng #{idea.id}"
    return desc[:80] + ("..." if len(desc) > 80 else "")


def _get_latest_scores(idea: Idea) -> tuple[Optional[ApprovalScoreView], Optional[ApprovalScoreView], list[ApprovalScoreView]]:
    dept_score: Optional[ApprovalScoreView] = None
    ie_score: Optional[ApprovalScoreView] = None
    ordered = sorted(idea.scores, key=lambda item: item.scored_at or datetime.min, reverse=True)
    formatted = [_format_score(score) for score in ordered]
    for score in ordered:
        role_bucket = _score_role_bucket(_role_name(score.scorer))
        if role_bucket == "dept" and dept_score is None:
            dept_score = _format_score(score)
        if role_bucket == "ie" and ie_score is None:
            ie_score = _format_score(score)
    return dept_score, ie_score, formatted


def _get_latest_review(idea: Idea) -> tuple[Optional[ApprovalReviewView], list[ApprovalReviewView]]:
    ordered = sorted(idea.reviews, key=lambda item: item.reviewed_at or datetime.min, reverse=True)
    formatted = [_format_review(review) for review in ordered]
    return (formatted[0] if formatted else None), formatted


def _idea_to_item(idea: Idea, can_review: bool) -> ApprovalIdeaItem:
    dept_score, ie_score, _ = _get_latest_scores(idea)
    latest_review, _ = _get_latest_review(idea)
    slip = idea.payment_slip
    return ApprovalIdeaItem(
        id=idea.id,
        title=_build_title(idea),
        full_name=idea.full_name,
        employee_code=idea.employee_code,
        unit_id=idea.unit_id,
        unit_name=idea.unit.name if idea.unit else "",
        unit_department=idea.unit.department if idea.unit else None,
        category=_normalize_status(idea.category),
        status=_normalize_status(idea.status),
        description=idea.description,
        submitted_at=idea.submitted_at,
        attachments_count=len(idea.attachments),
        rejection_reason=idea.rejection_reason,
        can_review=can_review,
        employee_received=bool(slip and slip.employee_received),
        dept_score=dept_score,
        ie_score=ie_score,
        latest_review=latest_review,
    )


def _idea_to_detail(idea: Idea, can_review: bool) -> ApprovalIdeaDetail:
    item = _idea_to_item(idea, can_review)
    _, _, scores = _get_latest_scores(idea)
    _, reviews = _get_latest_review(idea)
    return ApprovalIdeaDetail(
        **item.model_dump(),
        phone_number=idea.phone_number,
        position=idea.position,
        product_code=idea.product_code,
        is_anonymous=idea.is_anonymous,
        attachments=[_format_attachment(attachment) for attachment in idea.attachments],
        reviews=reviews,
        scores=scores,
        actual_benefit=_format_actual_benefit(idea.actual_benefit),
    )


def _assert_review_permission(user: User, idea: Idea) -> None:
    scope = _scope_kind(user)
    if scope == "anonymous":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền phê duyệt")
    if scope == "unit_represent":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="unit_represent không có quyền phê duyệt")
    if scope in {"dept", "unit_represent"} and idea.unit_id != user.unit_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ý tưởng không thuộc đơn vị của bạn")
    if not _can_review(user, idea):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ý tưởng chưa ở bước duyệt của bạn")


def _load_scoped_ideas(db: Session, user: User, status_filter: Optional[str]) -> list[Idea]:
    query = (
        db.query(Idea)
        .options(
            joinedload(Idea.unit),
            joinedload(Idea.attachments),
            joinedload(Idea.actual_benefit).joinedload(ActualBenefitEvaluation.evaluator),
            joinedload(Idea.reviews).joinedload(IdeaReview.reviewer),
            joinedload(Idea.scores).joinedload(IdeaScore.scorer),
            joinedload(Idea.payment_slip),
        )
        .order_by(Idea.submitted_at.desc(), Idea.id.desc())
    )

    scope = _scope_kind(user)
    if scope in {"dept", "unit_represent"}:
        query = query.filter(Idea.unit_id == user.unit_id)
        visible = _visible_statuses(user)
        if visible:
            query = query.filter(Idea.status.in_(visible))
    elif scope in {"ie", "bod"}:
        visible = _visible_statuses(user)
        if visible:
            query = query.filter(Idea.status.in_(visible))
    elif scope != "admin":
        return []

    if status_filter:
        query = query.filter(Idea.status == status_filter)
    return query.all()


def _build_metrics(scope: str, items: list[Idea]) -> ApprovalMetrics:
    statuses = [_normalize_status(item.status) for item in items]
    total = len(statuses)
    if scope in {"dept", "unit_represent"}:
        approved = sum(
            status
            in {
                IdeaStatus.DEPT_APPROVED.value,
                IdeaStatus.COUNCIL_REVIEW.value,
                IdeaStatus.LEADERSHIP_REVIEW.value,
                IdeaStatus.APPROVED.value,
                IdeaStatus.REWARDED.value,
            }
            for status in statuses
        )
        pending = sum(status in {IdeaStatus.SUBMITTED.value, IdeaStatus.UNDER_REVIEW.value} for status in statuses)
    elif scope == "ie":
        approved = sum(status in {IdeaStatus.LEADERSHIP_REVIEW.value, IdeaStatus.APPROVED.value, IdeaStatus.REWARDED.value} for status in statuses)
        pending = sum(status in {IdeaStatus.DEPT_APPROVED.value, IdeaStatus.COUNCIL_REVIEW.value} for status in statuses)
    elif scope == "bod":
        approved = sum(status in {IdeaStatus.APPROVED.value, IdeaStatus.REWARDED.value} for status in statuses)
        pending = sum(status == IdeaStatus.LEADERSHIP_REVIEW.value for status in statuses)
    else:
        approved = sum(status in {IdeaStatus.APPROVED.value, IdeaStatus.REWARDED.value} for status in statuses)
        pending = sum(
            status
            in {
                IdeaStatus.SUBMITTED.value,
                IdeaStatus.UNDER_REVIEW.value,
                IdeaStatus.DEPT_APPROVED.value,
                IdeaStatus.COUNCIL_REVIEW.value,
                IdeaStatus.LEADERSHIP_REVIEW.value,
            }
            for status in statuses
        )
    rejected = sum(status == IdeaStatus.REJECTED.value for status in statuses)
    return ApprovalMetrics(total=total, approved=approved, pending=pending, rejected=rejected)


@router.get("/pending", response_model=ApprovalQueueResponse, tags=["dashboard"])
async def get_pending_reviews(
    employee_code: str = Query(...),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    user = _require_user(db, employee_code)
    scope = _scope_kind(user)
    ideas = _load_scoped_ideas(db, user, status_filter)
    items = [_idea_to_item(idea, _can_review(user, idea)) for idea in ideas]
    return ApprovalQueueResponse(
        role=_role_name(user),
        unit_id=user.unit_id,
        unit_name=user.unit.name if user.unit else None,
        metrics=_build_metrics(scope, ideas),
        items=items,
    )


@router.get("/{idea_id}/detail", response_model=ApprovalIdeaDetail)
async def get_review_detail(idea_id: int, employee_code: str = Query(...), db: Session = Depends(get_db)):
    user = _require_user(db, employee_code)
    idea = (
        db.query(Idea)
        .options(
            joinedload(Idea.unit),
            joinedload(Idea.attachments),
            joinedload(Idea.actual_benefit).joinedload(ActualBenefitEvaluation.evaluator),
            joinedload(Idea.reviews).joinedload(IdeaReview.reviewer),
            joinedload(Idea.scores).joinedload(IdeaScore.scorer),
            joinedload(Idea.payment_slip),
        )
        .filter(Idea.id == idea_id)
        .first()
    )
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea không tồn tại")

    scope = _scope_kind(user)
    if scope in {"dept", "unit_represent"} and idea.unit_id != user.unit_id:
        raise HTTPException(status_code=403, detail="Bạn không được xem ý tưởng này")
    if scope == "anonymous":
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem phê duyệt")

    if not idea.attachments:
        created = sync_idea_attachments_from_drive(db, idea.id)
        if created:
            idea = (
                db.query(Idea)
                .options(
                    joinedload(Idea.unit),
                    joinedload(Idea.attachments),
                    joinedload(Idea.actual_benefit).joinedload(ActualBenefitEvaluation.evaluator),
                    joinedload(Idea.reviews).joinedload(IdeaReview.reviewer),
                    joinedload(Idea.scores).joinedload(IdeaScore.scorer),
                    joinedload(Idea.payment_slip),
                )
                .filter(Idea.id == idea_id)
                .first()
            )

    return _idea_to_detail(idea, _can_review(user, idea))


@router.post("/submit", response_model=ApprovalIdeaDetail)
async def submit_review(payload: ApprovalSubmitRequest, db: Session = Depends(get_db)):
    user = _require_user(db, payload.employee_code)
    idea = (
        db.query(Idea)
        .options(
            joinedload(Idea.unit),
            joinedload(Idea.attachments),
            joinedload(Idea.actual_benefit).joinedload(ActualBenefitEvaluation.evaluator),
            joinedload(Idea.reviews).joinedload(IdeaReview.reviewer),
            joinedload(Idea.scores).joinedload(IdeaScore.scorer),
            joinedload(Idea.payment_slip),
        )
        .filter(Idea.id == payload.idea_id)
        .first()
    )
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea không tồn tại")

    _assert_review_permission(user, idea)

    action = payload.action
    comment = (payload.comment or "").strip() or None
    scope = _scope_kind(user)
    recommend_unit_reward = bool(payload.recommend_unit_reward) if scope == "ie" and action == ReviewAction.REJECT else False
    if action == ReviewAction.REJECT and not comment:
        raise HTTPException(status_code=400, detail="Không duyệt phải nhập lý do")
    if action == ReviewAction.APPROVE and scope in {"dept", "ie"} and payload.score is None:
        raise HTTPException(status_code=400, detail="Phê duyệt ở cấp này phải chấm điểm")

    if action == ReviewAction.APPROVE and payload.score is not None and scope in {"dept", "ie"}:
        score_values = _calculate_score(db, payload.score)
        db.add(
            IdeaScore(
                idea_id=idea.id,
                scorer_id=user.id,
                is_final=scope == "ie",
                **score_values,
            )
        )

    review_level = _review_level(user, idea)
    if review_level is None:
        raise HTTPException(status_code=400, detail="Không xác định được cấp duyệt hiện tại")

    db.add(
        IdeaReview(
            idea_id=idea.id,
            reviewer_id=user.id,
            level=review_level,
            action=action,
            comment=comment,
            recommend_unit_reward=recommend_unit_reward,
            reviewed_at=datetime.utcnow(),
        )
    )

    next_status = _next_status(user, action)
    idea.status = next_status
    idea.reviewed_at = datetime.utcnow()
    if next_status == IdeaStatus.REJECTED:
        idea.rejected_at = datetime.utcnow()
        idea.rejection_reason = comment
    else:
        idea.rejection_reason = None
        if next_status == IdeaStatus.APPROVED:
            idea.approved_at = datetime.utcnow()

    db.commit()

    refreshed = (
        db.query(Idea)
        .options(
            joinedload(Idea.unit),
            joinedload(Idea.attachments),
            joinedload(Idea.actual_benefit).joinedload(ActualBenefitEvaluation.evaluator),
            joinedload(Idea.reviews).joinedload(IdeaReview.reviewer),
            joinedload(Idea.scores).joinedload(IdeaScore.scorer),
            joinedload(Idea.payment_slip),
        )
        .filter(Idea.id == idea.id)
        .first()
    )
    return _idea_to_detail(refreshed, _can_review(user, refreshed))


@router.post("/{idea_id}/actual-benefit", response_model=ActualBenefitView)
async def upsert_actual_benefit(idea_id: int, payload: ActualBenefitInput, db: Session = Depends(get_db)):
    user = _require_user(db, payload.employee_code)
    if _scope_kind(user) not in {"ie", "admin"}:
        raise HTTPException(status_code=403, detail="Chỉ IE hoặc admin được đánh giá giá trị làm lợi thực tế")

    idea = (
        db.query(Idea)
        .options(
            joinedload(Idea.actual_benefit).joinedload(ActualBenefitEvaluation.evaluator),
            joinedload(Idea.scores).joinedload(IdeaScore.scorer),
        )
        .filter(Idea.id == idea_id)
        .first()
    )
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea không tồn tại")

    status_value = _normalize_status(idea.status)
    if status_value not in {IdeaStatus.LEADERSHIP_REVIEW.value, IdeaStatus.APPROVED.value, IdeaStatus.REWARDED.value}:
        raise HTTPException(status_code=400, detail="Chỉ đánh giá sau khi IE đã xác nhận đạt")
    if not _has_measurable_ie_score(idea):
        raise HTTPException(status_code=400, detail="Chỉ áp dụng cho ý tưởng IE đánh giá là đo lường được")
    if payload.before_seconds <= 0:
        raise HTTPException(status_code=400, detail="Trước cải tiến phải lớn hơn 0")
    if payload.after_seconds < 0:
        raise HTTPException(status_code=400, detail="Sau cải tiến không được âm")
    if payload.after_seconds > payload.before_seconds:
        raise HTTPException(status_code=400, detail="Sau cải tiến không được lớn hơn trước cải tiến")
    if payload.quantity < 0:
        raise HTTPException(status_code=400, detail="Số lượng không được âm")
    if payload.labor_second_price < 0:
        raise HTTPException(status_code=400, detail="Đơn giá giây CN không được âm")

    improvement_percent = ((payload.before_seconds - payload.after_seconds) / payload.before_seconds) * 100
    benefit_value = (payload.before_seconds - payload.after_seconds) * payload.quantity * payload.labor_second_price

    evaluation = idea.actual_benefit
    if evaluation is None:
        evaluation = ActualBenefitEvaluation(idea_id=idea.id, evaluator_id=user.id)
        db.add(evaluation)

    evaluation.evaluator_id = user.id
    evaluation.before_seconds = payload.before_seconds
    evaluation.after_seconds = payload.after_seconds
    evaluation.improvement_percent = improvement_percent
    evaluation.quantity = payload.quantity
    evaluation.labor_second_price = payload.labor_second_price
    evaluation.benefit_value = benefit_value
    evaluation.note = (payload.note or "").strip() or None
    evaluation.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(evaluation)
    evaluation.evaluator = user
    return _format_actual_benefit(evaluation)


@router.get("/{idea_id}/history", response_model=ReviewHistoryResponse)
async def get_review_history(idea_id: int, db: Session = Depends(get_db)):
    reviews = db.query(IdeaReview).filter(IdeaReview.idea_id == idea_id).order_by(IdeaReview.reviewed_at.desc()).all()
    level_map = {}
    for review in reviews:
        key = _normalize_status(review.level)
        if key not in level_map:
            level_map[key] = review
    return ReviewHistoryResponse(
        technical=level_map.get(ReviewLevel.TECHNICAL.value),
        dept_head=level_map.get(ReviewLevel.DEPT_HEAD.value),
        council=level_map.get(ReviewLevel.COUNCIL.value),
        leadership=level_map.get(ReviewLevel.LEADERSHIP.value),
    )
