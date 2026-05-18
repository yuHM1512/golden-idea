from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.database import get_db
from app.models.attachment import FileAttachment
from app.models.idea import Idea, IdeaCategory, IdeaStatus
from app.models.review import IdeaReview, ReviewLevel
from app.models.standardized_idea_replication import StandardizedIdeaReplication
from app.models.unit import Unit
from app.models.user import User
from app.routers.ideas import build_attachment_file_url, sync_idea_attachments_from_drive
from app.schemas.library import (
    IdeaLibraryAttachment,
    IdeaLibraryDetail,
    IdeaLibraryRow,
    StandardizedIdeaReplicationCreate,
    StandardizedIdeaReplicationResponse,
)

router = APIRouter(prefix="/library", tags=["library"])

LIBRARY_TYPE_STANDARDIZATION = "standardization"
LIBRARY_TYPE_NON_STANDARDIZATION = "non_standardization"
LIBRARY_TYPE_UNIT = "unit"
STANDARDIZATION_RESULT_TYPES = {"APPROVED_STANDARDIZATION"}
NON_STANDARDIZATION_RESULT_TYPES = {"APPROVED_NO_STANDARDIZATION"}
UNIT_LIBRARY_ALLOWED_ROLES = {"dept_manager", "sub_dept_manager", "unit_represent", "admin"}


def _make_title(title: str | None, description: str) -> str:
    text = (title or "").strip()
    if text:
        return text[:80] + ("..." if len(text) > 80 else "")
    text = (description or "").strip()
    if not text:
        return "(Không có mô tả)"
    first_line = text.splitlines()[0].strip()
    if len(first_line) <= 80:
        return first_line
    return first_line[:77].rstrip() + "..."


def _attachment_to_view(attachment: FileAttachment) -> IdeaLibraryAttachment:
    return IdeaLibraryAttachment(
        id=attachment.id,
        original_filename=attachment.original_filename,
        file_type=attachment.file_type,
        file_size=attachment.file_size,
        file_url=build_attachment_file_url(attachment),
        attachment_type=(attachment.attachment_type or "after"),
        uploaded_at=attachment.uploaded_at,
    )


def _normalize_role(user: User | None) -> str:
    return (user.role or "").strip().lower() if user else ""


def _resolve_user(db: Session, employee_code: str | None) -> User | None:
    code = (employee_code or "").strip().upper()
    if not code:
        return None
    return db.query(User).options(joinedload(User.unit)).filter(func.upper(User.employee_code) == code).first()


def _resolve_library_type(value: str | None) -> str:
    normalized = (value or LIBRARY_TYPE_STANDARDIZATION).strip().lower()
    if normalized in {LIBRARY_TYPE_STANDARDIZATION, LIBRARY_TYPE_NON_STANDARDIZATION, LIBRARY_TYPE_UNIT}:
        return normalized
    raise HTTPException(status_code=400, detail="library_type không hợp lệ")


def _can_view_unit_library(user: User | None) -> bool:
    if user is None or user.unit_id is None:
        return False
    return _normalize_role(user) in UNIT_LIBRARY_ALLOWED_ROLES


def _latest_council_result_subquery(db: Session):
    return (
        db.query(
            IdeaReview.idea_id.label("idea_id"),
            IdeaReview.council_result_type.label("council_result_type"),
            func.row_number()
            .over(
                partition_by=IdeaReview.idea_id,
                order_by=(IdeaReview.reviewed_at.desc(), IdeaReview.id.desc()),
            )
            .label("rn"),
        )
        .filter(IdeaReview.level == ReviewLevel.COUNCIL)
        .subquery()
    )


def _latest_council_result_type(idea: Idea) -> str | None:
    reviews = sorted(
        [review for review in (idea.reviews or []) if review.level == ReviewLevel.COUNCIL],
        key=lambda item: (item.reviewed_at or datetime.min, item.id),
        reverse=True,
    )
    for review in reviews:
        value = (review.council_result_type or "").strip().upper()
        if value:
            return value
    return None


def _serialize_replication(replication: StandardizedIdeaReplication) -> StandardizedIdeaReplicationResponse:
    return StandardizedIdeaReplicationResponse(
        id=replication.id,
        idea_id=replication.idea_id,
        unit_id=replication.unit_id,
        unit_name=replication.unit.name if replication.unit else "",
        requester_user_id=replication.requester_user_id,
        requester_employee_code=replication.requester_employee_code,
        requester_name=replication.requester_name,
        idea_title=replication.idea_title,
        apply_date=replication.apply_date,
        description=replication.description,
        approve=bool(replication.approve),
        created_at=replication.created_at,
    )


@router.get("/ideas", response_model=List[IdeaLibraryRow])
async def list_library_ideas(
    employee_code: Optional[str] = Query(default=None),
    library_type: str = Query(default=LIBRARY_TYPE_STANDARDIZATION),
    q: Optional[str] = None,
    category: Optional[IdeaCategory] = None,
    status: Optional[IdeaStatus] = None,
    unit_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    limit = min(max(limit, 1), 500)
    skip = max(skip, 0)
    current_library_type = _resolve_library_type(library_type)
    user = _resolve_user(db, employee_code)
    latest_council = _latest_council_result_subquery(db)

    query = (
        db.query(
            Idea.id,
            Idea.title,
            Idea.category,
            Idea.status,
            Idea.submitted_at,
            Idea.description,
            Idea.full_name,
            Idea.employee_code,
            Idea.is_anonymous,
            Idea.unit_id,
            Unit.name.label("unit_name"),
            latest_council.c.council_result_type.label("council_result_type"),
            func.count(FileAttachment.id).label("attachment_count"),
        )
        .join(Unit, Unit.id == Idea.unit_id)
        .outerjoin(
            latest_council,
            and_(latest_council.c.idea_id == Idea.id, latest_council.c.rn == 1),
        )
        .outerjoin(FileAttachment, FileAttachment.idea_id == Idea.id)
        .group_by(
            Idea.id,
            Idea.title,
            Idea.category,
            Idea.status,
            Idea.submitted_at,
            Idea.description,
            Idea.full_name,
            Idea.employee_code,
            Idea.is_anonymous,
            Idea.unit_id,
            Unit.name,
            latest_council.c.council_result_type,
        )
        .order_by(Idea.submitted_at.desc())
    )

    if current_library_type == LIBRARY_TYPE_UNIT:
        if not _can_view_unit_library(user):
            raise HTTPException(status_code=403, detail="Bạn không có quyền xem Kho Đơn vị")
        query = query.filter(Idea.unit_id == user.unit_id, Idea.status != IdeaStatus.DRAFT)
    elif current_library_type == LIBRARY_TYPE_STANDARDIZATION:
        query = query.filter(latest_council.c.council_result_type.in_(STANDARDIZATION_RESULT_TYPES))
    else:
        query = query.filter(latest_council.c.council_result_type.in_(NON_STANDARDIZATION_RESULT_TYPES))

    if category is not None:
        query = query.filter(Idea.category == category)
    if status is not None and current_library_type == LIBRARY_TYPE_UNIT:
        query = query.filter(Idea.status == status)
    if unit_id is not None and current_library_type != LIBRARY_TYPE_UNIT:
        query = query.filter(Idea.unit_id == unit_id)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Idea.title.ilike(term),
                Idea.description.ilike(term),
                Idea.full_name.ilike(term),
                Idea.employee_code.ilike(term),
                Unit.name.ilike(term),
            )
        )

    rows = query.offset(skip).limit(limit).all()
    result: list[IdeaLibraryRow] = []
    for row in rows:
        result.append(
            IdeaLibraryRow(
                id=row.id,
                title=_make_title(row.title, row.description),
                category=row.category,
                status=row.status,
                submitted_at=row.submitted_at,
                unit_id=row.unit_id,
                unit_name=row.unit_name,
                full_name=(row.full_name or ""),
                employee_code=(row.employee_code or None),
                description=row.description or "",
                attachment_count=int(row.attachment_count or 0),
                library_type=current_library_type,
            )
        )
    return result


@router.get("/ideas/{idea_id}", response_model=IdeaLibraryDetail)
async def get_library_idea_detail(
    idea_id: int,
    employee_code: Optional[str] = Query(default=None),
    library_type: str = Query(default=LIBRARY_TYPE_STANDARDIZATION),
    db: Session = Depends(get_db),
):
    current_library_type = _resolve_library_type(library_type)
    user = _resolve_user(db, employee_code)

    idea = (
        db.query(Idea)
        .options(joinedload(Idea.unit), joinedload(Idea.attachments), joinedload(Idea.reviews))
        .filter(Idea.id == idea_id)
        .first()
    )
    if idea is None:
        raise HTTPException(status_code=404, detail="Ý tưởng không tồn tại trong kho dữ liệu")

    latest_result_type = _latest_council_result_type(idea)
    if current_library_type == LIBRARY_TYPE_UNIT:
        if not _can_view_unit_library(user) or idea.unit_id != user.unit_id or idea.status == IdeaStatus.DRAFT:
            raise HTTPException(status_code=403, detail="Bạn không có quyền xem ý tưởng này trong Kho Đơn vị")
    elif current_library_type == LIBRARY_TYPE_STANDARDIZATION:
        if latest_result_type not in STANDARDIZATION_RESULT_TYPES:
            raise HTTPException(status_code=404, detail="Ý tưởng không tồn tại trong kho Đưa vào chuẩn hoá")
    else:
        if latest_result_type not in NON_STANDARDIZATION_RESULT_TYPES:
            raise HTTPException(status_code=404, detail="Ý tưởng không tồn tại trong kho Không đưa vào chuẩn hoá")

    if not idea.attachments:
        created = sync_idea_attachments_from_drive(db, idea.id)
        if created:
            idea = (
                db.query(Idea)
                .options(joinedload(Idea.unit), joinedload(Idea.attachments), joinedload(Idea.reviews))
                .filter(Idea.id == idea_id)
                .first()
            )

    attachments = [_attachment_to_view(item) for item in (idea.attachments or [])]
    return IdeaLibraryDetail(
        id=idea.id,
        title=_make_title(idea.title, idea.description),
        category=idea.category,
        status=idea.status,
        submitted_at=idea.submitted_at,
        unit_id=idea.unit_id,
        unit_name=idea.unit.name if idea.unit else "",
        full_name=idea.full_name or "",
        employee_code=idea.employee_code or None,
        phone_number=idea.phone_number or None,
        position=idea.position or None,
        product_code=idea.product_code or None,
        description=idea.description or "",
        attachment_count=len(attachments),
        library_type=current_library_type,
        attachments=attachments,
    )


@router.post("/replications", response_model=StandardizedIdeaReplicationResponse)
async def create_standardized_idea_replication(
    payload: StandardizedIdeaReplicationCreate,
    db: Session = Depends(get_db),
):
    user = _resolve_user(db, payload.employee_code)
    if user is None or user.unit_id is None:
        raise HTTPException(status_code=403, detail="Chỉ người dùng thuộc đơn vị mới được nhân rộng ý tưởng")

    idea = (
        db.query(Idea)
        .options(joinedload(Idea.reviews))
        .filter(Idea.id == payload.idea_id)
        .first()
    )
    if idea is None:
        raise HTTPException(status_code=404, detail="Ý tưởng không tồn tại")

    latest_result_type = _latest_council_result_type(idea)
    if latest_result_type not in (STANDARDIZATION_RESULT_TYPES | NON_STANDARDIZATION_RESULT_TYPES):
        raise HTTPException(status_code=400, detail="Chỉ ý tưởng thuộc 2 kho chuẩn hoá mới được nhân rộng")

    description = (payload.description or "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="Phải nhập mô tả nhân rộng")

    duplicated = (
        db.query(StandardizedIdeaReplication.id)
        .filter(
            StandardizedIdeaReplication.idea_id == idea.id,
            StandardizedIdeaReplication.unit_id == user.unit_id,
        )
        .first()
    )
    if duplicated is not None:
        raise HTTPException(status_code=400, detail="Ý tưởng này đã được đơn vị bạn nhân rộng trước đó")

    replication = StandardizedIdeaReplication(
        idea_id=idea.id,
        unit_id=user.unit_id,
        requester_user_id=user.id,
        requester_employee_code=(user.employee_code or "").strip().upper(),
        requester_name=(user.full_name or "").strip() or (user.employee_code or "").strip().upper(),
        idea_title=_make_title(idea.title, idea.description),
        apply_date=payload.apply_date,
        description=description,
        approve=False,
    )
    db.add(replication)
    db.commit()
    db.refresh(replication)

    refreshed = (
        db.query(StandardizedIdeaReplication)
        .options(joinedload(StandardizedIdeaReplication.unit))
        .filter(StandardizedIdeaReplication.id == replication.id)
        .first()
    )
    return _serialize_replication(refreshed)
