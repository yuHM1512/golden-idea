from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pathlib import Path
import uuid
import json

from app.database import get_db
from app.config import settings
from app.schemas import (
    IdeaCreate, IdeaUpdate, IdeaDetailResponse,
    IdeaListResponse, IdeaSubmitResponse
)
from app.models.idea import Idea, IdeaStatus
from app.models.attachment import FileAttachment

router = APIRouter(prefix="/ideas", tags=["ideas"])

def _truncate(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value[:max_length] if value else None

def _normalize_participants(idea: IdeaCreate) -> list[dict[str, str]]:
    participants: list[dict[str, str]] = []
    for participant in idea.participants or []:
        full_name = (participant.full_name or "").strip()
        employee_code = (participant.employee_code or "").strip()
        if full_name:
            participants.append({"full_name": full_name, "employee_code": employee_code})

    if not participants:
        full_name = (idea.full_name or "").strip()
        if full_name:
            participants.append({
                "full_name": full_name,
                "employee_code": (idea.employee_code or "").strip(),
            })

    return participants

@router.post("/", response_model=IdeaSubmitResponse)
async def submit_idea(idea: IdeaCreate, db: Session = Depends(get_db)):
    """
    Submit a new idea (Phiếu đăng ký ý tưởng)
    Captures: full_name, employee_code, phone, bo_phan, position, product_code,
              category, description, is_anonymous, unit_id
    """
    try:
        participants = _normalize_participants(idea)
        if not participants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vui lòng nhập ít nhất 1 người tham gia",
            )

        display_full_name = "; ".join(participant["full_name"] for participant in participants)
        primary_employee_code = next(
            (participant["employee_code"] for participant in participants if participant["employee_code"]),
            None,
        )

        # Create new Idea record
        new_idea = Idea(
            full_name=_truncate(display_full_name, 255),
            employee_code=_truncate(primary_employee_code, 50),
            participants_json=json.dumps(participants, ensure_ascii=False),
            phone_number=idea.phone_number,
            bo_phan=_truncate(idea.bo_phan, 255),
            position=idea.position,
            product_code=idea.product_code,
            category=idea.category,
            description=idea.description,
            is_anonymous=idea.is_anonymous,
            unit_id=idea.unit_id,
            status=IdeaStatus.SUBMITTED,
            submitted_at=datetime.utcnow(),
        )

        db.add(new_idea)
        db.commit()
        db.refresh(new_idea)

        return {
            "id": new_idea.id,
            "status": new_idea.status,
            "submitted_at": new_idea.submitted_at,
            "message": "Ý tưởng của bạn đã được đăng ký thành công",
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi gửi ý tưởng: {str(e)}"
        )

@router.get("/", response_model=List[IdeaListResponse])
async def list_ideas(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    unit_id: int = None,
    db: Session = Depends(get_db)
):
    """List ideas with filters"""
    # TODO: Implement filtering
    pass

@router.get("/{idea_id}", response_model=IdeaDetailResponse)
async def get_idea(idea_id: int, db: Session = Depends(get_db)):
    """Get idea details with attachments"""
    # TODO: Implement
    pass

@router.put("/{idea_id}", response_model=IdeaDetailResponse)
async def update_idea(
    idea_id: int,
    idea: IdeaUpdate,
    db: Session = Depends(get_db)
):
    """Update idea (before submission)"""
    # TODO: Implement - only allow if status is DRAFT
    pass

@router.post("/{idea_id}/upload", tags=["attachments"])
async def upload_attachment(
    idea_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload image/video attachment to idea
    Max 10MB, allowed: jpg, jpeg, png, gif, mp4, avi, mov
    """
    idea = db.query(Idea).filter(Idea.id == idea_id).first()
    if idea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Idea không tồn tại")

    original_filename = (file.filename or "").strip()
    if not original_filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu tên file")

    suffix = Path(original_filename).suffix.lower().lstrip(".")
    if not suffix:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File không có đuôi mở rộng")

    allowed = {ext.lower().lstrip(".") for ext in (settings.ALLOWED_EXTENSIONS or [])}
    if suffix not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Không hỗ trợ định dạng: {suffix}")

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{uuid.uuid4().hex}.{suffix}"
    out_path = upload_dir / stored_filename

    max_bytes = int(settings.MAX_FILE_SIZE_MB) * 1024 * 1024
    size = 0
    try:
        with out_path.open("wb") as f_out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File vượt quá giới hạn {settings.MAX_FILE_SIZE_MB}MB",
                    )
                f_out.write(chunk)
    except HTTPException:
        if out_path.exists():
            out_path.unlink(missing_ok=True)
        raise
    except Exception as e:
        if out_path.exists():
            out_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lỗi lưu file: {str(e)}")
    finally:
        await file.close()

    attachment = FileAttachment(
        idea_id=idea_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_type=suffix,
        file_size=size,
        file_path=str(Path("uploads") / stored_filename),
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return {
        "id": attachment.id,
        "idea_id": attachment.idea_id,
        "original_filename": attachment.original_filename,
        "file_type": attachment.file_type,
        "file_size": attachment.file_size,
        "file_path": attachment.file_path,
        "uploaded_at": attachment.uploaded_at,
    }

@router.delete("/{idea_id}/attachments/{attachment_id}")
async def delete_attachment(
    idea_id: int,
    attachment_id: int,
    db: Session = Depends(get_db)
):
    """Delete attachment"""
    # TODO: Implement
    pass

@router.post("/{idea_id}/submit", response_model=IdeaSubmitResponse)
async def finalize_submission(idea_id: int, db: Session = Depends(get_db)):
    """Finalize submission (move from DRAFT to SUBMITTED)"""
    # TODO: Implement
    pass

@router.post("/{idea_id}/cancel")
async def cancel_idea(idea_id: int, db: Session = Depends(get_db)):
    """Cancel submitted idea"""
    # TODO: Implement
    pass
