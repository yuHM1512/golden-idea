from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.idea import Idea, IdeaCategory, IdeaStatus
from app.models.unit import Unit
from app.models.attachment import FileAttachment
from app.schemas.library import IdeaLibraryRow, IdeaLibraryDetail, IdeaLibraryAttachment

router = APIRouter(prefix="/library", tags=["library"])

LIBRARY_VISIBLE_STATUSES = {
    IdeaStatus.APPROVED,
    IdeaStatus.REWARDED,
}


def _make_title(description: str) -> str:
    text = (description or "").strip()
    if not text:
        return "(Không có mô tả)"
    first_line = text.splitlines()[0].strip()
    if len(first_line) <= 80:
        return first_line
    return first_line[:77].rstrip() + "..."


def _attachment_to_view(attachment: FileAttachment) -> IdeaLibraryAttachment:
    file_path = (attachment.file_path or "").replace("\\", "/").lstrip("/")
    return IdeaLibraryAttachment(
        id=attachment.id,
        original_filename=attachment.original_filename,
        file_type=attachment.file_type,
        file_size=attachment.file_size,
        file_url=f"/{file_path}" if file_path else "#",
        uploaded_at=attachment.uploaded_at,
    )


@router.get("/ideas", response_model=List[IdeaLibraryRow])
async def list_library_ideas(
    q: Optional[str] = None,
    category: Optional[IdeaCategory] = None,
    status: Optional[IdeaStatus] = None,
    unit_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Library list view for ideas with enough fields for UI.
    """
    limit = min(max(limit, 1), 500)
    skip = max(skip, 0)

    query = (
        db.query(
            Idea.id,
            Idea.category,
            Idea.status,
            Idea.submitted_at,
            Idea.description,
            Idea.full_name,
            Idea.employee_code,
            Idea.is_anonymous,
            Idea.unit_id,
            Unit.name.label("unit_name"),
            func.count(FileAttachment.id).label("attachment_count"),
        )
        .join(Unit, Unit.id == Idea.unit_id)
        .outerjoin(FileAttachment, FileAttachment.idea_id == Idea.id)
        .filter(Idea.status.in_(LIBRARY_VISIBLE_STATUSES))
        .group_by(
            Idea.id,
            Idea.category,
            Idea.status,
            Idea.submitted_at,
            Idea.description,
            Idea.full_name,
            Idea.employee_code,
            Idea.is_anonymous,
            Idea.unit_id,
            Unit.name,
        )
        .order_by(Idea.submitted_at.desc())
    )

    if category is not None:
        query = query.filter(Idea.category == category)
    if status is not None:
        query = query.filter(Idea.status == status)
    if unit_id is not None:
        query = query.filter(Idea.unit_id == unit_id)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Idea.description.ilike(term),
                Idea.full_name.ilike(term),
                Idea.employee_code.ilike(term),
                Unit.name.ilike(term),
            )
        )

    rows = query.offset(skip).limit(limit).all()
    result: list[IdeaLibraryRow] = []
    for r in rows:
        result.append(
            IdeaLibraryRow(
                id=r.id,
                title=_make_title(r.description),
                category=r.category,
                status=r.status,
                submitted_at=r.submitted_at,
                unit_id=r.unit_id,
                unit_name=r.unit_name,
                full_name=(r.full_name or ""),
                employee_code=(r.employee_code or None),
                description=r.description or "",
                attachment_count=int(r.attachment_count or 0),
            )
        )
    return result


@router.get("/ideas/{idea_id}", response_model=IdeaLibraryDetail)
async def get_library_idea_detail(idea_id: int, db: Session = Depends(get_db)):
    idea = (
        db.query(Idea)
        .options(joinedload(Idea.unit), joinedload(Idea.attachments))
        .filter(Idea.id == idea_id, Idea.status.in_(LIBRARY_VISIBLE_STATUSES))
        .first()
    )
    if idea is None:
        raise HTTPException(status_code=404, detail="Ý tưởng không tồn tại trong kho chuẩn hoá")

    attachments = [_attachment_to_view(item) for item in (idea.attachments or [])]
    return IdeaLibraryDetail(
        id=idea.id,
        title=_make_title(idea.description),
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
        attachments=attachments,
    )
